# drive_uploader.py - VERSION COMPLETA CON SUBIDA Y DESCARGA
import os
import pickle
import time
import io
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

# --- CONFIGURACIÓN ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
PARENT_FOLDER_ID = os.environ.get('PARENT_FOLDER_ID')
MAX_RETRIES = 3
# ---------------------

def authenticate_drive():
    """Autentica con Google Drive y devuelve el servicio."""
    print("🔐 Autenticando con Google Drive...", flush=True)
    
    creds = None
    token_file = 'token.json'
    credentials_file = 'credentials.json'
    
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            if creds and creds.valid:
                print("✅ Credenciales cargadas desde token.json", flush=True)
                return build('drive', 'v3', credentials=creds)
            elif creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("✅ Token refrescado correctamente", flush=True)
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
                    return build('drive', 'v3', credentials=creds)
                except Exception as e:
                    print(f"⚠️ Error al refrescar token: {e}", flush=True)
                    if os.path.exists(token_file):
                        os.remove(token_file)
            else:
                print("⚠️ Credenciales inválidas, se eliminará token.json", flush=True)
                if os.path.exists(token_file):
                    os.remove(token_file)
        except Exception as e:
            print(f"⚠️ Error al cargar token.json: {e}", flush=True)
            if os.path.exists(token_file):
                os.remove(token_file)
    
    if not os.path.exists(credentials_file):
        print(f"❌ Error: No se encuentra el archivo '{credentials_file}'.", flush=True)
        return None
    
    try:
        print("🔐 Iniciando flujo de autenticación OAuth...", flush=True)
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        try:
            print("   Intentando autenticación sin navegador (headless)...", flush=True)
            creds = flow.run_console()
            print("✅ Autenticación headless exitosa", flush=True)
        except Exception as e:
            print(f"⚠️ Error en autenticación headless: {e}", flush=True)
            print("   Intentando autenticación con navegador...", flush=True)
            creds = flow.run_local_server(port=0)
            print("✅ Autenticación con navegador exitosa", flush=True)
        
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Credenciales guardadas en {token_file}", flush=True)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Error en el flujo OAuth: {e}", flush=True)
        return None

def upload_file_to_drive(service, filename, filepath, mime_type, retry_count=0):
    """Sube un archivo a Google Drive con reintentos."""
    if not service:
        print("❌ Servicio de Drive no disponible.", flush=True)
        return None
    if not os.path.exists(filepath):
        print(f"⚠️ Archivo no encontrado: {filepath}", flush=True)
        return None
    
    try:
        file_metadata = {'name': filename}
        if PARENT_FOLDER_ID:
            file_metadata['parents'] = [PARENT_FOLDER_ID]
            print(f"📁 Subiendo a carpeta con ID: {PARENT_FOLDER_ID[:20]}...", flush=True)
        else:
            print(f"📁 Subiendo a la raíz de Drive", flush=True)
        
        media = MediaFileUpload(filepath, mimetype=mime_type, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, webContentLink'
        ).execute()
        file_id = file.get('id')
        print(f"✅ Archivo subido a Drive: {filename} (ID: {file_id[:10]}...)", flush=True)
        
        # Hacer público
        try:
            permission = {'type': 'anyone', 'role': 'reader'}
            service.permissions().create(fileId=file_id, body=permission, fields='id').execute()
            print(f"   🔓 Archivo {file_id[:10]}... configurado como público", flush=True)
        except Exception as e:
            print(f"   ⚠️ No se pudo hacer público: {e}", flush=True)
        
        return file_id
    except HttpError as error:
        if error.resp.status in [429, 500, 503] and retry_count < MAX_RETRIES:
            wait_time = (retry_count + 1) * 5
            print(f"⏳ Reintentando en {wait_time} segundos...", flush=True)
            time.sleep(wait_time)
            return upload_file_to_drive(service, filename, filepath, mime_type, retry_count + 1)
        print(f"❌ Error al subir {filename}: {error}", flush=True)
        return None
    except Exception as e:
        print(f"❌ Error inesperado al subir {filename}: {e}", flush=True)
        return None

def download_specific_file(service, filename: str, destination: str = None) -> bool:
    """Descarga un archivo específico desde Drive."""
    if not service:
        print("❌ Servicio de Drive no disponible.", flush=True)
        return False
    
    if not destination:
        destination = filename
    
    try:
        query = f"name='{filename}' and trashed=false"
        if PARENT_FOLDER_ID:
            query += f" and '{PARENT_FOLDER_ID}' in parents"
        
        results = service.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=1
        ).execute()
        files = results.get('files', [])
        
        if not files:
            print(f"⚠️ Archivo no encontrado en Drive: {filename}", flush=True)
            return False
        
        file_id = files[0]['id']
        print(f"📥 Descargando {filename} desde Drive...", flush=True)
        
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"   Progreso: {int(status.progress() * 100)}%", flush=True)
        
        print(f"✅ Archivo descargado: {destination}", flush=True)
        return True
        
    except HttpError as error:
        print(f"❌ Error al descargar {filename}: {error}", flush=True)
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}", flush=True)
        return False

def download_history_from_drive(history_folder="historial_cooperativo"):
    """Descarga todos los archivos históricos desde Drive."""
    print("\n📥 Descargando históricos desde Google Drive...", flush=True)
    
    service = authenticate_drive()
    if not service:
        print("❌ No se pudo autenticar con Google Drive.", flush=True)
        return False
    
    query = (
        "trashed=false and ("
        "name contains 'resumen_' or "
        "name contains 'cooperativo_' or "
        "name contains 'audio_'"
        ") and ("
        "mimeType='text/html' or "
        "mimeType='audio/mpeg'"
        ")"
    )
    
    if PARENT_FOLDER_ID:
        query += f" and '{PARENT_FOLDER_ID}' in parents"
    
    try:
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, modifiedTime)",
            pageSize=100
        ).execute()
        files = results.get('files', [])
        print(f"📁 Encontrados {len(files)} archivos en Drive.", flush=True)
        
        if not files:
            print("ℹ️ No hay archivos históricos en Drive para descargar.", flush=True)
            return True
        
        os.makedirs(history_folder, exist_ok=True)
        
        downloaded_count = 0
        skipped_count = 0
        
        for file in files:
            file_id = file['id']
            filename = file['name']
            filepath = os.path.join(history_folder, filename)
            
            if os.path.exists(filepath):
                print(f"⏭️ {filename} ya existe localmente, saltando.", flush=True)
                skipped_count += 1
                continue
            
            print(f"📥 Descargando: {filename}", flush=True)
            try:
                request = service.files().get_media(fileId=file_id)
                fh = io.FileIO(filepath, 'wb')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    print(f"   Progreso: {int(status.progress() * 100)}%", flush=True)
                print(f"✅ Descargado: {filename}", flush=True)
                downloaded_count += 1
            except Exception as e:
                print(f"   ❌ Error descargando {filename}: {e}", flush=True)
        
        print(f"✅ {downloaded_count} archivos descargados, {skipped_count} saltados a {history_folder}/", flush=True)
        return True
        
    except HttpError as error:
        print(f"❌ Error al listar archivos en Drive: {error}", flush=True)
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}", flush=True)
        return False

def upload_daily_document(html_file, audio_file=None):
    """Sube los archivos del día a Google Drive."""
    print("\n☁️ Iniciando subida a Google Drive...", flush=True)
    service = authenticate_drive()
    if not service:
        print("❌ No se pudo autenticar con Google Drive.", flush=True)
        return None
    
    results = {}
    if html_file and os.path.exists(html_file):
        filename = os.path.basename(html_file)
        file_id = upload_file_to_drive(service, filename, html_file, 'text/html')
        if file_id:
            results['html'] = {'id': file_id, 'name': filename}
    
    if audio_file and os.path.exists(audio_file):
        filename = os.path.basename(audio_file)
        file_id = upload_file_to_drive(service, filename, audio_file, 'audio/mpeg')
        if file_id:
            results['audio'] = {'id': file_id, 'name': filename}
    
    return results if results else None

def upload_history_folder(history_folder="historial", max_files=10):
    """Sube los archivos más recientes del histórico a Drive."""
    if not os.path.exists(history_folder):
        print(f"⚠️ Carpeta '{history_folder}' no encontrada.", flush=True)
        return []
    
    html_files = []
    for f in os.listdir(history_folder):
        if (f.startswith("resumen_") or f.startswith("cooperativo_")) and f.endswith(".html"):
            try:
                date_str = f.replace("resumen_", "").replace("cooperativo_", "").replace(".html", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                html_files.append((file_date, f))
            except ValueError:
                continue
    
    html_files.sort(key=lambda x: x[0], reverse=True)
    files_to_upload = html_files[:max_files]
    
    if not files_to_upload:
        print("ℹ️ No hay archivos en el histórico para subir.", flush=True)
        return []
    
    service = authenticate_drive()
    if not service:
        return []
    
    uploaded = []
    for _, filename in files_to_upload:
        filepath = os.path.join(history_folder, filename)
        file_id = upload_file_to_drive(service, filename, filepath, 'text/html')
        if file_id:
            uploaded.append(filename)
            audio_file = filepath.replace(".html", ".mp3")
            if os.path.exists(audio_file):
                audio_name = os.path.basename(audio_file)
                upload_file_to_drive(service, audio_name, audio_file, 'audio/mpeg')
    
    return uploaded


if __name__ == '__main__':
    print("=== Probando drive_uploader.py ===")
    print("🧪 Probando descarga de históricos desde Drive...")
    download_history_from_drive()