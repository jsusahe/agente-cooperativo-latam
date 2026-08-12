# main.py - VERSION CORREGIDA CON DESCARGA DE HISTÓRICOS ANTES DEL HTML
import os
import sys
import json
import shutil
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

# 🔥 CONFIGURAR BUFFER DE SALIDA
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("🚀 INICIANDO AGENTE IA-COOP-LAB", flush=True)
print(f"🐍 Python: {sys.version}", flush=True)

# 🔥 Verificar imports
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

# 🔥 IMPORTAR DRIVE UPLOADER
try:
    from drive_uploader import upload_file_to_drive, authenticate_drive, upload_history_folder, download_history_from_drive
    print("  ✅ drive_uploader", flush=True)
except Exception as e:
    print(f"  ❌ drive_uploader: {e}", flush=True)
    print("  ⚠️ La subida a Drive no estará disponible", flush=True)

print("✅ Todos los imports cargados correctamente", flush=True)

# --- CONFIGURACION ---
HISTORY_FOLDER = "historial_cooperativo"
MAX_HISTORY_DAYS = 30
# --------------------

def ensure_history_folder():
    if not os.path.exists(HISTORY_FOLDER):
        os.makedirs(HISTORY_FOLDER)
        print(f"✅ Carpeta '{HISTORY_FOLDER}' creada.", flush=True)

def cleanup_old_history():
    """Elimina archivos históricos antiguos"""
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
                print(f"🗑️ Eliminado historico: {f}", flush=True)
                mp3_file = file_path.replace(".html", ".mp3")
                if os.path.exists(mp3_file):
                    os.remove(mp3_file)
                    print(f"🗑️ Eliminado audio asociado: {os.path.basename(mp3_file)}", flush=True)
            except Exception as e:
                print(f"⚠️ Error al eliminar {f}: {e}", flush=True)

def upload_to_drive(service, html_file, audio_files=None):
    """
    🔥 Sube los archivos generados a Google Drive.
    """
    parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
    if not parent_folder_id:
        print("ℹ️ PARENT_FOLDER_ID no configurada. Omitiendo subida a Drive.", flush=True)
        return False

    print("\n☁️ Subiendo archivos a Google Drive...", flush=True)
    
    try:
        if not service:
            print("❌ Servicio de Drive no disponible.", flush=True)
            return False
        
        print("✅ Autenticación exitosa", flush=True)
        
        # 1. Subir HTML del día
        if html_file and os.path.exists(html_file):
            print(f"📤 Subiendo: {html_file}", flush=True)
            upload_file_to_drive(service, html_file, html_file, 'text/html')
        
        # 2. Subir index.html
        if os.path.exists("index.html"):
            print("📤 Subiendo: index.html", flush=True)
            upload_file_to_drive(service, "index.html", "index.html", 'text/html')
        
        # 3. Subir audio regional
        if os.path.exists("resumen_cooperativo.mp3"):
            print("📤 Subiendo: resumen_cooperativo.mp3", flush=True)
            upload_file_to_drive(service, "resumen_cooperativo.mp3", "resumen_cooperativo.mp3", 'audio/mpeg')
        
        # 4. Subir audios por país
        if audio_files:
            for audio_file in audio_files:
                if os.path.exists(audio_file):
                    print(f"📤 Subiendo: {audio_file}", flush=True)
                    upload_file_to_drive(service, audio_file, audio_file, 'audio/mpeg')
        
        # 5. Subir archivos históricos (últimos 10 días)
        print("📤 Subiendo archivos históricos...", flush=True)
        uploaded = upload_history_folder(service, HISTORY_FOLDER, max_files=10)
        if uploaded:
            print(f"✅ {len(uploaded)} archivos históricos subidos", flush=True)
        
        # 6. 🔥 SUBIR ÍNDICE DE TEMAS
        if os.path.exists("topic_index_local.json"):
            print("📤 Subiendo: topic_index.json", flush=True)
            upload_file_to_drive(service, "topic_index.json", "topic_index_local.json", 'application/json')
        
        print("✅ Archivos subidos a Drive correctamente.", flush=True)
        return True
        
    except Exception as e:
        print(f"❌ Error al subir a Drive: {e}", flush=True)
        traceback.print_exc()
        return False

def generate_empty_document():
    """Genera un documento HTML vacío cuando no hay noticias"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"cooperativo_{date_str}.html"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Boletín Cooperativo - {date_str}</title>
</head>
<body>
    <h1>🏢 IA-COOP-LAB</h1>
    <p>📅 {datetime.now().strftime("%A, %d de %B de %Y")}</p>
    <p>⚠️ No se encontraron noticias cooperativas en las fuentes monitoreadas.</p>
    <p>🔄 Intenta nuevamente mañana.</p>
</body>
</html>
    """
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    target_path = os.path.join(HISTORY_FOLDER, filename)
    shutil.copy(filename, target_path)
    
    return filename

def update_topic_index(summaries: Dict, topic_index) -> int:
    """
    🔥 Actualiza el índice de temas con los tópicos generados.
    Retorna el número de temas nuevos agregados.
    """
    if not topic_index:
        print("⚠️ No hay índice de temas disponible", flush=True)
        return 0
    
    added_topics = 0
    added_tips = 0
    
    # 🔥 Procesar temas de cada país
    for code, summary in summaries.items():
        if code in ['REGIONAL', 'COOP_TIP']:
            continue
        
        key_topics = summary.get('key_topics', [])
        country = summary.get('country', 'Desconocido')
        
        for topic in key_topics:
            if topic and topic_index.add_topic(topic, country):
                added_topics += 1
                print(f"  📌 Nuevo tema agregado: '{topic}' ({country})", flush=True)
    
    # 🔥 Procesar TIP IA-COOP-LAB
    coop_tip = summaries.get('COOP_TIP', {})
    tip_title = coop_tip.get('title', '')
    tip_text = coop_tip.get('summary', '')
    tip_phase = coop_tip.get('phase', '')
    
    if tip_title:
        # 🔥 Guardamos el TIP con la fase y decisión completa
        if topic_index.add_tip(tip_title, tip_text + f"\n\nFase: {tip_phase}"):
            added_tips += 1
            print(f"  💡 Nuevo TIP agregado: '{tip_title}' (Fase: {tip_phase})", flush=True)
        else:
            print(f"  ℹ️ TIP ya existente: '{tip_title}'", flush=True)
    
    # 🔥 Guardar índice actualizado
    if added_topics > 0 or added_tips > 0:
        topic_index.save_to_drive()
        print(f"✅ Índice actualizado: {added_topics} temas nuevos, {added_tips} tips nuevos", flush=True)
    else:
        print("ℹ️ No se agregaron temas ni tips nuevos", flush=True)
    
    return added_topics + added_tips

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
    
    # 🔥 Autenticación única de Drive (para usar en todo el flujo)
    service = None
    if os.environ.get('PARENT_FOLDER_ID'):
        try:
            service = authenticate_drive()
            if service:
                print("✅ Conexión con Google Drive establecida", flush=True)
            else:
                print("⚠️ No se pudo conectar con Google Drive", flush=True)
        except Exception as e:
            print(f"⚠️ Error al autenticar con Drive: {e}", flush=True)
    
    # 🔥 Inicializar índice de temas (usando el servicio de Drive)
    print("\n📚 Cargando índice de temas...", flush=True)
    try:
        topic_index = get_topic_index(service)
        stats = topic_index.get_stats()
        print(f"✅ Índice cargado: {stats['total_topics']} temas, {stats['total_tips']} tips", flush=True)
    except Exception as e:
        print(f"⚠️ Error al cargar índice: {e}", flush=True)
        topic_index = None
    
    # Variables para subir a Drive
    html_file = None
    audio_files = []
    
    try:
        # ============================================
        # PASO 1: OBTENER NOTICIAS
        # ============================================
        print("\n📡 PASO 1: Obteniendo noticias...", flush=True)
        
        raw_data = None
        try:
            raw_data = get_cooperative_news(max_workers=1)
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
        
        if not processed_data:
            print("❌ No se procesaron datos", flush=True)
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
            print(f"  📊 {code}: {total} noticias, {selected} seleccionadas", flush=True)
        
        print(f"📊 Total: {total_news} noticias en {countries_with_news} paises", flush=True)
        
        # 🔥 Si no hay noticias, generar documento vacío
        if total_news == 0:
            print("⚠️ No hay noticias para generar resumen", flush=True)
            html_file = generate_empty_document()
            if html_file:
                shutil.copy(html_file, "index.html")
                print("✅ index.html generado (sin noticias)", flush=True)
                upload_to_drive(service, html_file, [])
            return True
        
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
        
        if not summaries:
            print("❌ No se generaron resumenes", flush=True)
            return False
        
        print(f"✅ Resumenes generados: {len(summaries)}", flush=True)
        
        # ============================================
        # PASO 4: ACTUALIZAR ÍNDICE DE TEMAS
        # ============================================
        print("\n📚 PASO 4: Actualizando índice de temas...", flush=True)
        if topic_index:
            new_items = update_topic_index(summaries, topic_index)
            print(f"✅ Índice actualizado: {new_items} items nuevos", flush=True)
        else:
            print("⚠️ No se pudo actualizar el índice (servicio no disponible)", flush=True)
        
        # ============================================
        # 🔥 PASO 5: DESCARGAR HISTÓRICOS DESDE DRIVE (ANTES DE GENERAR HTML)
        # ============================================
        print("\n📥 PASO 5: Descargando históricos desde Drive...", flush=True)
        if service:
            try:
                download_success = download_history_from_drive(service, HISTORY_FOLDER)
                if download_success:
                    print("✅ Históricos descargados correctamente", flush=True)
                    
                    # 🔥 Verificar que haya al menos 10 archivos
                    files = [f for f in os.listdir(HISTORY_FOLDER) if f.startswith("cooperativo_") and f.endswith(".html")]
                    print(f"📁 Archivos en histórico después de descarga: {len(files)}", flush=True)
                else:
                    print("⚠️ No se pudieron descargar históricos", flush=True)
            except Exception as e:
                print(f"⚠️ Error al descargar históricos: {e}", flush=True)
        else:
            print("ℹ️ No se configuró Drive. Usando históricos locales existentes.", flush=True)
        
        # ============================================
        # PASO 6: GENERAR HTML Y AUDIOS
        # ============================================
        print("\n📄 PASO 6: Generando boletin HTML y audios...", flush=True)
        
        html_file = None
        try:
            html_file = generate_cooperative_document(summaries)
        except Exception as e:
            print(f"❌ Error en generate_cooperative_document: {e}", flush=True)
            traceback.print_exc()
            return False
        
        if not html_file:
            print("❌ No se genero HTML", flush=True)
            return False
        
        print(f"✅ HTML generado: {html_file}", flush=True)
        
        # Buscar audios generados
        date_str = datetime.now().strftime('%Y-%m-%d')
        for code in ['CO', 'PA', 'CR', 'DO']:
            audio_file = f"audio_{code}_{date_str}.mp3"
            if os.path.exists(audio_file):
                audio_files.append(audio_file)
        
        # ============================================
        # PASO 7: COPIAR A LA RAIZ
        # ============================================
        print("\n🌐 PASO 7: Copiando archivos a la raiz...", flush=True)
        
        latest_html = os.path.join(HISTORY_FOLDER, html_file)
        if os.path.exists(latest_html):
            try:
                shutil.copy(latest_html, "index.html")
                print("✅ index.html generado", flush=True)
            except Exception as e:
                print(f"⚠️ Error copiando index.html: {e}", flush=True)
        elif os.path.exists(html_file):
            try:
                shutil.copy(html_file, "index.html")
                print("✅ index.html generado desde raiz", flush=True)
            except Exception as e:
                print(f"⚠️ Error copiando index.html: {e}", flush=True)
        
        # ============================================
        # PASO 8: SUBIR A DRIVE
        # ============================================
        print("\n☁️ PASO 8: Subiendo a Google Drive...", flush=True)
        upload_success = upload_to_drive(service, html_file, audio_files)
        
        if upload_success:
            print("✅ Subida a Drive completada", flush=True)
        else:
            print("⚠️ Subida a Drive falló o no se configuró", flush=True)
        
        # ============================================
        # PASO 9: LIMPIAR HISTORICO
        # ============================================
        print(f"\n🗑️ PASO 9: Limpiando historico (manteniendo {MAX_HISTORY_DAYS} dias)...", flush=True)
        cleanup_old_history()
        
        # ============================================
        # FINALIZAR
        # ============================================
        elapsed = time.time() - start_time
        print("\n" + "="*70, flush=True)
        print("✅ AGENTE COMPLETADO CON EXITO", flush=True)
        print(f"⏱️ Tiempo total: {elapsed:.1f} segundos", flush=True)
        print("="*70, flush=True)
        
        # Verificar archivos generados
        print("\n📁 Archivos generados:", flush=True)
        for f in os.listdir('.'):
            if f in ['index.html', 'resumen_cooperativo.mp3'] or f.startswith('audio_'):
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
    
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_cooperative_agent()
    sys.exit(0 if success else 1)