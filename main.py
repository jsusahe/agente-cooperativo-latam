# main.py - VERSION CON LOGS DE DEBUG MEJORADOS
import os
import json
import shutil
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any

# 🔥 Verificar imports críticos al inicio
print("🔍 Verificando imports...")
try:
    from cooperative_fetcher import get_cooperative_news
    print("  ✅ cooperative_fetcher")
    from cooperative_processor import process_cooperative_news
    print("  ✅ cooperative_processor")
    from summary_generator_coop import generate_cooperative_summaries
    print("  ✅ summary_generator_coop")
    from document_generator_coop import generate_cooperative_document
    print("  ✅ document_generator_coop")
    from audio_generator import generate_audio
    print("  ✅ audio_generator")
    from topic_index import get_topic_index
    print("  ✅ topic_index")
except Exception as e:
    print(f"❌ Error en imports: {e}")
    traceback.print_exc()
    sys.exit(1)

# --- CONFIGURACION ---
HISTORY_FOLDER = "historial_cooperativo"
MAX_HISTORY_DAYS = 30
# --------------------

def ensure_history_folder():
    if not os.path.exists(HISTORY_FOLDER):
        os.makedirs(HISTORY_FOLDER)
        print("Carpeta '{}' creada.".format(HISTORY_FOLDER))

def cleanup_old_history():
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
        
        # Cargar el indice de temas
        print("Cargando indice de temas desde Drive...")
        try:
            index = get_topic_index(service)
            index.load_from_drive()
            print("✅ Indice de temas cargado")
        except Exception as e:
            print(f"⚠️ Error al cargar indice: {e}")
        
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
        traceback.print_exc()
        return True  # Continuamos aunque falle

def load_audio_from_drive():
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
        traceback.print_exc()
        return False

def upload_to_drive():
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("PARENT_FOLDER_ID no configurada. Omitiendo subida a Drive.")
        return True

    print("\nPASO 10: Subiendo archivos a Google Drive...")
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
        
        # Subir indice de temas
        try:
            from topic_index import TopicIndex
            index = TopicIndex(service, parent_folder_id)
            index.save_to_drive()
            print("✅ Indice de temas subido a Drive")
        except Exception as e:
            print("Error al subir indice: {}".format(e))
        
        print("Archivos subidos a Drive correctamente.")
        return True
        
    except ImportError as e:
        print("Error importando drive_uploader: {}".format(e))
        return False
    except Exception as e:
        print("Error al subir a Drive: {}".format(e))
        traceback.print_exc()
        return False

def ensure_audio_in_root():
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    historical_audio = os.path.join(HISTORY_FOLDER, "resumen_cooperativo_{}.mp3".format(current_date))
    if os.path.exists(historical_audio):
        print("Audio encontrado en historico: {}".format(historical_audio))
        shutil.copy(historical_audio, "resumen_cooperativo.mp3")
        print("Audio copiado a la raiz: resumen_cooperativo.mp3")
        return True
    
    if os.environ.get('PARENT_FOLDER_ID'):
        print("Buscando audio en Drive...")
        if load_audio_from_drive():
            return True
    
    if os.path.exists("resumen_cooperativo.mp3"):
        print("Audio ya existe en la raiz: resumen_cooperativo.mp3")
        return True
    
    print("No se encontro audio regional en ninguna ubicacion")
    return False

def generate_audio_if_needed(summary_text):
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    if os.path.exists("resumen_cooperativo.mp3"):
        print("Audio regional ya existe en la raiz")
        return "resumen_cooperativo.mp3"
    
    historical_audio = os.path.join(HISTORY_FOLDER, "resumen_cooperativo_{}.mp3".format(current_date))
    if os.path.exists(historical_audio):
        print("Audio regional existe en historico: {}".format(historical_audio))
        shutil.copy(historical_audio, "resumen_cooperativo.mp3")
        return "resumen_cooperativo.mp3"
    
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

def update_topic_index(summaries: Dict):
    """Actualiza el indice de temas con los topicos generados"""
    print("\n📝 Actualizando indice de temas...")
    
    try:
        from topic_index import TopicIndex
        from drive_uploader import authenticate_drive
        
        service = authenticate_drive()
        if not service:
            print("⚠️ No se pudo autenticar para actualizar indice")
            # Intentar con índice local
            index = TopicIndex()
            index.load_from_drive()
        else:
            index = TopicIndex(service)
            index.load_from_drive()
        
        added = 0
        for code, summary in summaries.items():
            if code in ['REGIONAL', 'COOP_TIP']:
                continue
            
            key_topics = summary.get('key_topics', [])
            country = summary.get('country', 'Desconocido')
            
            for topic in key_topics:
                if topic and index.add_topic(topic, country):
                    added += 1
        
        if added > 0:
            index.save_to_drive()
            print("✅ Indice actualizado: {} nuevos temas agregados".format(added))
        else:
            print("ℹ️ No se agregaron nuevos temas")
        
        return True
        
    except Exception as e:
        print("⚠️ Error al actualizar indice: {}".format(e))
        traceback.print_exc()
        return False

def run_cooperative_agent():
    start_time = time.time()
    
    print("\n" + "="*70)
    print("🏢 AGENTE IA-COOP-LAB")
    print("📅 Fecha: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("🐍 Python: {}".format(sys.version))
    print("="*70)
    
    # Verificar API Key de DeepSeek
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    if not deepseek_key:
        print("❌ ERROR: DEEPSEEK_API_KEY no esta configurada")
        return False
    
    print("✅ DEEPSEEK_API_KEY configurada")
    ensure_history_folder()
    
    # PASO 0: SINCRONIZAR CON DRIVE
    if not sync_from_drive():
        print("⚠️ La sincronizacion inicial con Drive fallo, pero continuamos...")
    
    try:
        # PASO 1: OBTENER NOTICIAS
        print("\n📡 PASO 1: Obteniendo noticias de fuentes cooperativas (paralelo)...")
        raw_data = get_cooperative_news(max_workers=8)
        
        if not raw_data:
            print("❌ No se obtuvieron datos")
            return False
        
        print(f"✅ Datos obtenidos: {len(raw_data)} paises")
        
        # PASO 2: PROCESAR NOTICIAS
        print("\n🔍 PASO 2: Procesando y clasificando noticias...")
        processed_data = process_cooperative_news(raw_data)
        print(f"✅ Datos procesados: {len(processed_data)} paises")
        
        total_news = 0
        countries_with_news = 0
        print("\n📊 Resumen por pais:")
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
            print("  {} {}: {} noticias, {} seleccionadas".format(status, country, total, selected))
        
        print("\n📈 Total: {} noticias en {} paises".format(total_news, countries_with_news))
        
        # PASO 3: GENERAR RESUMENES
        print("\n🧠 PASO 3: Generando resumenes con IA (paralelo)...")
        summaries = generate_cooperative_summaries(processed_data)
        print(f"✅ Resumenes generados: {len(summaries)}")
        
        # PASO 4: ACTUALIZAR INDICE DE TEMAS
        print("\n📝 PASO 4: Actualizando indice de temas...")
        update_topic_index(summaries)
        
        # PASO 5: GENERAR HTML
        print("\n📄 PASO 5: Generando boletin HTML...")
        html_file = generate_cooperative_document(summaries)
        print(f"✅ HTML generado: {html_file}")
        
        # PASO 6: CARGAR AUDIO REGIONAL
        print("\n🎧 PASO 6: Cargando audio del resumen regional...")
        audio_loaded = ensure_audio_in_root()
        
        regional_summary = summaries.get('REGIONAL', {}).get('summary', '')
        if not audio_loaded:
            audio_file = generate_audio_if_needed(regional_summary)
            if audio_file:
                print("✅ Audio regional preparado: {}".format(audio_file))
            else:
                print("⚠️ No se pudo obtener audio regional")
        else:
            print("✅ Audio regional cargado exitosamente")
        
        if os.path.exists("resumen_cooperativo.mp3"):
            size = os.path.getsize("resumen_cooperativo.mp3")
            print("📁 resumen_cooperativo.mp3 existe en la raiz ({} bytes)".format(size))
        else:
            print("⚠️ resumen_cooperativo.mp3 NO existe en la raiz")
        
        # PASO 7: ARCHIVAR EN HISTORICO
        print("\n📁 PASO 7: Archivando en historico...")
        
        if os.path.exists(html_file):
            target_path = os.path.join(HISTORY_FOLDER, html_file)
            shutil.move(html_file, target_path)
            print("✅ HTML archivado: {}".format(target_path))
        
        if os.path.exists("resumen_cooperativo.mp3"):
            target_path = os.path.join(HISTORY_FOLDER, "resumen_cooperativo_{}.mp3".format(datetime.now().strftime('%Y-%m-%d')))
            shutil.copy("resumen_cooperativo.mp3", target_path)
            print("✅ Audio archivado: {}".format(target_path))
        
        # PASO 8: COPIAR A LA RAIZ
        print("\n🌐 PASO 8: Preparando archivos para la web...")
        
        latest_html = os.path.join(HISTORY_FOLDER, "cooperativo_{}.html".format(datetime.now().strftime('%Y-%m-%d')))
        if os.path.exists(latest_html):
            shutil.copy(latest_html, "index.html")
            print("✅ index.html actualizado")
        
        ensure_audio_in_root()
        
        # PASO 9: LIMPIAR HISTORICO
        print("\n🗑️ PASO 9: Limpiando historico (manteniendo {} dias)...".format(MAX_HISTORY_DAYS))
        cleanup_old_history()
        
        # PASO 10: SUBIR A DRIVE
        upload_to_drive()
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print("✅ AGENTE COMPLETADO CON EXITO")
        print("⏱️ Tiempo total: {:.1f} segundos".format(elapsed))
        print("📊 Paises procesados: {}".format(countries_with_news))
        print("📰 Total de noticias: {}".format(total_news))
        
        print("\n📁 Archivos en la raiz:")
        for f in os.listdir('.'):
            if f in ['index.html', 'resumen_cooperativo.mp3']:
                size = os.path.getsize(f) if os.path.exists(f) else 0
                print("  {} {} ({} bytes)".format('✅' if os.path.exists(f) else '❌', f, size))
        
        print("="*70)
        
        return True
        
    except Exception as e:
        print("\n❌ ERROR EN EL AGENTE: {}".format(e))
        traceback.print_exc()
        return False

def run_agent_with_retry(max_retries=2):
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print("\n🔄 Reintento {} de {}...".format(attempt, max_retries))
            time.sleep(15)
        
        if run_cooperative_agent():
            return True
    
    print("\n❌ El agente fallo despues de todos los reintentos.")
    return False

if __name__ == '__main__':
    print("🚀 INICIANDO AGENTE IA-COOP-LAB")
    print("🐍 Python: {}".format(sys.version))
    
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_agent_with_retry()
    sys.exit(0 if success else 1)