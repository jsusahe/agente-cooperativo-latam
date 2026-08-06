# youtube_fetcher.py - Módulo para extraer videos de YouTube
import os
import json
import requests
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs


class YouTubeFetcher:
    """Extrae información de videos de YouTube"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('YOUTUBE_API_KEY')
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
    def extract_channel_id(self, url: str) -> Optional[str]:
        """Extrae el ID del canal desde una URL"""
        # Patrón para @username
        match = re.search(r'@([^/]+)', url)
        if match:
            username = match.group(1)
            if self.api_key:
                return self._get_channel_id_by_username(username)
            else:
                print(f"⚠️ Sin API Key, no se puede resolver @{username}")
                return None
        
        # Patrón para channel/ID
        match = re.search(r'channel/([^/?]+)', url)
        if match:
            return match.group(1)
        
        # Patrón para /c/ (nombre personalizado)
        match = re.search(r'/c/([^/?]+)', url)
        if match:
            return self._get_channel_id_by_username(match.group(1))
        
        return None
    
    def _get_channel_id_by_username(self, username: str) -> Optional[str]:
        """Obtiene el ID del canal por nombre de usuario"""
        if not self.api_key:
            return None
        
        try:
            search_url = f"{self.base_url}/search"
            params = {
                'part': 'snippet',
                'q': username,
                'type': 'channel',
                'maxResults': 1,
                'key': self.api_key
            }
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('items'):
                return data['items'][0]['snippet']['channelId']
        except Exception as e:
            print(f"⚠️ Error al obtener ID del canal: {e}")
        
        return None
    
    def get_videos(self, channel_id: str, max_results: int = 5) -> List[Dict]:
        """Obtiene videos de un canal"""
        if not self.api_key or not channel_id:
            return []
        
        try:
            # Obtener videos del canal
            search_url = f"{self.base_url}/search"
            params = {
                'part': 'snippet',
                'channelId': channel_id,
                'order': 'date',
                'type': 'video',
                'maxResults': max_results,
                'key': self.api_key
            }
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            videos = []
            for item in data.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']
                
                video_info = {
                    'id': video_id,
                    'title': snippet.get('title', 'Sin título'),
                    'description': snippet.get('description', ''),
                    'published_at': snippet.get('publishedAt'),
                    'channel': snippet.get('channelTitle', 'Desconocido'),
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', '')
                }
                
                # Intentar obtener estadísticas
                stats = self._get_video_stats(video_id)
                if stats:
                    video_info.update(stats)
                
                videos.append(video_info)
            
            return videos
            
        except Exception as e:
            print(f"⚠️ Error al obtener videos: {e}")
            return []
    
    def _get_video_stats(self, video_id: str) -> Dict:
        """Obtiene estadísticas de un video"""
        if not self.api_key:
            return {}
        
        try:
            url = f"{self.base_url}/videos"
            params = {
                'part': 'statistics',
                'id': video_id,
                'key': self.api_key
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('items'):
                stats = data['items'][0].get('statistics', {})
                return {
                    'views': stats.get('viewCount', '0'),
                    'likes': stats.get('likeCount', '0'),
                    'comments': stats.get('commentCount', '0')
                }
        except Exception:
            pass
        
        return {}


def fetch_youtube_content(channel_urls: List[str], max_videos: int = 3) -> List[Dict]:
    """Función principal para extraer contenido de YouTube"""
    fetcher = YouTubeFetcher()
    all_videos = []
    
    for url in channel_urls:
        channel_id = fetcher.extract_channel_id(url)
        if channel_id:
            videos = fetcher.get_videos(channel_id, max_videos)
            all_videos.extend(videos)
        else:
            print(f"⚠️ No se pudo extraer ID del canal: {url}")
    
    return all_videos


def save_videos_to_json(videos: List[Dict], filename: str = None):
    """Guarda videos en un archivo JSON"""
    if not filename:
        filename = f"youtube_content_{datetime.now().strftime('%Y-%m-%d')}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(videos, f, indent=4, ensure_ascii=False)
        print(f"✅ Videos guardados en {filename}")
    except Exception as e:
        print(f"⚠️ Error al guardar videos: {e}")