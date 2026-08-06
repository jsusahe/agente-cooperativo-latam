# drive_uploader.py - SECCIÓN DE SUBIDA COMPLETA

def upload_to_drive(service, filename, filepath, mime_type):
    """Sube un archivo a Google Drive con verificación de existencia."""
    if not os.path.exists(filepath):
        print(f"⚠️ Archivo no encontrado: {filepath}")
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
        print(f"❌ Error al subir {filename}: {error}")
        return None


def sync_all_files():
    """Sincroniza todos los archivos entre local y Drive."""
    print("\n☁️ SINCRONIZANDO CON GOOGLE DRIVE")
    print("="*50)
    
    service = authenticate_drive()
    if not service:
        print("❌ No se pudo autenticar con Google Drive.")
        return False
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Subir HTML del día
    html_file = os.path.join('historial_cooperativo', f"cooperativo_{current_date}.html")
    if os.path.exists(html_file):
        upload_to_drive(service, f"cooperativo_{current_date}.html", html_file, 'text/html')
    
    # 2. Subir index.html (más reciente)
    if os.path.exists('index.html'):
        upload_to_drive(service, 'index.html', 'index.html', 'text/html')
    
    # 3. Subir audio regional (desde la raíz)
    if os.path.exists('resumen_cooperativo.mp3'):
        upload_to_drive(service, 'resumen_cooperativo.mp3', 'resumen_cooperativo.mp3', 'audio/mpeg')
    
    # 4. Subir audio regional con fecha (desde histórico)
    regional_audio = os.path.join('historial_cooperativo', f"resumen_cooperativo_{current_date}.mp3")
    if os.path.exists(regional_audio):
        upload_to_drive(service, f"resumen_cooperativo_{current_date}.mp3", regional_audio, 'audio/mpeg')
    
    # 5. Subir audios por país
    country_codes = ['CO', 'PA', 'CR', 'DO']
    for code in country_codes:
        audio_file = os.path.join('historial_cooperativo', f"audio_{code}_{current_date}.mp3")
        if os.path.exists(audio_file):
            upload_to_drive(service, f"audio_{code}_{current_date}.mp3", audio_file, 'audio/mpeg')
        
        # También buscar en la raíz
        root_audio = f"audio_{code}_{current_date}.mp3"
        if os.path.exists(root_audio):
            upload_to_drive(service, root_audio, root_audio, 'audio/mpeg')
    
    print("✅ Sincronización completada")
    return True