# cooperative_fetcher.py - VERSIÓN CON INTEGRACIÓN DE REDES SOCIALES
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

# 🔥 Importamos el módulo de YouTube
from youtube_fetcher import YouTubeFetcher

# Deshabilitar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CooperativeFetcher:
    def __init__(self, config_file="config_countries.json", max_workers=1):
        self.config = self._load_config(config_file)
        self.countries = self.config.get("countries", [])
        self.latam_sources = self.config.get("latam_sources", [])
        self.settings = self.config.get("settings", {})
        self.min_news = self.settings.get("min_news_per_country", 3)
        self.days_back = self.settings.get("days_back", 3)
        self.timeout = 10
        self.max_retries = 1
        self.max_workers = max_workers
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        
        # 🔥 Inicializar fetcher de YouTube
        self.youtube_fetcher = YouTubeFetcher()
        
        # 🔥 Configuración de Facebook Graph API
        self.fb_access_token = os.environ.get('FACEBOOK_ACCESS_TOKEN')
        self.fb_graph_url = "https://graph.facebook.com/v18.0"
        
    def _load_config(self, config_file: str) -> Dict:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error al cargar configuración: {e}")
            return {"countries": []}
    
    def _safe_request(self, url: str) -> Optional[requests.Response]:
        """Realiza una solicitud HTTP con timeouts cortos"""
        try:
            response = requests.get(
                url, 
                timeout=(5, 8),
                verify=False,
                allow_redirects=True,
                headers={'User-Agent': self.user_agent}
            )
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"    ⏱️ Error en {url[:50]}...: {str(e)[:30]}")
            return None
    
    def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Obtiene artículos de un feed RSS"""
        try:
            response = self._safe_request(url)
            if not response:
                return []
            
            feed = feedparser.parse(response.content[:30000])
            if feed.bozo:
                return []
            
            articles = []
            cutoff_date = datetime.now() - timedelta(days=self.days_back)
            
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
        """Extrae noticias de un sitio web"""
        articles = []
        try:
            response = self._safe_request(url)
            if not response:
                return []
            
            soup = BeautifulSoup(response.content[:100000], 'html.parser')
            
            selectors = ['article', '.post', '.news-item', '.noticia']
            
            for selector in selectors:
                items = soup.select(selector)
                for item in items[:2]:
                    title_elem = item.find(['h1', 'h2', 'h3']) or item.find('a')
                    title = title_elem.get_text(strip=True)[:80] if title_elem else None
                    
                    if not title or len(title) < 10:
                        continue
                    
                    link_elem = item.find('a', href=True)
                    link = link_elem.get('href') if link_elem else '#'
                    if link and not link.startswith('http'):
                        from urllib.parse import urljoin
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
                    
                    if len(articles) >= 1:
                        break
                
                if len(articles) >= 1:
                    break
            
            return articles[:1]
        except Exception:
            return []

    # ==========================================================
    # 🔥 NUEVOS MÉTODOS PARA REDES SOCIALES
    # ==========================================================

    def fetch_youtube_channel(self, channel_url: str) -> List[Dict]:
        """Obtiene los últimos videos de un canal de YouTube"""
        try:
            channel_id = self.youtube_fetcher.extract_channel_id(channel_url)
            if not channel_id:
                print(f"    ⚠️ No se pudo extraer ID del canal: {channel_url}")
                return []
            
            videos = self.youtube_fetcher.get_videos(channel_id, max_results=3)
            articles = []
            for video in videos:
                # 🔥 Convertir el formato de YouTube al formato interno del agente
                articles.append({
                    'title': video.get('title', 'Sin título'),
                    'link': video.get('url', '#'),
                    'summary': video.get('description', '')[:200],
                    'published': video.get('published_at'),
                    'source': video.get('channel', 'Canal de YouTube'),
                    'source_url': channel_url,
                    'media_type': 'video'
                })
            return articles
        except Exception as e:
            print(f"    ❌ Error al obtener videos de YouTube: {e}")
            return []

    def fetch_facebook_page(self, page_url: str) -> List[Dict]:
        """
        Obtiene las últimas publicaciones de una página de Facebook.
        Requiere un token de acceso de página (FACEBOOK_ACCESS_TOKEN).
        """
        if not self.fb_access_token:
            print("    ⚠️ FACEBOOK_ACCESS_TOKEN no configurado. Saltando Facebook.")
            return []
        
        try:
            # Extraer el nombre de usuario o ID de la página de la URL
            # Ejemplo: https://www.facebook.com/confecoopcoop/
            match = re.search(r'facebook\.com/([^/?]+)', page_url)
            if not match:
                print(f"    ⚠️ URL de Facebook no reconocida: {page_url}")
                return []
            
            page_id_or_username = match.group(1)
            
            # Llamar a la API de Graph para obtener las publicaciones
            params = {
                'fields': 'message,permalink_url,created_time,full_picture',
                'access_token': self.fb_access_token,
                'limit': 5
            }
            
            url = f"{self.fb_graph_url}/{page_id_or_username}/posts"
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for post in data.get('data', []):
                message = post.get('message', '')
                if not message:
                    continue
                
                # 🔥 Extraer el primer enlace del mensaje si existe
                link_match = re.search(r'(https?://[^\s]+)', message)
                link = link_match.group(0) if link_match else post.get('permalink_url', '#')
                
                articles.append({
                    'title': message[:80],
                    'link': link,
                    'summary': message[:200],
                    'published': post.get('created_time'),
                    'source': 'Facebook',
                    'source_url': page_url,
                    'media_type': 'social'
                })
            
            return articles
        except Exception as e:
            print(f"    ❌ Error al obtener publicaciones de Facebook: {e}")
            return []

    def fetch_instagram_page(self, page_url: str) -> List[Dict]:
        """
        Obtiene las últimas publicaciones de una cuenta de Instagram.
        Requiere un token de acceso de usuario de Instagram (FACEBOOK_ACCESS_TOKEN).
        """
        if not self.fb_access_token:
            print("    ⚠️ FACEBOOK_ACCESS_TOKEN no configurado. Saltando Instagram.")
            return []
        
        try:
            # Extraer el nombre de usuario de la URL
            # Ejemplo: https://www.instagram.com/confecoop/
            match = re.search(r'instagram\.com/([^/?]+)', page_url)
            if not match:
                print(f"    ⚠️ URL de Instagram no reconocida: {page_url}")
                return []
            
            username = match.group(1)
            
            # 🔥 Instagram Basic Display API requiere un proceso de autenticación diferente.
            # Por simplicidad, usamos scraping básico si no hay token de Instagram.
            # Esta es una solución temporal.
            articles = self._scrape_instagram(username)
            return articles
        except Exception as e:
            print(f"    ❌ Error al obtener publicaciones de Instagram: {e}")
            return []

    def _scrape_instagram(self, username: str) -> List[Dict]:
        """
        Scraping básico de Instagram (sin autenticación).
        Útil para obtener las últimas publicaciones sin token.
        """
        try:
            url = f"https://www.instagram.com/{username}/feed/?__a=1&__d=1"
            response = self._safe_request(url)
            if not response:
                return []
            
            data = response.json()
            items = data.get('data', {}).get('user', {}).get('edge_owner_to_timeline_media', {}).get('edges', [])
            
            articles = []
            for edge in items[:3]:
                node = edge.get('node', {})
                caption = node.get('edge_media_to_caption', {}).get('edges', [])
                text = caption[0].get('node', {}).get('text', '') if caption else ''
                
                articles.append({
                    'title': text[:80] if text else 'Publicación de Instagram',
                    'link': f"https://www.instagram.com/p/{node.get('shortcode', '')}",
                    'summary': text[:200],
                    'published': datetime.fromtimestamp(node.get('taken_at_timestamp', time.time())).isoformat(),
                    'source': 'Instagram',
                    'source_url': url,
                    'media_type': 'social'
                })
            
            return articles
        except Exception:
            return []

    # ==========================================================
    # FIN DE NUEVOS MÉTODOS
    # ==========================================================

    def fetch_source(self, source: Dict) -> List[Dict]:
        """Obtiene noticias de una fuente (web, RSS, YouTube, Facebook, Instagram)"""
        source_type = source.get('type', 'website')
        url = source.get('url', '')
        name = source.get('name', 'Desconocido')
        
        if not url:
            return []
        
        articles = []
        
        # 🔥 Manejo de YouTube
        if source_type == 'youtube':
            print(f"    ▶️ Obteniendo videos de YouTube: {name}")
            return self.fetch_youtube_channel(url)
        
        # 🔥 Manejo de Facebook
        if source_type == 'facebook':
            print(f"    📘 Obteniendo publicaciones de Facebook: {name}")
            return self.fetch_facebook_page(url)
        
        # 🔥 Manejo de Instagram
        if source_type == 'instagram':
            print(f"    📸 Obteniendo publicaciones de Instagram: {name}")
            return self.fetch_instagram_page(url)
        
        # Intentar RSS primero
        if source.get('rss'):
            articles = self.fetch_rss_feed(source['rss'])
            if articles:
                for article in articles:
                    article['source_name'] = name
                    article['source_type'] = source_type
                return articles
        
        # Scraping
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
        
        for idx, source in enumerate(all_sources):
            try:
                name = source.get('name', 'Desconocido')
                print(f"  [{idx+1}/{len(all_sources)}] 🔍 {name}")
                articles = self.fetch_source(source)
                
                if articles:
                    category = source.get('_category', 'general')
                    for article in articles:
                        article['country'] = country_name
                        article['country_code'] = country_code
                        article['category'] = category
                    all_articles.extend(articles)
                    print(f"    ✅ {len(articles)} elementos")
                else:
                    print(f"    ⚠️ Sin contenido")
                    
            except Exception as e:
                print(f"    ❌ Error: {str(e)[:50]}")
            
            time.sleep(0.5)
        
        print(f"📊 {len(all_articles)} elementos encontrados")
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
        
        for country in self.countries:
            try:
                print(f"\n🌍 Procesando {country.get('name', 'Desconocido')}...")
                result = self.fetch_country_news(country)
                results[country['code']] = result
                time.sleep(1)
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
        for source in self.latam_sources:
            try:
                name = source.get('name', 'Desconocido')
                print(f"  🔍 {name}")
                fetched = self.fetch_source(source)
                for article in fetched:
                    article['country'] = 'Latinoamérica'
                    article['country_code'] = 'LATAM'
                    article['category'] = 'regional'
                articles.extend(fetched)
                print(f"    ✅ {len(fetched)} elementos")
            except Exception as e:
                print(f"    ❌ Error: {e}")
            time.sleep(0.5)
        
        return articles


def get_cooperative_news(max_workers: int = 1) -> Dict:
    """Función principal para obtener todas las noticias cooperativas"""
    start_time = time.time()
    
    fetcher = CooperativeFetcher(max_workers=max_workers)
    
    print("🚀 INICIANDO AGENTE DE NOTICIAS COOPERATIVAS")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚡ Procesamiento secuencial (estable)")
    
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