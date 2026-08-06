# content_fetcher.py - Módulo para extraer contenido general de sitios web
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime


def fetch_website_content(url: str, max_length: int = 2000) -> Optional[Dict]:
    """
    Extrae contenido general de un sitio web (no solo noticias)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remover scripts y estilos
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extraer título
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else ""
        
        # Extraer meta descripción
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ""
        
        # Extraer contenido principal
        content_selectors = [
            'main', 'article', '.content', '.main-content', 
            '.post-content', '.entry-content', '.article-content'
        ]
        
        main_content = ""
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                main_content = element.get_text(strip=True)
                break
        
        # Si no se encontró contenido con selectores, tomar todo el body
        if not main_content:
            body = soup.find('body')
            if body:
                main_content = body.get_text(strip=True)
        
        # Limpiar y limitar contenido
        main_content = re.sub(r'\s+', ' ', main_content).strip()[:max_length]
        
        # Extraer palabras clave (topics)
        words = main_content.split()[:100]
        topics = []
        for word in words:
            if len(word) > 3 and word not in ['que', 'para', 'como', 'por', 'con', 'sin', 'sobre']:
                topics.append(word.lower())
        
        # Tomar las palabras más frecuentes como temas
        from collections import Counter
        topic_counter = Counter(topics)
        common_topics = [t for t, c in topic_counter.most_common(10) if c > 1]
        
        return {
            'title': title_text[:200],
            'description': description[:300],
            'content': main_content,
            'topics': common_topics,
            'url': url,
            'fetched_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"⚠️ Error al extraer contenido de {url}: {e}")
        return None


def extract_content_from_sources(sources: List[Dict], limit: int = 3) -> List[Dict]:
    """
    Extrae contenido de una lista de fuentes
    """
    results = []
    for source in sources[:limit]:
        url = source.get('url')
        name = source.get('name', 'Desconocido')
        if url:
            content = fetch_website_content(url)
            if content:
                content['source_name'] = name
                results.append(content)
    return results