# cooperative_fetcher.py
import feedparser
import json
import os
import requests
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

class CooperativeFetcher:
    """Clase para extraer noticias de fuentes cooperativas por país"""
    
    def __init__(self, config_file="config_countries.json"):
        self.config = self._load_config(config_file)
        self.countries = self.config.get("countries", [])
        self.latam_sources = self.config.get("latam_sources", [])
        self.settings = self.config.get("settings", {})
        self.min_news = self.settings.get("min_news_per_country", 5)
        self.days_back = self.settings.get("days_back", 3)
        self.user_agent = self.settings.get("user_agent", "Mozilla/5.0")
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
    def _load_config(self, config_file: str) -> Dict:
        """Carga la configuración desde archivo JSON"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error al cargar configuración: {e}")
            return {"countries": []}
    
    def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Obtiene artículos de un feed RSS"""
        try:
            feed = feedparser.parse(url)
            articles = []
            cutoff_date = datetime.now() - timedelta(days=self.days_back)
            
            for entry in feed.entries[:self.settings.get("max_news_per_source", 3)]:
                published = entry.get('published_parsed') or entry.get('updated_parsed')
                if published:
                    pub_date = datetime(*published[:6])
                    if pub_date < cutoff_date:
                        continue
                
                # Limpiar summary
                summary = entry.get('summary', '')
                summary = re.sub(r'<[^>]+>', '', summary)  # Remover HTML
                summary = summary[:400]
                
                articles.append({
                    'title': entry.get('title', 'Sin título'),
                    'link': entry.get('link', '#'),
                    'summary': summary,
                    'description': entry.get('description', ''),
                    'published': published,
                    'source': feed.feed.get('title', 'Fuente desconocida'),
                    'source_url': url
                })
            return articles
        except Exception as e:
            print(f"  ⚠️ Error al consultar RSS {url}: {e}")
            return []
    
    def fetch_website_news(self, url: str) -> List[Dict]:
        """Extrae noticias de un sitio web (scraping)"""
        articles = []
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Selectores comunes para diferentes CMS
            selectors = [
                'article', '.post', '.news-item', '.noticia', 
                '.entry', '.blog-post', '.feed-item',
                '.item', '.story', '.content-item'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                for item in items[:5]:
                    # Título
                    title_elem = (item.find(['h1', 'h2', 'h3', 'h4']) or 
                                 item.find('a'))
                    title = title_elem.get_text(strip=True) if title_elem else 'Sin título'
                    
                    # Enlace
                    link_elem = item.find('a', href=True)
                    link = link_elem.get('href') if link_elem else '#'
                    if link and not link.startswith('http'):
                        link = requests.compat.urljoin(url, link)
                    
                    # Resumen
                    p_elem = item.find('p')
                    summary = p_elem.get_text(strip=True) if p_elem else ''
                    
                    # Fecha
                    date_elem = item.find(['time', '.date', '.published'])
                    published = None
                    if date_elem:
                        date_str = date_elem.get_text(strip=True)
                        # Intentar parsear fecha
                        try:
                            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%B %d, %Y', '%d de %B de %Y']:
                                try:
                                    published = datetime.strptime(date_str, fmt)
                                    break
                                except:
                                    continue
                        except:
                            pass
                    
                    if title and len(title) > 10:  # Filtrar títulos cortos
                        articles.append({
                            'title': title,
                            'link': link,
                            'summary': summary[:400],
                            'published': published,
                            'source': url,
                            'source_url': url
                        })
                
                if len(articles) >= 3:
                    break
            
            return articles[:3]
        except Exception as e:
            print(f"  ⚠️ Error al scrapear {url}: {e}")
            return []
    
    def fetch_source(self, source: Dict) -> List[Dict]:
        """Obtiene noticias de una fuente según su tipo"""
        source_type = source.get('type', 'website')
        url = source.get('url', '')
        name = source.get('name', 'Desconocido')
        
        if not url:
            return []
        
        print(f"    🔍 {name}")
        articles = []
        
        # Intentar RSS primero
        if source.get('rss'):
            articles = self.fetch_rss_feed(source['rss'])
            if articles:
                for article in articles:
                    article['source_name'] = name
                    article['source_type'] = source_type
                print(f"      ✅ {len(articles)} noticias (RSS)")
                return articles
        
        # Scraping para websites
        if source_type in ['website', 'blog', 'media']:
            articles = self.fetch_website_news(url)
            for article in articles:
                article['source_name'] = name
                article['source_type'] = source_type
            if articles:
                print(f"      ✅ {len(articles)} noticias (Scraping)")
            else:
                print(f"      ⚠️ No se obtuvieron noticias")
            return articles
        
        print(f"      ⚠️ Tipo no soportado: {source_type}")
        return []
    
    def fetch_country_news(self, country: Dict) -> Dict:
        """Obtiene todas las noticias de un país"""
        country_name = country.get('name', 'Desconocido')
        country_code = country.get('code', 'XX')
        sources = country.get('sources', {})
        
        print(f"\n{'='*60}")
        print(f"🇨🇴 Procesando {country_name} ({country_code})")
        print(f"{'='*60}")
        
        all_articles = []
        total_sources = 0
        
        for category, source_list in sources.items():
            category_display = {
                'supervision': '🏛️ Supervisión',
                'national_associations': '🏢 Confederaciones Nacionales',
                'regional_associations': '📌 Confederaciones Regionales',
                'employee_funds': '💼 Fondos de Empleados',
                'insurance_guarantee': '🛡️ Garantías',
                'cooperatives': '🏪 Cooperativas',
                'media': '📰 Medios',
                'solidarist_associations': '🤝 Asociaciones Solidaristas',
                'youtube_channels': '📹 YouTube'
            }.get(category, f'📂 {category}')
            
            print(f"\n  {category_display}")
            
            for source in source_list:
                total_sources += 1
                articles = self.fetch_source(source)
                if articles:
                    for article in articles:
                        article['country'] = country_name
                        article['country_code'] = country_code
                        article['category'] = category
                    all_articles.extend(articles)
                time.sleep(0.3)
        
        print(f"\n📊 Total para {country_name}: {len(all_articles)} noticias de {total_sources} fuentes")
        return {
            'country': country_name,
            'code': country_code,
            'articles': all_articles,
            'total': len(all_articles),
            'sources_checked': total_sources
        }
    
    def fetch_all_countries(self) -> Dict:
        """Obtiene noticias de todos los países configurados"""
        results = {}
        for country in self.countries:
            country_data = self.fetch_country_news(country)
            results[country['code']] = country_data
            time.sleep(2)  # Pausa entre países
        return results
    
    def get_latam_news(self) -> List[Dict]:
        """Obtiene noticias de fuentes latinoamericanas"""
        print(f"\n{'='*60}")
        print("🌎 Procesando fuentes Latinoamericanas")
        print(f"{'='*60}")
        
        articles = []
        for source in self.latam_sources:
            fetched = self.fetch_source(source)
            for article in fetched:
                article['country'] = 'Latinoamérica'
                article['country_code'] = 'LATAM'
                article['category'] = 'regional'
            articles.extend(fetched)
            time.sleep(0.5)
        
        return articles


def get_cooperative_news() -> Dict:
    """Función principal para obtener todas las noticias cooperativas"""
    fetcher = CooperativeFetcher()
    
    print("🚀 INICIANDO AGENTE DE NOTICIAS COOPERATIVAS")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 Países: {', '.join([c['name'] for c in fetcher.countries])}")
    
    # Obtener noticias por país
    country_results = fetcher.fetch_all_countries()
    
    # Obtener noticias regionales
    latam_news = fetcher.get_latam_news()
    country_results['LATAM'] = {
        'country': 'Latinoamérica',
        'code': 'LATAM',
        'articles': latam_news,
        'total': len(latam_news),
        'sources_checked': len(fetcher.latam_sources)
    }
    
    # Guardar resultados
    output_file = f"cooperative_news_{datetime.now().strftime('%Y-%m-%d')}.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(country_results, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Datos guardados en {output_file}")
    except Exception as e:
        print(f"⚠️ Error al guardar: {e}")
    
    return country_results


if __name__ == '__main__':
    print("=== PRUEBA DE COOPERATIVE_FETCHER ===")
    results = get_cooperative_news()
    
    print("\n📊 RESUMEN DE NOTICIAS POR PAÍS:")
    print("-" * 50)
    for code, data in results.items():
        if code == 'LATAM':
            continue
        print(f"{data.get('country', 'Desconocido')} ({code}): {data.get('total', 0)} noticias")
    print(f"\n🌎 Latinoamérica: {results.get('LATAM', {}).get('total', 0)} noticias")