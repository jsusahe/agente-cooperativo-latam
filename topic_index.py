# topic_index.py - Módulo para gestionar índice de temas en Drive
import os
import json
import io
from datetime import datetime
from typing import List, Dict, Optional
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError


class TopicIndex:
    """Gestiona el índice de temas en Google Drive"""
    
    def __init__(self, service=None, folder_id=None):
        self.service = service
        self.folder_id = folder_id or os.environ.get('PARENT_FOLDER_ID')
        self.index_file = "topic_index.json"
        self.topics = []
        
    def load_from_drive(self) -> bool:
        """Carga el índice desde Google Drive"""
        if not self.service or not self.folder_id:
            print("⚠️ Servicio de Drive no disponible para cargar índice")
            return False
        
        try:
            # Buscar el archivo de índice
            query = f"name='{self.index_file}' and trashed=false and '{self.folder_id}' in parents"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=1
            ).execute()
            files = results.get('files', [])
            
            if not files:
                print("ℹ️ No se encontró índice de temas en Drive. Se creará uno nuevo.")
                self.topics = []
                return True
            
            file_id = files[0]['id']
            print(f"📥 Cargando índice desde Drive: {self.index_file}")
            
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            fh.seek(0)
            data = json.loads(fh.read().decode('utf-8'))
            self.topics = data.get('topics', [])
            print(f"✅ Índice cargado: {len(self.topics)} temas")
            return True
            
        except HttpError as e:
            print(f"⚠️ Error al cargar índice: {e}")
            return False
        except Exception as e:
            print(f"⚠️ Error al cargar índice: {e}")
            return False
    
    def save_to_drive(self) -> bool:
        """Guarda el índice en Google Drive"""
        if not self.service or not self.folder_id:
            print("⚠️ Servicio de Drive no disponible para guardar índice")
            return False
        
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'total_topics': len(self.topics),
                'topics': self.topics
            }
            
            # Crear archivo temporal
            temp_file = f"{self.index_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Buscar si ya existe
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
                # Actualizar archivo existente
                self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                print(f"✅ Índice actualizado en Drive: {self.index_file}")
            else:
                # Crear nuevo archivo
                file_metadata = {
                    'name': self.index_file,
                    'parents': [self.folder_id]
                }
                self.service.files().create(
                    body=file_metadata,
                    media_body=media
                ).execute()
                print(f"✅ Índice creado en Drive: {self.index_file}")
            
            # Limpiar archivo temporal
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error al guardar índice: {e}")
            return False
    
    def add_topic(self, topic: str, source: str = None) -> bool:
        """Agrega un tema al índice si no existe"""
        # Normalizar tema
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
        topic_lower = topic.lower().strip()
        for t in self.topics:
            if t.get('topic', '').lower().strip() == topic_lower:
                return True
        return False
    
    def get_unseen_topics(self, topics: List[str]) -> List[str]:
        """Filtra temas que no están en el índice"""
        unseen = []
        for topic in topics:
            if not self.topic_exists(topic):
                unseen.append(topic)
        return unseen
    
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
            'last_updated': datetime.now().isoformat()
        }


def get_topic_index(service=None) -> TopicIndex:
    """Obtiene una instancia del índice de temas"""
    folder_id = os.environ.get('PARENT_FOLDER_ID')
    index = TopicIndex(service, folder_id)
    index.load_from_drive()
    return index