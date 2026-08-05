# drive_uploader.py
import os
import pickle
import time
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io

SCOPES = ['https://www.googleapis.com/auth/drive.file']
PARENT_FOLDER_ID = os.environ.get('PARENT_FOLDER_ID')
MAX_RETRIES = 3

def authenticate_drive():
    """Autentica con Google Drive y devuelve el servicio."""
    creds = None
    token_file = 'token.json'
    credentials_file = 'credentials.json'
    
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            if creds and creds.valid:
                return build('drive', 'v3', credentials=creds)
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
                return build('drive', 'v3', credentials=creds)
            else:
                os.remove(token_file)
        except Exception as e:
            print(f"⚠️ Error al cargar token.json: {e}")
            if os.path.exists(token_file):
                os.remove(token_file)
    
    if not os.path.exists(credentials_file):
        print(f"❌ Error: No se encuentra el archivo '{credentials_file}'.")
        return None
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Error en autenticación: {e}")
        return None

def upload_file_to_drive(service, filename, filepath, mime_type, retry_count=0):
    """Sube un archivo a Google Drive."""
    if not service or not os.path.exists(filepath):
        return None
    
    try:
        file_metadata = {'name': filename}
        if PARENT_FOLDER_ID:
            file_metadata['parents'] = [PARENT_FOLDER_ID]
        
        media = MediaFileUpload(filepath, mimetype=mime_type, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        file_id = file.get('id')
        print(f"✅ Subido a Drive: {filename}")
        return file_id
    except HttpError as error:
        if error.resp.status in [429, 500, 503] and retry_count < MAX_RETRIES:
            wait_time = (retry_count + 1) * 5
            print(f"⏳ Reintentando en {wait_time} segundos...")
            time.sleep(wait_time)
            return upload_file_to_drive(service, filename, filepath, mime_type, retry_count + 1)
        print(f"❌ Error al subir {filename}: {error}")
        return None