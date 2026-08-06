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

# Deshabilitar advertencias de SSL (solo para sitios problemáticos)
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
        self.user_agent = self.settings.get("user_agent", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Crear sesión con configuración SSL mejorada
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Configuración SSL para sitios problemáticos
        self.session.verify = False  # Deshabilitar verificación SSL para sitios con certificados problemáticos
        
        # Timeouts
        self.timeout = 30
        self.max_retries = 3
        
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
                    verify=False,  # Deshabilitar verificación SSL
                    allow_redirects=True
                )
                response.raise_for_status()
                return response
            except requests.exceptions.SSLError as e:
                print(f"    ⚠️ Error SSL en {url}: {str(e)[:100]}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2)
            except requests.exceptions.ConnectionError as e:
                print(f"    ⚠️ Error de conexión en {url}: {str(e)[:100]}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(3)
            except requests.exceptions.Timeout:
                print(f"    ⚠️ Timeout en {url}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2)
            except Exception as e:
                print(f"    ⚠️ Error en {url}: {str(e)[:100]}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(2)
        return None
    
    def fetch_website_news(self, url: str) -> List[Dict]:
        """Extrae noticias de un sitio web con manejo de errores mejorado"""
        articles = []
        try:
            print(f"    🔍 Intentando conectar a {url}")
            response = self._safe_request(url)
            
            if not response:
                print(f"    ⚠️ No se pudo conectar a {url}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Selectores comunes para diferentes CMS
            selectors = [
                'article', '.post', '.news-item', '.noticia', 
                '.entry', '.blog-post', '.feed-item',
                '.item', '.story', '.content-item',
                '.noticias', '.articulo', '.contenido'
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
                    
                    if title and len(title) > 10:  # Filtrar títulos muy cortos
                        articles.append({
                            'title': title,
                            'link': link,
                            'summary': summary[:400],
                            'published': None,
                            'source': url,
                            'source_url': url
                        })
                
                if len(articles) >= 3:
                    break
            
            if articles:
                print(f"    ✅ {len(articles)} noticias extraídas")
            else:
                print(f"    ⚠️ No se encontraron noticias en la página")
            
            return articles[:3]
        except Exception as e:
            print(f"    ⚠️ Error al scrapear: {str(e)[:150]}")
            return []
    
    def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Obtiene artículos de un feed RSS con mejor manejo de errores"""
        try:
            # Usar la sesión con configuración SSL
            response = self._safe_request(url)
            if not response:
                return []
            
            # Parsear el feed
            feed = feedparser.parse(response.content)
            
            if feed.bozo:  # Si hay errores de parsing
                print(f"    ⚠️ Error en feed RSS: {feed.bozo_exception}")
            
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
            
            if articles:
                print(f"    ✅ {len(articles)} noticias (RSS)")
            return articles
        except Exception as e:
            print(f"    ⚠️ Error al consultar RSS: {str(e)[:150]}")
            return []