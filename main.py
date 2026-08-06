# main.py - VERSION CON CHECKPOINTS PARA DEPURACION
import os
import json
import shutil
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any

# 🔥 Importar módulos con verificación
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
CHECKPOINT_FILE = "checkpoint.json"
# --------------------

def save_checkpoint(step: str, data: Dict = None):
    """Guarda un checkpoint para saber hasta dónde llegó el proceso"""
    checkpoint = {
        'step': step,
        'timestamp': datetime.now().isoformat(),
        'data': data or {}
    }
    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2)
        print(f"   💾 Checkpoint guardado: {step}")
    except Exception as e:
        print(f"   ⚠️ Error guardando checkpoint: {e}")

def load_checkpoint():
    """Carga el último checkpoint"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return None

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
        
        return True
        
    except Exception as e:
        print(f"⚠️ Error en sincronizacion: {e}")
        return True

def upload_to_drive():
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("PARENT_FOLDER_ID no configurada. Omitiendo subida a Drive.")
        return True

    print("\nPASO 9: Subiendo archivos a Google Drive...")
    try:
        from drive_uploader import authenticate_drive, upload_file_to_drive
        
        service = authenticate_drive()
        if not service:
            print("No se pudo autenticar con Google Drive.")
            return False

        # Subir HTML del dia
        latest_html = os.path.join(HISTORY_FOLDER, "cooperativo_{}.html".format(datetime.now().strftime('%Y-%m-%d')))
        if os.path.exists(latest_html):
            upload_file_to_drive(
                service,
                "cooperativo_{}.html".format(datetime.now().strftime('%Y-%m-%d')),
                latest_html,
                'text/html'
            )
        
        if os.path.exists("index.html"):
            upload_file_to_drive(service, "index.html", "index.html", 'text/html')
        
        if os.path.exists("resumen_cooperativo.mp3"):
            upload_file_to_drive(service, "resumen_cooperativo.mp3", "resumen_cooperativo.mp3", 'audio/mpeg')
        
        # Subir indice de temas
        try:
            from topic_index import TopicIndex
            index = TopicIndex(service, parent_folder_id)
            index.save_to_drive()
        except Exception as e:
            print(f"Error al subir indice: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error al subir a Drive: {e}")
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
            shutil.copy(audio_file, os.path.join(HISTORY_FOLDER, audio_filename))
            return "resumen_cooperativo.mp3"
    
    return None

def run_cooperative_agent():
    start_time = time.time()
    
    print("\n" + "="*70)
    print("🏢 AGENTE IA-COOP-LAB")
    print("📅 Fecha: {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("🐍 Python: {}".format(sys.version))
    print("="*70)
    
    # Verificar API Key
    if not os.environ.get('DEEPSEEK_API_KEY'):
        print("❌ ERROR: DEEPSEEK_API_KEY no esta configurada")
        return False
    
    ensure_history_folder()
    
    # ============================================
    # PASO 0: SINCRONIZAR CON DRIVE
    # ============================================
    print("\n📡 PASO 0: Sincronizando con Drive...")
    save_checkpoint("step0_start")
    sync_from_drive()
    save_checkpoint("step0_done")
    
    try:
        # ============================================
        # PASO 1: OBTENER NOTICIAS
        # ============================================
        print("\n📡 PASO 1: Obteniendo noticias...")
        save_checkpoint("step1_start")
        raw_data = get_cooperative_news(max_workers=4)  # Reducido para estabilidad
        save_checkpoint("step1_done", {"total_countries": len(raw_data) if raw_data else 0})
        
        if not raw_data:
            print("❌ No se obtuvieron datos")
            return False
        
        print(f"✅ Datos obtenidos: {len(raw_data)} paises")
        
        # ============================================
        # PASO 2: PROCESAR NOTICIAS
        # ============================================
        print("\n🔍 PASO 2: Procesando noticias...")
        save_checkpoint("step2_start")
        processed_data = process_cooperative_news(raw_data)
        save_checkpoint("step2_done", {"total_articles": sum(d.get('total_articles', 0) for d in processed_data.values())})
        
        print(f"✅ Datos procesados: {len(processed_data)} paises")
        
        # Mostrar resumen
        total_news = 0
        countries_with_news = 0
        for code, data in processed_data.items():
            if code == 'LATAM':
                continue
            total = data.get('total_articles', 0)
            selected = len(data.get('selected_news', []))
            total_news += total
            if selected > 0:
                countries_with_news += 1
        
        print(f"📊 Total: {total_news} noticias en {countries_with_news} paises")
        
        # ============================================
        # PASO 3: GENERAR RESUMENES
        # ============================================
        print("\n🧠 PASO 3: Generando resumenes con IA...")
        save_checkpoint("step3_start")
        summaries = generate_cooperative_summaries(processed_data)
        save_checkpoint("step3_done", {"summaries_count": len(summaries)})
        print(f"✅ Resumenes generados: {len(summaries)}")
        
        # ============================================
        # PASO 4: GENERAR HTML
        # ============================================
        print("\n📄 PASO 4: Generando boletin HTML...")
        save_checkpoint("step4_start")
        
        # Verificar que document_generator existe
        print("   📄 Llamando a generate_cooperative_document...")
        html_file = generate_cooperative_document(summaries)
        save_checkpoint("step4_done", {"html_file": html_file})
        print(f"✅ HTML generado: {html_file}")
        
        # ============================================
        # PASO 5: COPIAR A LA RAIZ
        # ============================================
        print("\n🌐 PASO 5: Preparando archivos para la web...")
        save_checkpoint("step5_start")
        
        # Copiar HTML a la raíz
        if os.path.exists(html_file):
            shutil.copy(html_file, "index.html")
            print("✅ index.html generado")
        
        # ============================================
        # PASO 6: LIMPIAR Y SUBIR
        # ============================================
        print("\n🗑️ PASO 6: Limpiando historico...")
        cleanup_old_history()
        
        print("\n☁️ PASO 7: Subiendo a Drive...")
        upload_to_drive()
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print("✅ AGENTE COMPLETADO CON EXITO")
        print(f"⏱️ Tiempo total: {elapsed:.1f} segundos")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN EL AGENTE: {e}")
        traceback.print_exc()
        save_checkpoint("error", {"error": str(e)})
        return False

def run_agent_with_retry(max_retries=1):
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"\n🔄 Reintento {attempt} de {max_retries}...")
            time.sleep(10)
        
        if run_cooperative_agent():
            return True
    
    # Si falló, revisar el checkpoint
    checkpoint = load_checkpoint()
    if checkpoint:
        print(f"\n📋 Último checkpoint: {checkpoint.get('step')}")
        print(f"   Timestamp: {checkpoint.get('timestamp')}")
    
    return False

if __name__ == '__main__':
    print("🚀 INICIANDO AGENTE IA-COOP-LAB")
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_agent_with_retry()
    sys.exit(0 if success else 1)