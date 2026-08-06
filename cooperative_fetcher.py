# cooperative_fetcher.py - Timeouts Agresivos
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

# 🔥 CACHE DE SESIONES
_session_cache = {}
_session_lock = threading.Lock()

def get_session(url: str = None) -> requests.Session:
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
            # 🔥 Reducir timeouts en el adaptador
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=5,
                pool_maxsize=5,
                max_retries=0,  # Sin reintentos automáticos
                pool_block=False
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            _session_cache[key] = session
        
        return _session_cache[key]


class CooperativeFetcher:
    def __init__(self, config_file="config_countries.json", max_workers=3):  # 🔥 Reducido a 3
        self.config = self._load_config(config_file)
        self.countries = self.config.get("countries", [])
        self.latam_sources = self.config.get("latam_sources", [])
        self.settings = self.config.get("settings", {})
        self.min_news = self.settings.get("min_news_per_country", 5)
        self.days_back = self.settings.get("days_back", 3)
        self.timeout = self.settings.get("timeout", 10)  # 🔥 Reducido a 10
        self.max_retries = 1  # 🔥 Solo 1 reintento
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
        """Realiza una solicitud HTTP con timeouts agresivos"""
        session = get_session(url)
        
        # 🔥 TIMEOUTS AGRESIVOS: 5s conexión, 8s lectura
        connect_timeout = 5
        read_timeout = 8
        total_timeout = (connect_timeout, read_timeout)
        
        for attempt in range(self.max_retries + 1):
            try:
                response = session.get(
                    url, 
                    timeout=total_timeout,
                    verify=False,
                    allow_redirects=True,
                    stream=True
                )
                # Limitar tamaño a 1MB
                if int(response.headers.get('content-length', 0)) > 1 * 1024 * 1024:
                    response.close()
                    return None
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                print(f"    ⏱️ Timeout en {url[:50]}...")
                if attempt >= self.max_retries:
                    return None
                time.sleep(0.5)  # 🔥 Solo 0.5s entre reintentos
            except requests.exceptions.ConnectionError:
                print(f"    ⚠️ Error de conexión en {url[:50]}...")
                if attempt >= self.max_retries:
                    return None
                time.sleep(0.5)
            except Exception as e:
                print(f"    ⚠️ Error en {url[:50]}...: {str(e)[:30]}")
                return None
        return None
    
    def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Obtiene artículos de un feed RSS con timeout rápido"""
        try:
            response = self._safe_request(url)
            if not response:
                return []
            
            content = response.content[:30000]  # 🔥 Reducido a 30KB
            feed = feedparser.parse(content)
            
            if feed.bozo:
                return []
            
            articles = []
            cutoff_date = datetime.now() - timedelta(days=self.days_back)
            
            # 🔥 Solo 1 artículo por feed
            for entry in feed.entries[:1]:
                published = entry.get('published_parsed') or entry.get('updated_parsed')
                if published:
                    pub_date = datetime(*published[:6])
                    if pub_date < cutoff_date:
                        continue
                
                summary = entry.get('summary', '')
                summary = re.sub(r'<[^>]+>', '', summary)[:200]
                
                articles.append({
                    'title': entry.get('title', 'Sin título')[:80],
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
        """Extrae noticias de un sitio web con scraping rápido"""
        articles = []
        try:
            response = self._safe_request(url)
            if not response:
                return []
            
            content = response.content[:100000]  # 🔥 Reducido a 100KB
            soup = BeautifulSoup(content, 'html.parser')
            
            # 🔥 Selectores reducidos
            selectors = ['article', '.post', '.news-item', '.noticia']
            
            for selector in selectors:
                items = soup.select(selector)
                for item in items[:2]:  # 🔥 Solo 2 items
                    title_elem = item.find(['h1', 'h2', 'h3']) or item.find('a')
                    title = title_elem.get_text(strip=True)[:80] if title_elem else None
                    
                    if not title or len(title) < 10:
                        continue
                    
                    link_elem = item.find('a', href=True)
                    link = link_elem.get('href') if link_elem else '#'
                    if link and not link.startswith('http'):
                        link = urljoin(url, link)
                    
                    p_elem = item.find('p')
                    summary = p_elem.get_text(strip=True)[:150] if p_elem else ''
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'published': None,
                        'source': url,
                        'source_url': url
                    })
                    
                    if len(articles) >= 1:  # 🔥 Solo 1 artículo por sitio
                        break
                
                if len(articles) >= 1:
                    break
            
            return articles[:1]  # 🔥 Máximo 1 artículo
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
        
        # Intentar RSS primero (más rápido)
        if source.get('rss'):
            articles = self.fetch_rss_feed(source['rss'])
            if articles:
                for article in articles:
                    article['source_name'] = name
                    article['source_type'] = source_type
                return articles
        
        # Scraping solo para websites
        if source_type in ['website', 'blog', 'media', 'news', 'government']:
            articles = self.fetch_website_news(url)
            for article in articles:
                article['source_name'] = name
                article['source_type'] = source_type
            return articles
        
        return []
    
    def fetch_country_news(self, country: Dict) -> Dict:
        """Obtiene todas las noticias de un país"""
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
        
        # 🔥 Reducir workers para evitar saturación
        actual_workers = min(self.max_workers, 2)  # Máximo 2 por país
        
        with ThreadPoolExecutor(max_workers=actual_workers) as executor:
            future_to_source = {
                executor.submit(self.fetch_source, source): source 
                for source in all_sources
            }
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    # 🔥 Timeout de 15s por tarea
                    articles = future.result(timeout=15)
                    if articles:
                        category = source.get('_category', 'general')
                        for article in articles:
                            article['country'] = country_name
                            article['country_code'] = country_code
                            article['category'] = category
                        all_articles.extend(articles)
                        print(f"  ✅ {source.get('name', '')}: {len(articles)} noticias")
                except Exception as e:
                    print(f"  ⚠️ {source.get('name', '')}: timeout/error")
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
        """Obtiene noticias de todos los países"""
        results = {}
        
        # 🔥 Procesar países secuencialmente (uno a la vez)
        for country in self.countries:
            try:
                result = self.fetch_country_news(country)
                results[country['code']] = result
                time.sleep(0.5)  # Pausa entre países
            except Exception as e:
                print(f"⚠️ Error con {country.get('name', 'Desconocido')}: {e}")
                results[country['code']] = {
                    'country': country.get('name', 'Desconocido'),
                    'code': country.get('code', 'XX'),
                    'articles': [],
                    'total': 0,
                    'sources_checked': 0
                }
        
        return results
    
    def get_latam_news(self) -> List[Dict]:
        """Obtiene noticias de fuentes latinoamericanas"""
        print(f"\n{'='*50}")
        print("🌎 Fuentes Latinoamericanas")
        print(f"{'='*50}")
        
        articles = []
        
        with ThreadPoolExecutor(max_workers=min(len(self.latam_sources), 2)) as executor:
            future_to_source = {
                executor.submit(self.fetch_source, source): source
                for source in self.latam_sources
            }
            
            for future in as_completed(future_to_source):
                try:
                    fetched = future.result(timeout=15)
                    for article in fetched:
                        article['country'] = 'Latinoamérica'
                        article['country_code'] = 'LATAM'
                        article['category'] = 'regional'
                    articles.extend(fetched)
                except Exception:
                    pass
        
        return articles


def get_cooperative_news(max_workers: int = 3) -> Dict:
    """Función principal para obtener todas las noticias cooperativas"""
    start_time = time.time()
    
    fetcher = CooperativeFetcher(max_workers=max_workers)
    
    print("🚀 INICIANDO AGENTE DE NOTICIAS COOPERATIVAS")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚡ Paralelismo: {max_workers} workers")
    print(f"⏱️ Timeouts agresivos: 5s conexión, 8s lectura")
    
    country_results = fetcher.fetch_all_countries()
    
    latam_news = fetcher.get_latam_news()
    country_results['LATAM'] = {
        'country': 'Latinoamérica',
        'code': 'LATAM',
        'articles': latam_news,
        'total': len(latam_news),
        'sources_checked': len(fetcher.latam_sources)
    }
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ Tiempo total: {elapsed:.1f} segundos")
    
    return country_results