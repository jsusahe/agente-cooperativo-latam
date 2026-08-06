# cooperative_fetcher.py - VERSIÓN OPTIMIZADA CON PARALELISMO
import feedparser
import json
import os
import requests
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from urllib.parse import urlparse, urljoin

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🔥 CACHE DE SESIONES - Reutilizar conexiones
_session_cache = {}
_session_lock = threading.Lock()

def get_session(url: str = None) -> requests.Session:
    """Obtiene o crea una sesión cacheada"""
    key = 'default'
    if url:
        parsed = urlparse(url)
        key = parsed.netloc or 'default'
    
    with _session_lock:
        if key not in _session_cache:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0'
            })
            session.verify = False
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=10,
                max_retries=2,
                pool_block=False
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            _session_cache[key] = session
        
        return _session_cache[key]


class CooperativeFetcher:
    """Clase optimizada para extraer noticias de fuentes cooperativas"""
    
    def __init__(self, config_file="config_countries.json", max_workers=5):
        self.config = self._load_config(config_file)
        self.countries = self.config.get("countries", [])
        self.latam_sources = self.config.get("latam_sources", [])
        self.settings = self.config.get("settings", {})
        self.min_news = self.settings.get("min_news_per_country", 5)
        self.days_back = self.settings.get("days_back", 3)
        self.timeout = self.settings.get("timeout", 15)
        self.max_retries = self.settings.get("max_retries", 2)
        self.max_workers = max_workers
        self.user_agent = self.settings.get("user_agent", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
    def _load_config(self, config_file: str) -> Dict:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error al cargar configuración: {e}")
            return {"countries": []}
    
    def _safe_request(self, url: str) -> Optional[requests.Response]:
        """Realiza una solicitud HTTP con timeout optimizado"""
        session = get_session(url)
        connect_timeout = 10
        read_timeout = 15
        
        for attempt in range(self.max_retries):
            try:
                response = session.get(
                    url, 
                    timeout=(connect_timeout, read_timeout),
                    verify=False,
                    allow_redirects=True,
                    stream=True
                )
                if int(response.headers.get('content-length', 0)) > 2 * 1024 * 1024:
                    response.close()
                    return None
                response.raise_for_status()
                return response
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)
            except Exception:
                return None
        return None
    
    def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Obtiene artículos de un feed RSS"""
        try:
            response = self._safe_request(url)
            if not response:
                return []
            
            content = response.content[:50000]
            feed = feedparser.parse(content)
            
            if feed.bozo:
                return []
            
            articles = []
            cutoff_date = datetime.now() - timedelta(days=self.days_back)
            
            for entry in feed.entries[:2]:
                published = entry.get('published_parsed') or entry.get('updated_parsed')
                if published:
                    pub_date = datetime(*published[:6])
                    if pub_date < cutoff_date:
                        continue
                
                summary = entry.get('summary', '')
                summary = re.sub(r'<[^>]+>', '', summary)[:300]
                
                articles.append({
                    'title': entry.get('title', 'Sin título')[:100],
                    'link': entry.get('link', '#'),
                    'summary': summary,
                    'published': published,
                    'source': feed.feed.get('title', 'Fuente desconocida'),
                    'source_url': url
                })
            
            return articles
        except Exception:
            return []
    
    def fetch_website_news(self, url: str) -> List[Dict]:
        """Extrae noticias de un sitio web con scraping optimizado"""
        articles = []
        try:
            response = self._safe_request(url)
            if not response:
                return []
            
            content = response.content[:200000]
            soup = BeautifulSoup(content, 'html.parser')
            
            selectors = [
                'article', '.post', '.news-item', '.noticia',
                '.entry', '.blog-post', '.feed-item', '.item'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                for item in items[:3]:
                    title_elem = item.find(['h1', 'h2', 'h3', 'h4']) or item.find('a')
                    title = title_elem.get_text(strip=True)[:100] if title_elem else 'Sin título'
                    
                    if len(title) < 10:
                        continue
                    
                    link_elem = item.find('a', href=True)
                    link = link_elem.get('href') if link_elem else '#'
                    if link and not link.startswith('http'):
                        link = urljoin(url, link)
                    
                    p_elem = item.find('p')
                    summary = p_elem.get_text(strip=True)[:200] if p_elem else ''
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'published': None,
                        'source': url,
                        'source_url': url
                    })
                    
                    if len(articles) >= 2:
                        break
                
                if len(articles) >= 2:
                    break
            
            return articles[:2]
        except Exception:
            return []
    
    def fetch_source(self, source: Dict) -> List[Dict]:
        """Obtiene noticias de una fuente según su tipo"""
        source_type = source.get('type', 'website')
        url = source.get('url', '')
        name = source.get('name', 'Desconocido')
        
        if not url:
            return []
        
        articles = []
        
        if source.get('rss'):
            articles = self.fetch_rss_feed(source['rss'])
            if articles:
                for article in articles:
                    article['source_name'] = name
                    article['source_type'] = source_type
                return articles
        
        if source_type in ['website', 'blog', 'media', 'news', 'government']:
            articles = self.fetch_website_news(url)
            for article in articles:
                article['source_name'] = name
                article['source_type'] = source_type
            return articles
        
        return []
    
    def fetch_country_news(self, country: Dict) -> Dict:
        """Obtiene todas las noticias de un país (paralelo)"""
        country_name = country.get('name', 'Desconocido')
        country_code = country.get('code', 'XX')
        sources = country.get('sources', {})
        
        print(f"\n{'='*50}")
        print(f"🇨🇴 {country_name} ({country_code})")
        print(f"{'='*50}")
        
        all_articles = []
        
        all_sources = []
        for category, source_list in sources.items():
            for source in source_list:
                source['_category'] = category
                all_sources.append(source)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {
                executor.submit(self.fetch_source, source): source 
                for source in all_sources
            }
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    articles = future.result(timeout=20)
                    if articles:
                        category = source.get('_category', 'general')
                        for article in articles:
                            article['country'] = country_name
                            article['country_code'] = country_code
                            article['category'] = category
                        all_articles.extend(articles)
                except Exception:
                    pass
        
        print(f"📊 {len(all_articles)} noticias")
        return {
            'country': country_name,
            'code': country_code,
            'articles': all_articles,
            'total': len(all_articles),
            'sources_checked': len(all_sources)
        }
    
    def fetch_all_countries(self) -> Dict:
        """Obtiene noticias de todos los países (paralelo)"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(self.countries)) as executor:
            future_to_country = {
                executor.submit(self.fetch_country_news, country): country
                for country in self.countries
            }
            
            for future in as_completed(future_to_country):
                country = future_to_country[future]
                try:
                    country_data = future.result(timeout=60)
                    results[country['code']] = country_data
                except Exception as e:
                    print(f"⚠️ Error procesando {country.get('name', 'Desconocido')}: {e}")
                    results[country['code']] = {
                        'country': country.get('name', 'Desconocido'),
                        'code': country.get('code', 'XX'),
                        'articles': [],
                        'total': 0,
                        'sources_checked': 0
                    }
        
        return results
    
    def get_latam_news(self) -> List[Dict]:
        """Obtiene noticias de fuentes latinoamericanas (paralelo)"""
        print(f"\n{'='*50}")
        print("🌎 Fuentes Latinoamericanas")
        print(f"{'='*50}")
        
        articles = []
        
        with ThreadPoolExecutor(max_workers=len(self.latam_sources)) as executor:
            future_to_source = {
                executor.submit(self.fetch_source, source): source
                for source in self.latam_sources
            }
            
            for future in as_completed(future_to_source):
                try:
                    fetched = future.result(timeout=20)
                    for article in fetched:
                        article['country'] = 'Latinoamérica'
                        article['country_code'] = 'LATAM'
                        article['category'] = 'regional'
                    articles.extend(fetched)
                except Exception:
                    pass
        
        return articles


def get_cooperative_news(max_workers: int = 5) -> Dict:
    """Función principal para obtener todas las noticias cooperativas"""
    start_time = time.time()
    
    fetcher = CooperativeFetcher(max_workers=max_workers)
    
    print("🚀 INICIANDO AGENTE DE NOTICIAS COOPERATIVAS")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚡ Paralelismo: {max_workers} workers")
    
    country_results = fetcher.fetch_all_countries()
    
    latam_news = fetcher.get_latam_news()
    country_results['LATAM'] = {
        'country': 'Latinoamérica',
        'code': 'LATAM',
        'articles': latam_news,
        'total': len(latam_news),
        'sources_checked': len(fetcher.latam_sources)
    }
    
    if any(country_results.get(c, {}).get('total', 0) for c in country_results if c != 'LATAM'):
        output_file = f"cooperative_news_{datetime.now().strftime('%Y-%m-%d')}.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(country_results, f, indent=4, ensure_ascii=False, default=str)
        except Exception:
            pass
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ Tiempo total: {elapsed:.1f} segundos")
    
    return country_results


if __name__ == '__main__':
    print("=== PRUEBA DE COOPERATIVE_FETCHER (OPTIMIZADO) ===")
    results = get_cooperative_news(max_workers=8)
    
    print("\n📊 RESUMEN DE NOTICIAS POR PAÍS:")
    print("-" * 50)
    for code, data in results.items():
        if code == 'LATAM':
            continue
        print(f"{data.get('country', 'Desconocido')} ({code}): {data.get('total', 0)} noticias")
    print(f"\n🌎 Latinoamérica: {results.get('LATAM', {}).get('total', 0)} noticias")