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
import urllib3

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CooperativeFetcher:
    """Clase para extraer noticias de fuentes cooperativas por país"""
    
    def __init__(self, config_file="config_countries.json"):
        self.config = self._load_config(config_file)
        self.countries = self.config.get("countries", [])
        self.latam_sources = self.config.get("latam_sources", [])
        self.settings = self.config.get("settings", {})
        self.min_news = self.settings.get("min_news_per_country", 5)
        self.days_back = self.settings.get("days_back", 3)
        self.timeout = self.settings.get("timeout", 30)
        self.max_retries = self.settings.get("max_retries", 3)
        self.user_agent = self.settings.get("user_agent", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Crear sesión con configuración SSL mejorada
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        self.session.verify = False
        
        # Headers adicionales para simular navegador real
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
    def _load_config(self, config_file: str) -> Dict:
        """Carga la configuración desde archivo JSON"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error al cargar configuración: {e}")
            return {"countries": []}
    
    def _safe_request(self, url: str) -> Optional[requests.Response]:
        """Realiza una solicitud HTTP con manejo de errores y reintentos"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url, 
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True
                )
                response.raise_for_status()
                return response
            except requests.exceptions.SSLError as e:
                print(f"    ⚠️ Error SSL en {url}: {str(e)[:100]}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2 ** attempt)  # Backoff exponencial
            except requests.exceptions.ConnectionError as e:
                print(f"    ⚠️ Error de conexión en {url}: {str(e)[:100]}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(3 ** attempt)
            except requests.exceptions.Timeout:
                print(f"    ⚠️ Timeout en {url}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2)
            except requests.exceptions.TooManyRedirects:
                print(f"    ⚠️ Demasiadas redirecciones en {url}")
                return None
            except Exception as e:
                print(f"    ⚠️ Error en {url}: {str(e)[:100]}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2)
        return None
    
    def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Obtiene artículos de un feed RSS"""
        try:
            response = self._safe_request(url)
            if not response:
                return []
            
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                print(f"    ⚠️ Error en feed RSS: {feed.bozo_exception}")
            
            articles = []
            cutoff_date = datetime.now() - timedelta(days=self.days_back)
            
            for entry in feed.entries[:self.settings.get("max_news_per_source", 3)]:
                published = entry.get('published_parsed') or entry.get('updated_parsed')
                if published:
                    pub_date = datetime(*published[:6])
                    if pub_date < cutoff_date:
                        continue
                
                summary = entry.get('summary', '')
                summary = re.sub(r'<[^>]+>', '', summary)
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
            
            if articles:
                print(f"    ✅ {len(articles)} noticias (RSS)")
            return articles
        except Exception as e:
            print(f"    ⚠️ Error al consultar RSS: {str(e)[:150]}")
            return []
    
    def fetch_website_news(self, url: str) -> List[Dict]:
        """Extrae noticias de un sitio web con selectores mejorados"""
        articles = []
        try:
            print(f"    🔍 Intentando conectar a {url}")
            response = self._safe_request(url)
            
            if not response:
                print(f"    ⚠️ No se pudo conectar a {url}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # ============================================
            # SELECTORES MEJORADOS - Más completos
            # ============================================
            selectors = [
                # Selectores HTML5 semánticos
                'article', 
                'section[class*="news"]',
                'section[class*="post"]',
                'section[class*="article"]',
                
                # Selectores por clase comunes en CMS
                '.post', 
                '.news-item', 
                '.noticia', 
                '.entry', 
                '.blog-post', 
                '.feed-item',
                '.item', 
                '.story', 
                '.content-item',
                '.noticias', 
                '.articulo', 
                '.contenido',
                '.card',
                '.col-md-12', 
                '.col-lg-8',
                '.col-sm-12',
                '.col-xs-12',
                
                # Selectores de WordPress
                '.post-content',
                '.entry-content',
                '.blog-content',
                '.article-content',
                '.news-content',
                '.content-area',
                '.main-content',
                
                # Selectores por clase con palabras clave
                'div[class*="news"]', 
                'div[class*="post"]',
                'div[class*="article"]',
                'div[class*="blog"]',
                'div[class*="noticia"]',
                
                # Selectores por ID (comunes en sitios de noticias)
                '#content',
                '#main',
                '#primary',
                '#post-content',
                '#article-content',
                '#news-content',
                '#blog-content',
                
                # Selectores de Bootstrap
                '.row > .col-md-12',
                '.row > .col-lg-8',
                '.container > .row > div',
                
                # Selectores de Joomla
                '.item-page',
                '.blog-item',
                '.newsflash',
                
                # Selectores de Drupal
                '.node',
                '.node-article',
                '.view-content',
                
                # Selectores de sitios gubernamentales
                '.noticia',
                '.comunicado',
                '.boletin',
                '.publicacion',
                '.informacion',
                
                # Selectores para fondos de empleados
                '.cooperativa',
                '.empleado',
                '.fondo',
                
                # Selectores para asociaciones solidaristas
                '.solidarista',
                '.asociacion'
            ]
            
            # Eliminar duplicados manteniendo orden
            seen = set()
            unique_selectors = []
            for s in selectors:
                if s not in seen:
                    seen.add(s)
                    unique_selectors.append(s)
            
            items_found = False
            for selector in unique_selectors:
                try:
                    items = soup.select(selector)
                    if items:
                        for item in items[:5]:
                            # Intentar extraer título
                            title_elem = (
                                item.find(['h1', 'h2', 'h3', 'h4']) or 
                                item.find('a', class_='title') or
                                item.find('a', class_='post-title') or
                                item.find('a', class_='entry-title') or
                                item.find('a', class_='article-title') or
                                item.find('a', class_='news-title') or
                                item.find('a')
                            )
                            title = title_elem.get_text(strip=True) if title_elem else 'Sin título'
                            
                            # Intentar extraer enlace
                            link_elem = item.find('a', href=True)
                            link = link_elem.get('href') if link_elem else '#'
                            if link and not link.startswith('http'):
                                link = requests.compat.urljoin(url, link)
                            
                            # Intentar extraer resumen
                            p_elem = item.find('p')
                            summary = p_elem.get_text(strip=True) if p_elem else ''
                            
                            # Intentar extraer fecha
                            date_elem = (
                                item.find('time') or
                                item.find(class_='date') or
                                item.find(class_='published') or
                                item.find(class_='post-date') or
                                item.find(class_='entry-date') or
                                item.find(class_='article-date')
                            )
                            published = None
                            if date_elem:
                                date_str = date_elem.get_text(strip=True)
                                try:
                                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%B %d, %Y', '%d de %B de %Y', '%d-%m-%Y']:
                                        try:
                                            published = datetime.strptime(date_str, fmt)
                                            break
                                        except:
                                            continue
                                except:
                                    pass
                            
                            # Filtrar títulos muy cortos o spam
                            if title and len(title) > 10 and not any(x in title.lower() for x in ['cookies', 'privacidad', 'suscribirse']):
                                articles.append({
                                    'title': title,
                                    'link': link,
                                    'summary': summary[:400],
                                    'published': published,
                                    'source': url,
                                    'source_url': url
                                })
                        
                        if len(articles) >= 3:
                            items_found = True
                            break
                except Exception as e:
                    continue
            
            if articles:
                print(f"    ✅ {len(articles)} noticias extraídas")
            else:
                # Último intento: buscar elementos con patrones de fecha
                print(f"    🔍 Buscando noticias por patrones...")
                for element in soup.find_all(['div', 'section', 'article']):
                    text = element.get_text(strip=True)
                    if len(text) > 50 and any(x in text.lower() for x in ['cooperativa', 'fondo', 'empleado', 'solidarista', 'confecoop', 'superintendencia']):
                        title_elem = element.find(['h1', 'h2', 'h3', 'h4'])
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            link_elem = element.find('a', href=True)
                            link = link_elem.get('href') if link_elem else '#'
                            if link and not link.startswith('http'):
                                link = requests.compat.urljoin(url, link)
                            if title and len(title) > 10:
                                articles.append({
                                    'title': title,
                                    'link': link,
                                    'summary': text[:400],
                                    'published': None,
                                    'source': url,
                                    'source_url': url
                                })
                            if len(articles) >= 3:
                                break
            
            return articles[:3]
        except Exception as e:
            print(f"    ⚠️ Error al scrapear: {str(e)[:150]}")
            return []
    
    def fetch_youtube_content(self, source: Dict) -> List[Dict]:
        """Obtiene contenido de canales de YouTube (placeholder)"""
        # Implementación futura si se tiene YOUTUBE_API_KEY
        print(f"    ⚠️ YouTube requiere autenticación (YOUTUBE_API_KEY)")
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
                return articles
        
        # Scraping para websites
        if source_type in ['website', 'blog', 'media', 'news', 'government']:
            articles = self.fetch_website_news(url)
            for article in articles:
                article['source_name'] = name
                article['source_type'] = source_type
            if articles:
                print(f"    ✅ {len(articles)} noticias (Scraping)")
            else:
                print(f"    ⚠️ No se obtuvieron noticias")
            return articles
        
        # YouTube (requiere API)
        if source_type == 'youtube':
            articles = self.fetch_youtube_content(source)
            return articles
        
        print(f"    ⚠️ Tipo no soportado: {source_type}")
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
                'youtube_channels': '📹 YouTube',
                'government': '🏛️ Gobierno'
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
                time.sleep(0.5)  # Pausa entre fuentes
        
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


# ============================================
# ✅ FUNCIÓN PRINCIPAL - EXPORTADA
# ============================================
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
            json.dump(country_results, f, indent=4, ensure_ascii=False, default=str)
        print(f"\n✅ Datos guardados en {output_file}")
    except Exception as e:
        print(f"⚠️ Error al guardar: {e}")
    
    return country_results


# ============================================
# ✅ FUNCIÓN PARA PRUEBAS
# ============================================
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