# main.py - VERSIÓN SIN Optional PARA EVITAR ERRORES
import os
import json
import shutil
import sys
import time
from datetime import datetime
from typing import Dict, Any  # Sin Optional para evitar errores

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
    """Asegura que la carpeta de historico exista"""
    if not os.path.exists(HISTORY_FOLDER):
        os.makedirs(HISTORY_FOLDER)
        print("Carpeta '{}' creada.".format(HISTORY_FOLDER))

def cleanup_old_history():
    """Elimina archivos historicos antiguos (HTML y MP3)"""
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
                print("Eliminado historico: {}".format(f))
                mp3_file = file_path.replace(".html", ".mp3")
                if os.path.exists(mp3_file):
                    os.remove(mp3_file)
                    print("Eliminado audio asociado: {}".format(os.path.basename(mp3_file)))
            except Exception as e:
                print("Error al eliminar {}: {}".format(f, e))

def sync_from_drive():
    """
    PASO 0: Sincroniza los archivos historicos desde Google Drive.
    """
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("PARENT_FOLDER_ID no configurada. Omitiendo sincronizacion con Drive.")
        return True

    print("\nPASO 0: Sincronizando historico con Google Drive...")
    try:
        from drive_uploader import authenticate_drive, download_history_from_drive
        
        print("Autenticando con Google Drive...")
        service = authenticate_drive()
        if not service:
            print("No se pudo autenticar con Google Drive.")
            return False
        
        print("Descargando archivos historicos desde Drive...")
        success = download_history_from_drive(history_folder=HISTORY_FOLDER)
        
        if success:
            print("Sincronizacion con Drive completada.")
        else:
            print("La sincronizacion con Drive tuvo problemas, pero continuamos.")
        
        return True
        
    except ImportError as e:
        print("Error importando drive_uploader: {}".format(e))
        return True
    except Exception as e:
        print("Error en sincronizacion con Drive: {}".format(e))
        return True

def load_audio_from_drive():
    """
    Carga el audio del resumen regional desde Drive si existe.
    """
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("PARENT_FOLDER_ID no configurada. Omitiendo carga desde Drive.")
        return False

    print("\nCargando audio regional desde Google Drive...")
    try:
        from drive_uploader import authenticate_drive, download_specific_file
        
        print("Autenticando con Google Drive...")
        service = authenticate_drive()
        if not service:
            print("No se pudo autenticar con Google Drive.")
            return False
        
        from googleapiclient.errors import HttpError
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        audio_files = [
            "resumen_cooperativo_{}.mp3".format(current_date),
            "resumen_cooperativo.mp3"
        ]
        
        for filename in audio_files:
            query = "name='{}' and trashed=false".format(filename)
            if parent_folder_id:
                query += " and '{}' in parents".format(parent_folder_id)
            
            try:
                results = service.files().list(
                    q=query,
                    fields="files(id, name)",
                    pageSize=1
                ).execute()
                files = results.get('files', [])
                
                if files:
                    file_id = files[0]['id']
                    print("Descargando {} desde Drive...".format(filename))
                    
                    import io
                    from googleapiclient.http import MediaIoBaseDownload
                    
                    request = service.files().get_media(fileId=file_id)
                    fh = io.FileIO(filename, 'wb')
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        print("   Progreso: {}%".format(int(status.progress() * 100)))
                    
                    print("Audio cargado desde Drive: {}".format(filename))
                    return True
                    
            except HttpError as e:
                print("Error buscando {}: {}".format(filename, e))
            except Exception as e:
                print("Error descargando {}: {}".format(filename, e))
        
        print("No se encontro audio regional en Drive")
        return False
        
    except ImportError as e:
        print("Error importando drive_uploader: {}".format(e))
        return False
    except Exception as e:
        print("Error cargando audio desde Drive: {}".format(e))
        return False

def upload_to_drive():
    """
    Sube los archivos del dia y los principales a Drive.
    """
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("PARENT_FOLDER_ID no configurada. Omitiendo subida a Drive.")
        return True

    print("\nPASO 9: Subiendo archivos a Google Drive...")
    try:
        from drive_uploader import authenticate_drive, upload_file_to_drive
        
        print("Autenticando con Google Drive...")
        service = authenticate_drive()
        if not service:
            print("No se pudo autenticar con Google Drive.")
            return False

        print("Autenticacion exitosa")
        
        # Subir HTML del dia
        latest_html = os.path.join(HISTORY_FOLDER, "cooperativo_{}.html".format(datetime.now().strftime('%Y-%m-%d')))
        if os.path.exists(latest_html):
            print("Subiendo: cooperativo_{}.html".format(datetime.now().strftime('%Y-%m-%d')))
            upload_file_to_drive(
                service,
                "cooperativo_{}.html".format(datetime.now().strftime('%Y-%m-%d')),
                latest_html,
                'text/html'
            )
        else:
            print("No se encontro: {}".format(latest_html))
        
        # Subir index.html
        if os.path.exists("index.html"):
            print("Subiendo: index.html")
            upload_file_to_drive(service, "index.html", "index.html", 'text/html')
        else:
            print("No se encontro: index.html")
        
        # Subir audio regional
        if os.path.exists("resumen_cooperativo.mp3"):
            print("Subiendo: resumen_cooperativo.mp3")
            upload_file_to_drive(
                service,
                "resumen_cooperativo.mp3",
                "resumen_cooperativo.mp3",
                'audio/mpeg'
            )
        else:
            print("No se encontro resumen_cooperativo.mp3 en la raiz")
        
        # Subir audio regional con fecha
        regional_audio = os.path.join(HISTORY_FOLDER, "resumen_cooperativo_{}.mp3".format(datetime.now().strftime('%Y-%m-%d')))
        if os.path.exists(regional_audio):
            print("Subiendo: resumen_cooperativo_{}.mp3".format(datetime.now().strftime('%Y-%m-%d')))
            upload_file_to_drive(
                service,
                "resumen_cooperativo_{}.mp3".format(datetime.now().strftime('%Y-%m-%d')),
                regional_audio,
                'audio/mpeg'
            )
        
        # Subir audios por pais
        country_codes = ['CO', 'PA', 'CR', 'DO']
        for code in country_codes:
            audio_file = os.path.join(HISTORY_FOLDER, "audio_{}_{}.mp3".format(code, datetime.now().strftime('%Y-%m-%d')))
            if os.path.exists(audio_file):
                print("Subiendo: audio_{}_{}.mp3".format(code, datetime.now().strftime('%Y-%m-%d')))
                upload_file_to_drive(
                    service,
                    "audio_{}_{}.mp3".format(code, datetime.now().strftime('%Y-%m-%d')),
                    audio_file,
                    'audio/mpeg'
                )
            
            root_audio = "audio_{}_{}.mp3".format(code, datetime.now().strftime('%Y-%m-%d'))
            if os.path.exists(root_audio):
                print("Subiendo: {}".format(root_audio))
                upload_file_to_drive(service, root_audio, root_audio, 'audio/mpeg')
        
        print("Archivos subidos a Drive correctamente.")
        return True
        
    except ImportError as e:
        print("Error importando drive_uploader: {}".format(e))
        return False
    except Exception as e:
        print("Error al subir a Drive: {}".format(e))
        return False

def ensure_audio_in_root():
    """
    Asegura que el audio regional existe en la raiz.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Buscar en historico primero
    historical_audio = os.path.join(HISTORY_FOLDER, "resumen_cooperativo_{}.mp3".format(current_date))
    if os.path.exists(historical_audio):
        print("Audio encontrado en historico: {}".format(historical_audio))
        shutil.copy(historical_audio, "resumen_cooperativo.mp3")
        print("Audio copiado a la raiz: resumen_cooperativo.mp3")
        return True
    
    # Buscar en Drive
    if os.environ.get('PARENT_FOLDER_ID'):
        print("Buscando audio en Drive...")
        if load_audio_from_drive():
            return True
    
    # Verificar si ya existe en la raiz
    if os.path.exists("resumen_cooperativo.mp3"):
        print("Audio ya existe en la raiz: resumen_cooperativo.mp3")
        return True
    
    print("No se encontro audio regional en ninguna ubicacion")
    return False

def generate_audio_if_needed(summary_text):
    """
    Genera audio del resumen regional si no existe en ninguna ubicacion.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Verificar si ya existe en la raiz
    if os.path.exists("resumen_cooperativo.mp3"):
        print("Audio regional ya existe en la raiz")
        return "resumen_cooperativo.mp3"
    
    # Verificar si ya existe en historico
    historical_audio = os.path.join(HISTORY_FOLDER, "resumen_cooperativo_{}.mp3".format(current_date))
    if os.path.exists(historical_audio):
        print("Audio regional existe en historico: {}".format(historical_audio))
        shutil.copy(historical_audio, "resumen_cooperativo.mp3")
        return "resumen_cooperativo.mp3"
    
    # Si no existe, generar nuevo audio
    if summary_text and len(summary_text) > 50:
        print("Generando nuevo audio regional...")
        audio_filename = "resumen_cooperativo_{}.mp3".format(current_date)
        audio_file = generate_audio(summary_text, audio_filename)
        
        if audio_file and os.path.exists(audio_file):
            shutil.copy(audio_file, "resumen_cooperativo.mp3")
            print("Audio generado y copiado a la raiz: resumen_cooperativo.mp3")
            
            shutil.copy(audio_file, os.path.join(HISTORY_FOLDER, audio_filename))
            print("Audio archivado en historico: {}".format(audio_filename))
            
            return "resumen_cooperativo.mp3"
    
    return None

def run_cooperative_agent():
    """Ejecuta el agente cooperativo completo"""
    start_time = time.time()
    
    print("\n" + "="*70)
    print("AGENTE DE NOTICIAS COOPERATIVAS LATINOAMERICANAS")
    print("Fecha: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("="*70)
    
    # Verificar API Key de DeepSeek
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    if not deepseek_key:
        print("ERROR: DEEPSEEK_API_KEY no esta configurada")
        return False
    
    ensure_history_folder()
    
    # PASO 0: SINCRONIZAR CON DRIVE
    if not sync_from_drive():
        print("La sincronizacion inicial con Drive fallo, pero continuamos...")
    
    try:
        # PASO 1: OBTENER NOTICIAS
        print("\nPASO 1: Obteniendo noticias de fuentes cooperativas (paralelo)...")
        raw_data = get_cooperative_news(max_workers=8)
        
        if not raw_data:
            print("No se obtuvieron datos")
            return False
        
        # PASO 2: PROCESAR NOTICIAS
        print("\nPASO 2: Procesando y clasificando noticias...")
        processed_data = process_cooperative_news(raw_data)
        
        total_news = 0
        countries_with_news = 0
        print("\nResumen por pais:")
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
            status = "SI" if selected >= 5 else "NO"
            print("  {} {}: {} noticias, {} seleccionadas".format(status, country, total, selected))
        
        print("\nTotal: {} noticias en {} paises".format(total_news, countries_with_news))
        
        # PASO 3: GENERAR RESUMENES
        print("\nPASO 3: Generando resumenes con IA (paralelo)...")
        summaries = generate_cooperative_summaries(processed_data)
        
        # PASO 4: GENERAR HTML
        print("\nPASO 4: Generando boletin HTML...")
        html_file = generate_cooperative_document(summaries)
        
        # PASO 5: CARGAR AUDIO REGIONAL
        print("\nPASO 5: Cargando audio del resumen regional...")
        audio_loaded = ensure_audio_in_root()
        
        regional_summary = summaries.get('REGIONAL', {}).get('summary', '')
        if not audio_loaded:
            audio_file = generate_audio_if_needed(regional_summary)
            if audio_file:
                print("Audio regional preparado: {}".format(audio_file))
            else:
                print("No se pudo obtener audio regional")
        else:
            print("Audio regional cargado exitosamente")
        
        if os.path.exists("resumen_cooperativo.mp3"):
            size = os.path.getsize("resumen_cooperativo.mp3")
            print("resumen_cooperativo.mp3 existe en la raiz ({} bytes)".format(size))
        else:
            print("resumen_cooperativo.mp3 NO existe en la raiz")
        
        # PASO 6: ARCHIVAR EN HISTORICO
        print("\nPASO 6: Archivando en historico...")
        
        if os.path.exists(html_file):
            target_path = os.path.join(HISTORY_FOLDER, html_file)
            shutil.move(html_file, target_path)
            print("HTML archivado: {}".format(target_path))
        
        if os.path.exists("resumen_cooperativo.mp3"):
            target_path = os.path.join(HISTORY_FOLDER, "resumen_cooperativo_{}.mp3".format(datetime.now().strftime('%Y-%m-%d')))
            shutil.copy("resumen_cooperativo.mp3", target_path)
            print("Audio archivado: {}".format(target_path))
        
        # PASO 7: COPIAR A LA RAIZ
        print("\nPASO 7: Preparando archivos para la web...")
        
        latest_html = os.path.join(HISTORY_FOLDER, "cooperativo_{}.html".format(datetime.now().strftime('%Y-%m-%d')))
        if os.path.exists(latest_html):
            shutil.copy(latest_html, "index.html")
            print("index.html actualizado")
        
        ensure_audio_in_root()
        
        # PASO 8: LIMPIAR HISTORICO
        print("\nPASO 8: Limpiando historico (manteniendo {} dias)...".format(MAX_HISTORY_DAYS))
        cleanup_old_history()
        
        # PASO 9: SUBIR A DRIVE
        upload_to_drive()
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print("AGENTE COMPLETADO CON EXITO")
        print("Tiempo total: {:.1f} segundos".format(elapsed))
        print("Paises procesados: {}".format(countries_with_news))
        print("Total de noticias: {}".format(total_news))
        
        print("\nArchivos en la raiz:")
        for f in os.listdir('.'):
            if f in ['index.html', 'resumen_cooperativo.mp3']:
                size = os.path.getsize(f) if os.path.exists(f) else 0
                print("  {} {} ({} bytes)".format('SI' if os.path.exists(f) else 'NO', f, size))
        
        print("="*70)
        
        return True
        
    except Exception as e:
        print("\nERROR EN EL AGENTE: {}".format(e))
        import traceback
        traceback.print_exc()
        return False

def run_agent_with_retry(max_retries=2):
    """Ejecuta el agente con reintentos en caso de fallo"""
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print("\nReintento {} de {}...".format(attempt, max_retries))
            time.sleep(15)
        
        if run_cooperative_agent():
            return True
    
    print("\nEl agente fallo despues de todos los reintentos.")
    return False

if __name__ == '__main__':
    print("INICIANDO AGENTE COOPERATIVO")
    print("Python: {}".format(sys.version))
    
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_agent_with_retry()
    sys.exit(0 if success else 1)