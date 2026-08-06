# main.py - VERSION CON DEBUG Y FLUSH DE SALIDA
import os
import sys
import json
import shutil
import time
import traceback
from datetime import datetime
from typing import Dict, Any

# 🔥 CONFIGURAR BUFFER DE SALIDA - Para ver logs en tiempo real
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("🚀 INICIANDO AGENTE IA-COOP-LAB", flush=True)
print(f"🐍 Python: {sys.version}", flush=True)

# 🔥 Verificar imports al inicio
print("🔍 Verificando imports...", flush=True)

try:
    from cooperative_fetcher import get_cooperative_news
    print("  ✅ cooperative_fetcher", flush=True)
except Exception as e:
    print(f"  ❌ cooperative_fetcher: {e}", flush=True)
    sys.exit(1)

try:
    from cooperative_processor import process_cooperative_news
    print("  ✅ cooperative_processor", flush=True)
except Exception as e:
    print(f"  ❌ cooperative_processor: {e}", flush=True)
    sys.exit(1)

try:
    from summary_generator_coop import generate_cooperative_summaries
    print("  ✅ summary_generator_coop", flush=True)
except Exception as e:
    print(f"  ❌ summary_generator_coop: {e}", flush=True)
    sys.exit(1)

try:
    from document_generator_coop import generate_cooperative_document
    print("  ✅ document_generator_coop", flush=True)
except Exception as e:
    print(f"  ❌ document_generator_coop: {e}", flush=True)
    sys.exit(1)

try:
    from audio_generator import generate_audio
    print("  ✅ audio_generator", flush=True)
except Exception as e:
    print(f"  ❌ audio_generator: {e}", flush=True)
    sys.exit(1)

try:
    from topic_index import get_topic_index
    print("  ✅ topic_index", flush=True)
except Exception as e:
    print(f"  ❌ topic_index: {e}", flush=True)
    sys.exit(1)

print("✅ Todos los imports cargados correctamente", flush=True)

# --- CONFIGURACION ---
HISTORY_FOLDER = "historial_cooperativo"
MAX_HISTORY_DAYS = 30
# --------------------

def ensure_history_folder():
    if not os.path.exists(HISTORY_FOLDER):
        os.makedirs(HISTORY_FOLDER)
        print(f"✅ Carpeta '{HISTORY_FOLDER}' creada.", flush=True)

def run_cooperative_agent():
    """Ejecuta el agente cooperativo completo"""
    start_time = time.time()
    
    print("\n" + "="*70, flush=True)
    print("🏢 AGENTE IA-COOP-LAB", flush=True)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("="*70, flush=True)
    
    # Verificar API Key
    if not os.environ.get('DEEPSEEK_API_KEY'):
        print("❌ ERROR: DEEPSEEK_API_KEY no esta configurada", flush=True)
        return False
    
    print("✅ DEEPSEEK_API_KEY configurada", flush=True)
    ensure_history_folder()
    
    try:
        # ============================================
        # PASO 1: OBTENER NOTICIAS
        # ============================================
        print("\n📡 PASO 1: Obteniendo noticias...", flush=True)
        
        raw_data = None
        try:
            raw_data = get_cooperative_news(max_workers=2)  # 🔥 Reducido a 2
        except Exception as e:
            print(f"❌ Error en get_cooperative_news: {e}", flush=True)
            traceback.print_exc()
            return False
        
        if not raw_data:
            print("❌ No se obtuvieron datos", flush=True)
            return False
        
        print(f"✅ Datos obtenidos: {len(raw_data)} paises", flush=True)
        
        # ============================================
        # PASO 2: PROCESAR NOTICIAS
        # ============================================
        print("\n🔍 PASO 2: Procesando noticias...", flush=True)
        
        processed_data = None
        try:
            processed_data = process_cooperative_news(raw_data)
        except Exception as e:
            print(f"❌ Error en process_cooperative_news: {e}", flush=True)
            traceback.print_exc()
            return False
        
        print(f"✅ Datos procesados: {len(processed_data)} paises", flush=True)
        
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
        
        print(f"📊 Total: {total_news} noticias en {countries_with_news} paises", flush=True)
        
        # ============================================
        # PASO 3: GENERAR RESUMENES
        # ============================================
        print("\n🧠 PASO 3: Generando resumenes con IA...", flush=True)
        
        summaries = None
        try:
            summaries = generate_cooperative_summaries(processed_data)
        except Exception as e:
            print(f"❌ Error en generate_cooperative_summaries: {e}", flush=True)
            traceback.print_exc()
            return False
        
        print(f"✅ Resumenes generados: {len(summaries)}", flush=True)
        
        # ============================================
        # PASO 4: GENERAR HTML
        # ============================================
        print("\n📄 PASO 4: Generando boletin HTML...", flush=True)
        
        html_file = None
        try:
            html_file = generate_cooperative_document(summaries)
        except Exception as e:
            print(f"❌ Error en generate_cooperative_document: {e}", flush=True)
            traceback.print_exc()
            return False
        
        print(f"✅ HTML generado: {html_file}", flush=True)
        
        # ============================================
        # PASO 5: COPIAR A LA RAIZ
        # ============================================
        print("\n🌐 PASO 5: Copiando archivos a la raiz...", flush=True)
        
        # Buscar el HTML en historial
        latest_html = os.path.join(HISTORY_FOLDER, html_file)
        if os.path.exists(latest_html):
            try:
                shutil.copy(latest_html, "index.html")
                print("✅ index.html generado", flush=True)
            except Exception as e:
                print(f"⚠️ Error copiando index.html: {e}", flush=True)
        
        # Copiar audio si existe
        if os.path.exists("resumen_cooperativo.mp3"):
            try:
                target = os.path.join(HISTORY_FOLDER, f"resumen_cooperativo_{datetime.now().strftime('%Y-%m-%d')}.mp3")
                shutil.copy("resumen_cooperativo.mp3", target)
                print("✅ Audio copiado a historial", flush=True)
            except Exception as e:
                print(f"⚠️ Error copiando audio: {e}", flush=True)
        
        # ============================================
        # PASO 6: FINALIZAR
        # ============================================
        elapsed = time.time() - start_time
        print("\n" + "="*70, flush=True)
        print("✅ AGENTE COMPLETADO CON EXITO", flush=True)
        print(f"⏱️ Tiempo total: {elapsed:.1f} segundos", flush=True)
        print("="*70, flush=True)
        
        # Verificar archivos generados
        print("\n📁 Archivos generados:", flush=True)
        for f in os.listdir('.'):
            if f in ['index.html', 'resumen_cooperativo.mp3']:
                if os.path.exists(f):
                    size = os.path.getsize(f)
                    print(f"  ✅ {f} ({size} bytes)", flush=True)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN EL AGENTE: {e}", flush=True)
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 EJECUTANDO MAIN.PY", flush=True)
    
    # Cargar variables de entorno
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_cooperative_agent()
    sys.exit(0 if success else 1)