# main.py - VERSIÓN COMPLETA CON IMPORTACIÓN DE Optional
import os
import json
import shutil
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional  # ⬅️ AGREGAR Optional AQUÍ

from cooperative_fetcher import get_cooperative_news
from cooperative_processor import process_cooperative_news
from summary_generator_coop import generate_cooperative_summaries
from document_generator_coop import generate_cooperative_document
from audio_generator import generate_audio

# --- CONFIGURACIÓN ---
HISTORY_FOLDER = "historial_cooperativo"
MAX_HISTORY_DAYS = 30
# --------------------

def ensure_history_folder():
    """Asegura que la carpeta de histórico exista"""
    if not os.path.exists(HISTORY_FOLDER):
        os.makedirs(HISTORY_FOLDER)
        print(f"✅ Carpeta '{HISTORY_FOLDER}' creada.")

def cleanup_old_history():
    """Elimina archivos históricos antiguos (HTML y MP3)"""
    if not os.path.exists(HISTORY_FOLDER):
        return
    
    files = [f for f in os.listdir(HISTORY_FOLDER) 
             if f.startswith("cooperativo_") and f.endswith(".html")]
    files.sort()
    
    if len(files) > MAX_HISTORY_DAYS:
        for f in files[:-MAX_HISTORY_DAYS]:
            file_path = os.path.join(HISTORY_FOLDER, f)
            try:
                os.remove(file_path)
                print(f"🗑️ Eliminado histórico: {f}")
                # Eliminar MP3 asociado
                mp3_file = file_path.replace(".html", ".mp3")
                if os.path.exists(mp3_file):
                    os.remove(mp3_file)
                    print(f"🗑️ Eliminado audio asociado: {os.path.basename(mp3_file)}")
            except Exception as e:
                print(f"⚠️ Error al eliminar {f}: {e}")

def sync_from_drive() -> bool:
    """
    PASO 0: Sincroniza los archivos históricos desde Google Drive.
    Descarga todos los archivos HTML y MP3 del histórico que estén en Drive.
    """
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("ℹ️ PARENT_FOLDER_ID no configurada. Omitiendo sincronización con Drive.")
        return True

    print("\n☁️ PASO 0: Sincronizando histórico con Google Drive...")
    try:
        from drive_uploader import authenticate_drive, download_history_from_drive
        
        print("🔐 Autenticando con Google Drive...")
        service = authenticate_drive()
        if not service:
            print("❌ No se pudo autenticar con Google Drive.")
            return False
        
        print("📥 Descargando archivos históricos desde Drive...")
        success = download_history_from_drive(history_folder=HISTORY_FOLDER)
        
        if success:
            print("✅ Sincronización con Drive completada.")
        else:
            print("⚠️ La sincronización con Drive tuvo problemas, pero continuamos.")
        
        return True
        
    except ImportError as e:
        print(f"⚠️ Error importando drive_uploader: {e}")
        return True
    except Exception as e:
        print(f"⚠️ Error en sincronización con Drive: {e}")
        return True

def load_audio_from_drive() -> bool:
    """
    Carga el audio del resumen regional desde Drive si existe.
    """
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("ℹ️ PARENT_FOLDER_ID no configurada. Omitiendo carga desde Drive.")
        return False

    print("\n☁️ Cargando audio regional desde Google Drive...")
    try:
        from drive_uploader import authenticate_drive, download_specific_file
        
        print("🔐 Autenticando con Google Drive...")
        service = authenticate_drive()
        if not service:
            print("❌ No se pudo autenticar con Google Drive.")
            return False
        
        # Buscar archivos de audio regional en Drive
        from googleapiclient.errors import HttpError
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        audio_files = [
            f"resumen_cooperativo_{current_date}.mp3",
            "resumen_cooperativo.mp3"
        ]
        
        for filename in audio_files:
            # Buscar el archivo en Drive
            query = f"name='{filename}' and trashed=false"
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"
            
            try:
                results = service.files().list(
                    q=query,
                    fields="files(id, name)",
                    pageSize=1
                ).execute()
                files = results.get('files', [])
                
                if files:
                    file_id = files[0]['id']
                    print(f"📥 Descargando {filename} desde Drive...")
                    
                    # Descargar a la raíz
                    import io
                    from googleapiclient.http import MediaIoBaseDownload
                    
                    request = service.files().get_media(fileId=file_id)
                    fh = io.FileIO(filename, 'wb')
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        print(f"   Progreso: {int(status.progress() * 100)}%")
                    
                    print(f"✅ Audio cargado desde Drive: {filename}")
                    return True
                    
            except HttpError as e:
                print(f"⚠️ Error buscando {filename}: {e}")
            except Exception as e:
                print(f"⚠️ Error descargando {filename}: {e}")
        
        print("⚠️ No se encontró audio regional en Drive")
        return False
        
    except ImportError as e:
        print(f"⚠️ Error importando drive_uploader: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Error cargando audio desde Drive: {e}")
        return False

def upload_to_drive() -> bool:
    """
    Sube los archivos del día y los principales (index.html, resumen_cooperativo.mp3) a Drive.
    """
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("ℹ️ PARENT_FOLDER_ID no configurada. Omitiendo subida a Drive.")
        return True

    print("\n☁️ PASO 9: Subiendo archivos a Google Drive...")
    try:
        from drive_uploader import authenticate_drive, upload_file_to_drive
        
        print("🔐 Autenticando con Google Drive...")
        service = authenticate_drive()
        if not service:
            print("❌ No se pudo autenticar con Google Drive.")
            return False

        print("✅ Autenticación exitosa")
        
        # 1. Subir HTML del día desde la carpeta de histórico
        latest_html = os.path.join(HISTORY_FOLDER, f"cooperativo_{datetime.now().strftime('%Y-%m-%d')}.html")
        if os.path.exists(latest_html):
            print(f"📤 Subiendo: cooperativo_{datetime.now().strftime('%Y-%m-%d')}.html")
            upload_file_to_drive(
                service,
                f"cooperativo_{datetime.now().strftime('%Y-%m-%d')}.html",
                latest_html,
                'text/html'
            )
        else:
            print(f"⚠️ No se encontró: {latest_html}")
        
        # 2. Subir index.html (copia más reciente)
        if os.path.exists("index.html"):
            print("📤 Subiendo: index.html")
            upload_file_to_drive(service, "index.html", "index.html", "text/html")
        else:
            print("⚠️ No se encontró: index.html")
        
        # 3. 🔥 Subir audio regional (desde la raíz)
        if os.path.exists("resumen_cooperativo.mp3"):
            print("📤 Subiendo: resumen_cooperativo.mp3")
            upload_file_to_drive(
                service,
                "resumen_cooperativo.mp3",
                "resumen_cooperativo.mp3",
                'audio/mpeg'
            )
        else:
            print("⚠️ No se encontró resumen_cooperativo.mp3 en la raíz")
        
        # 4. Subir audio regional con fecha (desde histórico)
        regional_audio = os.path.join(HISTORY_FOLDER, f"resumen_cooperativo_{datetime.now().strftime('%Y-%m-%d')}.mp3")
        if os.path.exists(regional_audio):
            print(f"📤 Subiendo: resumen_cooperativo_{datetime.now().strftime('%Y-%m-%d')}.mp3")
            upload_file_to_drive(
                service,
                f"resumen_cooperativo_{datetime.now().strftime('%Y-%m-%d')}.mp3",
                regional_audio,
                'audio/mpeg'
            )
        
        # 5. Subir audios por país
        country_codes = ['CO', 'PA', 'CR', 'DO']
        for code in country_codes:
            # Buscar en histórico
            audio_file = os.path.join(HISTORY_FOLDER, f"audio_{code}_{datetime.now().strftime('%Y-%m-%d')}.mp3")
            if os.path.exists(audio_file):
                print(f"📤 Subiendo: audio_{code}_{datetime.now().strftime('%Y-%m-%d')}.mp3")
                upload_file_to_drive(
                    service,
                    f"audio_{code}_{datetime.now().strftime('%Y-%m-%d')}.mp3",
                    audio_file,
                    'audio/mpeg'
                )
            
            # Buscar en raíz
            root_audio = f"audio_{code}_{datetime.now().strftime('%Y-%m-%d')}.mp3"
            if os.path.exists(root_audio):
                print(f"📤 Subiendo: {root_audio}")
                upload_file_to_drive(service, root_audio, root_audio, 'audio/mpeg')
        
        print("✅ Archivos subidos a Drive correctamente.")
        return True
        
    except ImportError as e:
        print(f"⚠️ Error importando drive_uploader: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Error al subir a Drive: {e}")
        return False

def ensure_audio_in_root() -> bool:
    """
    🔥 Asegura que el audio regional existe en la raíz.
    Prioriza: 1. Histórico → 2. Drive → 3. Generar nuevo
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Buscar en histórico primero
    historical_audio = os.path.join(HISTORY_FOLDER, f"resumen_cooperativo_{current_date}.mp3")
    if os.path.exists(historical_audio):
        print(f"📥 Audio encontrado en histórico: {historical_audio}")
        shutil.copy(historical_audio, "resumen_cooperativo.mp3")
        print(f"✅ Audio copiado a la raíz: resumen_cooperativo.mp3")
        return True
    
    # 2. Si no está en histórico, buscar en Drive
    if os.environ.get('PARENT_FOLDER_ID'):
        print("🔍 Buscando audio en Drive...")
        if load_audio_from_drive():
            return True
    
    # 3. Si no hay en Drive, verificar si ya existe en la raíz
    if os.path.exists("resumen_cooperativo.mp3"):
        print("✅ Audio ya existe en la raíz: resumen_cooperativo.mp3")
        return True
    
    print("⚠️ No se encontró audio regional en ninguna ubicación")
    return False

def generate_audio_if_needed(summary_text: str) -> Optional[str]:
    """
    Genera audio del resumen regional si no existe en ninguna ubicación.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Verificar si ya existe en la raíz
    if os.path.exists("resumen_cooperativo.mp3"):
        print("✅ Audio regional ya existe en la raíz")
        return "resumen_cooperativo.mp3"
    
    # Verificar si ya existe en histórico
    historical_audio = os.path.join(HISTORY_FOLDER, f"resumen_cooperativo_{current_date}.mp3")
    if os.path.exists(historical_audio):
        print(f"✅ Audio regional existe en histórico: {historical_audio}")
        shutil.copy(historical_audio, "resumen_cooperativo.mp3")
        return "resumen_cooperativo.mp3"
    
    # Si no existe, generar nuevo audio
    if summary_text and len(summary_text) > 50:
        print("🎧 Generando nuevo audio regional...")
        audio_filename = f"resumen_cooperativo_{current_date}.mp3"
        audio_file = generate_audio(summary_text, audio_filename)
        
        if audio_file and os.path.exists(audio_file):
            # Copiar a la raíz
            shutil.copy(audio_file, "resumen_cooperativo.mp3")
            print(f"✅ Audio generado y copiado a la raíz: resumen_cooperativo.mp3")
            
            # Archivar en histórico
            shutil.copy(audio_file, os.path.join(HISTORY_FOLDER, audio_filename))
            print(f"✅ Audio archivado en histórico: {audio_filename}")
            
            return "resumen_cooperativo.mp3"
    
    return None

def run_cooperative_agent() -> bool:
    """Ejecuta el agente cooperativo completo"""
    start_time = time.time()
    
    print("\n" + "="*70)
    print(f"🏢 AGENTE DE NOTICIAS COOPERATIVAS LATINOAMERICANAS")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Verificar API Key de DeepSeek (OBLIGATORIA)
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    if not deepseek_key:
        print("❌ ERROR: DEEPSEEK_API_KEY no está configurada")
        return False
    
    ensure_history_folder()
    
    # ============================================
    # PASO 0: SINCRONIZAR CON DRIVE (AL INICIO)
    # ============================================
    if not sync_from_drive():
        print("⚠️ La sincronización inicial con Drive falló, pero continuamos...")
    
    try:
        # ============================================
        # PASO 1: OBTENER NOTICIAS (PARALELO)
        # ============================================
        print("\n📡 PASO 1: Obteniendo noticias de fuentes cooperativas (paralelo)...")
        raw_data = get_cooperative_news(max_workers=8)
        
        if not raw_data:
            print("❌ No se obtuvieron datos")
            return False
        
        # ============================================
        # PASO 2: PROCESAR NOTICIAS
        # ============================================
        print("\n🔍 PASO 2: Procesando y clasificando noticias...")
        processed_data = process_cooperative_news(raw_data)
        
        # Mostrar resumen
        total_news = 0
        countries_with_news = 0
        print("\n📊 Resumen por país:")
        print("-" * 50)
        for code, data in processed_data.items():
            if code == 'LATAM':
                continue
            country = data.get('country', 'Desconocido')
            total = data.get('total_articles', 0)
            selected = len(data.get('selected_news', []))
            total_news += total
            if selected > 0:
                countries_with_news += 1
            status = "✅" if selected >= 5 else "⚠️"
            print(f"  {status} {country}: {total} noticias, {selected} seleccionadas")
        
        print(f"\n📈 Total: {total_news} noticias en {countries_with_news} países")
        
        # ============================================
        # PASO 3: GENERAR RESÚMENES (PARALELO)
        # ============================================
        print("\n🧠 PASO 3: Generando resúmenes con IA (paralelo)...")
        summaries = generate_cooperative_summaries(processed_data)
        
        # ============================================
        # PASO 4: GENERAR DOCUMENTO HTML
        # ============================================
        print("\n📄 PASO 4: Generando boletín HTML...")
        html_file = generate_cooperative_document(summaries)
        
        # ============================================
        # PASO 5: CARGAR AUDIO REGIONAL (DESDE DRIVE O GENERAR)
        # ============================================
        print("\n🎧 PASO 5: Cargando audio del resumen regional...")
        
        # 🔥 PRIMERO: Intentar cargar desde Drive o histórico
        audio_loaded = ensure_audio_in_root()
        
        # 🔥 SEGUNDO: Si no se cargó, generar nuevo audio
        regional_summary = summaries.get('REGIONAL', {}).get('summary', '')
        if not audio_loaded:
            audio_file = generate_audio_if_needed(regional_summary)
            if audio_file:
                print(f"✅ Audio regional preparado: {audio_file}")
            else:
                print("⚠️ No se pudo obtener audio regional")
        else:
            print("✅ Audio regional cargado exitosamente")
        
        # Verificar que el audio existe en la raíz
        if os.path.exists("resumen_cooperativo.mp3"):
            size = os.path.getsize("resumen_cooperativo.mp3")
            print(f"📁 resumen_cooperativo.mp3 existe en la raíz ({size} bytes)")
        else:
            print("⚠️ resumen_cooperativo.mp3 NO existe en la raíz")
        
        # ============================================
        # PASO 6: ARCHIVAR EN HISTÓRICO
        # ============================================
        print("\n📁 PASO 6: Archivando en histórico...")
        
        # Archivar HTML
        if os.path.exists(html_file):
            target_path = os.path.join(HISTORY_FOLDER, html_file)
            shutil.move(html_file, target_path)
            print(f"✅ HTML archivado: {target_path}")
        
        # Archivar audio si existe en la raíz
        if os.path.exists("resumen_cooperativo.mp3"):
            target_path = os.path.join(HISTORY_FOLDER, f"resumen_cooperativo_{datetime.now().strftime('%Y-%m-%d')}.mp3")
            shutil.copy("resumen_cooperativo.mp3", target_path)
            print(f"✅ Audio archivado: {target_path}")
        
        # ============================================
        # PASO 7: COPIAR A LA RAÍZ PARA LA WEB
        # ============================================
        print("\n🌐 PASO 7: Preparando archivos para la web...")
        
        # Copiar HTML más reciente a la raíz
        latest_html = os.path.join(HISTORY_FOLDER, f"cooperativo_{datetime.now().strftime('%Y-%m-%d')}.html")
        if os.path.exists(latest_html):
            shutil.copy(latest_html, "index.html")
            print("✅ index.html actualizado")
        
        # 🔥 Asegurar que el audio está en la raíz
        ensure_audio_in_root()
        
        # ============================================
        # PASO 8: LIMPIAR HISTÓRICO ANTIGUO
        # ============================================
        print(f"\n🗑️ PASO 8: Limpiando histórico (manteniendo {MAX_HISTORY_DAYS} días)...")
        cleanup_old_history()
        
        # ============================================
        # PASO 9: SUBIR A DRIVE (AL FINAL)
        # ============================================
        upload_to_drive()
        
        # ============================================
        # RESUMEN FINAL
        # ============================================
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print("✅ AGENTE COMPLETADO CON ÉXITO")
        print(f"⏱️ Tiempo total: {elapsed:.1f} segundos")
        print(f"📊 Países procesados: {countries_with_news}")
        print(f"📰 Total de noticias: {total_news}")
        
        # Verificar archivos finales
        print("\n📁 Archivos en la raíz:")
        for f in os.listdir('.'):
            if f in ['index.html', 'resumen_cooperativo.mp3']:
                size = os.path.getsize(f) if os.path.exists(f) else 0
                print(f"  ✅ {f} ({size} bytes)")
        
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN EL AGENTE: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_agent_with_retry(max_retries: int = 2) -> bool:
    """Ejecuta el agente con reintentos en caso de fallo"""
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"\n🔄 Reintento {attempt} de {max_retries}...")
            time.sleep(15)
        
        if run_cooperative_agent():
            return True
    
    print("\n❌ El agente falló después de todos los reintentos.")
    return False

if __name__ == '__main__':
    print("🚀 INICIANDO AGENTE COOPERATIVO")
    print(f"🐍 Python: {sys.version}")
    
    # Cargar variables de entorno
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_agent_with_retry()
    sys.exit(0 if success else 1)