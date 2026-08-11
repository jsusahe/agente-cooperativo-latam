# topic_index.py - Módulo para gestionar índice de temas en Drive
import os
import json
import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 🔥 Verificar dependencias de Google
try:
    from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("⚠️ Google API no disponible. La funcionalidad de Drive estará limitada.")


class TopicIndex:
    """Gestiona el índice de temas en Google Drive"""
    
    def __init__(self, service=None, folder_id=None):
        self.service = service
        self.folder_id = folder_id or os.environ.get('PARENT_FOLDER_ID')
        self.index_file = "topic_index.json"
        self.topics = []
        self.tips = []
        self.local_file = "topic_index_local.json"
        
    def load_from_drive(self) -> bool:
        # ... (código existente) ...
        # (Mantener el código de carga existente)
        pass
        
    def save_to_drive(self) -> bool:
        # ... (código existente) ...
        pass
    
    def add_topic(self, topic: str, source: str = None) -> bool:
        # ... (código existente) ...
        pass
    
    def topic_exists(self, topic: str) -> bool:
        # ... (código existente) ...
        pass
    
    def get_unseen_topics(self, topics: List[str]) -> List[str]:
        # ... (código existente) ...
        pass
    
    def add_tip(self, tip_title: str, tip_text: str = None) -> bool:
        # ... (código existente) ...
        pass
    
    def tip_exists(self, tip_title: str) -> bool:
        # ... (código existente) ...
        pass
    
    def get_recent_topics(self, days: int = 30) -> List[Dict]:
        # ... (código existente) ...
        pass
    
    def get_stats(self) -> Dict:
        # ... (código existente) ...
        pass

    # ===== NUEVO MÉTODO =====
    def get_recent_news(self, country_code: str, limit: int = 2) -> List[Dict]:
        """
        🔥 Recupera las últimas noticias almacenadas en el índice para un país específico.
        Esto sirve como contenido de respaldo cuando no hay noticias nuevas.
        """
        # En este ejemplo, asumimos que las noticias se guardan como "temas" con la fuente como el país.
        # Si se guardan en otro lugar, se debe ajustar la lógica.
        # Buscamos en los temas (topics) que tengan el país como fuente.
        recent_news = []
        for topic in self.topics:
            if topic.get('source') == country_code or topic.get('source') == 'Desconocida':
                recent_news.append({
                    'title': topic.get('topic', 'Sin título'),
                    'source_name': topic.get('source', 'Fuente desconocida'),
                    'summary': 'Contenido recuperado del archivo histórico.',
                    'link': '#',
                    'category': 'historical'
                })
                if len(recent_news) >= limit:
                    break
        return recent_news