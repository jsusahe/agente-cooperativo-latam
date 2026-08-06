# main.py - VERSIÓN OPTIMIZADA
import os
import json
import shutil
import sys
import time
from datetime import datetime
from typing import Dict, Any

from cooperative_fetcher import get_cooperative_news
from cooperative_processor import process_cooperative_news
from summary_generator_coop import generate_cooperative_summaries
from document_generator_coop import generate_cooperative_document
from audio_generator import generate_audio
from drive_uploader import authenticate_drive, upload_file_to_drive

HISTORY_FOLDER = "historial_cooperativo"
MAX_HISTORY_DAYS = 30


def ensure_history_folder():
    if not os.path.exists(HISTORY_FOLDER):
        os.makedirs(HISTORY_FOLDER)
        print(f"✅ Carpeta '{HISTORY_FOLDER}' creada")


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
                print(f"🗑️ Eliminado histórico: {f}")
                mp3_file = file_path.replace(".html", ".mp3")
                if os.path.exists(mp3_file):
                    os.remove(mp3_file)
            except Exception as e:
                print(f"⚠️ Error al eliminar {f}: {e}")


def run_cooperative_agent() -> bool:
    start_time = time.time()
    
    print("\n" + "="*70)
    print(f"🏢 AGENTE DE NOTICIAS COOPERATIVAS LATINOAMERICANAS")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    if not deepseek_key:
        print("❌ ERROR: DEEPSEEK_API_KEY no está configurada")
        return False
    
    ensure_history_folder()
    
    try:
        print("\n📡 PASO 1: Obteniendo noticias (paralelo)...")
        raw_data = get_cooperative_news(max_workers=8)
        
        if not raw_data:
            print("❌ No se obtuvieron datos")
            return False
        
        print("\n🔍 PASO 2: Procesando noticias...")
        processed_data = process_cooperative_news(raw_data)
        
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
        
        print("\n🧠 PASO 3: Generando resúmenes (paralelo)...")
        summaries = generate_cooperative_summaries(processed_data)
        
        print("\n📄 PASO 4: Generando boletín HTML...")
        html_file = generate_cooperative_document(summaries)
        
        print("\n🎧 PASO 5: Generando audio del resumen regional...")
        audio_file = None
        regional_summary = summaries.get('REGIONAL', {}).get('summary', '')
        if regional_summary and len(regional_summary) > 50:
            audio_filename = f"resumen_cooperativo_{datetime.now().strftime('%Y-%m-%d')}.mp3"
            audio_file = generate_audio(regional_summary, audio_filename)
            if audio_file and os.path.exists(audio_file):
                shutil.copy(audio_file, "resumen_cooperativo.mp3")
                print(f"✅ Audio generado: {audio_file}")
        
        print("\n📁 PASO 6: Archivando en histórico...")
        if os.path.exists(html_file):
            target_path = os.path.join(HISTORY_FOLDER, html_file)
            shutil.move(html_file, target_path)
            print(f"✅ HTML archivado: {target_path}")
        
        if audio_file and os.path.exists(audio_file):
            target_path = os.path.join(HISTORY_FOLDER, audio_file)
            shutil.move(audio_file, target_path)
            print(f"✅ Audio archivado: {target_path}")
        
        print("\n🌐 PASO 7: Preparando archivos para la web...")
        latest_html = os.path.join(HISTORY_FOLDER, f"cooperativo_{datetime.now().strftime('%Y-%m-%d')}.html")
        if os.path.exists(latest_html):
            shutil.copy(latest_html, "index.html")
            print("✅ index.html actualizado")
        
        print(f"\n🗑️ PASO 8: Limpiando histórico...")
        cleanup_old_history()
        
        if os.environ.get('PARENT_FOLDER_ID'):
            print("\n☁️ PASO 9: Subiendo a Google Drive...")
            try:
                service = authenticate_drive()
                if service:
                    latest_html = os.path.join(HISTORY_FOLDER, f"cooperativo_{datetime.now().strftime('%Y-%m-%d')}.html")
                    if os.path.exists(latest_html):
                        upload_file_to_drive(
                            service,
                            f"cooperativo_{datetime.now().strftime('%Y-%m-%d')}.html",
                            latest_html,
                            'text/html'
                        )
                    if os.path.exists("index.html"):
                        upload_file_to_drive(service, "index.html", "index.html", "text/html")
                    if os.path.exists("resumen_cooperativo.mp3"):
                        upload_file_to_drive(service, "resumen_cooperativo.mp3", "resumen_cooperativo.mp3", "audio/mpeg")
                    print("✅ Archivos subidos a Drive")
            except Exception as e:
                print(f"⚠️ Error al subir a Drive: {e}")
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print("✅ AGENTE COMPLETADO CON ÉXITO")
        print(f"⏱️ Tiempo total: {elapsed:.1f} segundos")
        print(f"📊 Países procesados: {countries_with_news}")
        print(f"📰 Total de noticias: {total_news}")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN EL AGENTE: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_agent_with_retry(max_retries: int = 2) -> bool:
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
    
    from dotenv import load_dotenv
    load_dotenv()
    
    success = run_agent_with_retry()
    sys.exit(0 if success else 1)