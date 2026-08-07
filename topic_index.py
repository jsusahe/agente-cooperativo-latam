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
        """Carga el índice desde Google Drive o local"""
        # Intentar cargar desde Drive primero
        if self.service and self.folder_id and GOOGLE_API_AVAILABLE:
            try:
                from googleapiclient.errors import HttpError
                
                query = f"name='{self.index_file}' and trashed=false and '{self.folder_id}' in parents"
                results = self.service.files().list(
                    q=query,
                    fields="files(id, name)",
                    pageSize=1
                ).execute()
                files = results.get('files', [])
                
                if files:
                    file_id = files[0]['id']
                    print(f"📥 Cargando índice desde Drive: {self.index_file}", flush=True)
                    
                    request = self.service.files().get_media(fileId=file_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    
                    fh.seek(0)
                    data = json.loads(fh.read().decode('utf-8'))
                    self.topics = data.get('topics', [])
                    self.tips = data.get('tips', [])
                    print(f"✅ Índice cargado desde Drive: {len(self.topics)} temas, {len(self.tips)} tips", flush=True)
                    return True
                    
            except Exception as e:
                print(f"⚠️ Error al cargar índice desde Drive: {e}", flush=True)
                # Continuar con carga local
        
        # Fallback: Cargar desde archivo local
        if os.path.exists(self.local_file):
            try:
                with open(self.local_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.topics = data.get('topics', [])
                    self.tips = data.get('tips', [])
                    print(f"✅ Índice cargado desde local: {len(self.topics)} temas, {len(self.tips)} tips", flush=True)
                    return True
            except Exception as e:
                print(f"⚠️ Error al cargar índice local: {e}", flush=True)
        
        # Si no hay índice, crear uno nuevo
        print("ℹ️ Creando nuevo índice de temas", flush=True)
        self.topics = []
        self.tips = []
        return True
    
    def save_to_drive(self) -> bool:
        """Guarda el índice en Google Drive y localmente"""
        # Siempre guardar localmente primero
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'total_topics': len(self.topics),
                'total_tips': len(self.tips),
                'topics': self.topics,
                'tips': self.tips
            }
            with open(self.local_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Índice guardado localmente: {len(self.topics)} temas, {len(self.tips)} tips", flush=True)
        except Exception as e:
            print(f"⚠️ Error al guardar índice local: {e}", flush=True)
            return False
        
        # Intentar guardar en Drive
        if not self.service or not self.folder_id or not GOOGLE_API_AVAILABLE:
            print("ℹ️ Drive no disponible, índice solo guardado localmente", flush=True)
            return True
        
        try:
            from googleapiclient.errors import HttpError
            
            data = {
                'last_updated': datetime.now().isoformat(),
                'total_topics': len(self.topics),
                'total_tips': len(self.tips),
                'topics': self.topics,
                'tips': self.tips
            }
            
            temp_file = f"{self.index_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            query = f"name='{self.index_file}' and trashed=false and '{self.folder_id}' in parents"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=1
            ).execute()
            files = results.get('files', [])
            
            media = MediaFileUpload(temp_file, mimetype='application/json')
            
            if files:
                file_id = files[0]['id']
                self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                print(f"✅ Índice actualizado en Drive: {self.index_file}", flush=True)
            else:
                file_metadata = {
                    'name': self.index_file,
                    'parents': [self.folder_id]
                }
                self.service.files().create(
                    body=file_metadata,
                    media_body=media
                ).execute()
                print(f"✅ Índice creado en Drive: {self.index_file}", flush=True)
            
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error al guardar índice en Drive: {e}", flush=True)
            return False  # Ya se guardó localmente
    
    def add_topic(self, topic: str, source: str = None) -> bool:
        """Agrega un tema al índice si no existe"""
        if not topic:
            return False
        
        topic_lower = topic.lower().strip()
        
        # Verificar si ya existe
        for t in self.topics:
            if t.get('topic', '').lower().strip() == topic_lower:
                return False
        
        # Agregar nuevo tema
        new_topic = {
            'topic': topic,
            'source': source or 'Desconocida',
            'date_added': datetime.now().isoformat()
        }
        self.topics.append(new_topic)
        return True
    
    def add_topics(self, topics: List[str], source: str = None) -> int:
        """Agrega múltiples temas al índice"""
        added = 0
        for topic in topics:
            if self.add_topic(topic, source):
                added += 1
        return added
    
    def topic_exists(self, topic: str) -> bool:
        """Verifica si un tema ya existe en el índice"""
        if not topic:
            return False
        topic_lower = topic.lower().strip()
        for t in self.topics:
            if t.get('topic', '').lower().strip() == topic_lower:
                return True
        return False
    
    def get_unseen_topics(self, topics: List[str]) -> List[str]:
        """Filtra temas que no están en el índice"""
        unseen = []
        for topic in topics:
            if topic and not self.topic_exists(topic):
                unseen.append(topic)
        return unseen
    
    def add_tip(self, tip_title: str, tip_text: str = None) -> bool:
        """Agrega un tip al índice si no existe"""
        if not tip_title:
            return False
        
        tip_lower = tip_title.lower().strip()
        
        # Verificar si ya existe (por título)
        for t in self.tips:
            if t.get('title', '').lower().strip() == tip_lower:
                return False
        
        # Agregar nuevo tip
        new_tip = {
            'title': tip_title,
            'text': tip_text or '',
            'date_added': datetime.now().isoformat()
        }
        self.tips.append(new_tip)
        return True
    
    def tip_exists(self, tip_title: str) -> bool:
        """Verifica si un tip ya existe en el índice"""
        if not tip_title:
            return False
        tip_lower = tip_title.lower().strip()
        for t in self.tips:
            if t.get('title', '').lower().strip() == tip_lower:
                return True
        return False
    
    def get_recent_topics(self, days: int = 30) -> List[Dict]:
        """Obtiene temas de los últimos N días"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = []
        for t in self.topics:
            try:
                date_added = datetime.fromisoformat(t.get('date_added', ''))
                if date_added >= cutoff:
                    recent.append(t)
            except:
                continue
        return recent
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del índice"""
        return {
            'total_topics': len(self.topics),
            'total_tips': len(self.tips),
            'last_updated': datetime.now().isoformat()
        }


def get_topic_index(service=None) -> TopicIndex:
    """Obtiene una instancia del índice de temas"""
    folder_id = os.environ.get('PARENT_FOLDER_ID')
    index = TopicIndex(service, folder_id)
    index.load_from_drive()
    return index