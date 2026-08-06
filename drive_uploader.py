def download_specific_file(service, filename: str, destination: str = None) -> bool:
    """
    Descarga un archivo específico desde Drive.
    """
    if not service:
        print("❌ Servicio de Drive no disponible.")
        return False
    
    if not destination:
        destination = filename
    
    try:
        from googleapiclient.errors import HttpError
        import io
        from googleapiclient.http import MediaIoBaseDownload
        
        # Buscar el archivo
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
            print(f"⚠️ Archivo no encontrado en Drive: {filename}")
            return False
        
        file_id = files[0]['id']
        print(f"📥 Descargando {filename} desde Drive...")
        
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"   Progreso: {int(status.progress() * 100)}%")
        
        print(f"✅ Archivo descargado: {destination}")
        return True
        
    except HttpError as error:
        print(f"❌ Error al descargar {filename}: {error}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False