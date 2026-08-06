# diagnostic.py - Script para diagnosticar el agente paso a paso
import os
import sys
import time
import traceback
from datetime import datetime

print("="*70)
print("🔍 DIAGNÓSTICO DEL AGENTE IA-COOP-LAB")
print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

# 1. Verificar Python
print("\n1. ✅ PYTHON")
print(f"   Version: {sys.version}")
print(f"   Path: {sys.executable}")

# 2. Verificar variables de entorno
print("\n2. ✅ VARIABLES DE ENTORNO")
env_vars = ['DEEPSEEK_API_KEY', 'YOUTUBE_API_KEY', 'PARENT_FOLDER_ID', 'DRIVE_TOKEN_JSON']
for var in env_vars:
    value = os.environ.get(var)
    if value:
        print(f"   ✅ {var}: {value[:15]}...")
    else:
        print(f"   ❌ {var}: No configurada")

# 3. Verificar imports
print("\n3. ✅ IMPORTS")
modules = [
    ('requests', 'requests'),
    ('feedparser', 'feedparser'),
    ('bs4', 'beautifulsoup4'),
    ('json', 'json'),
    ('datetime', 'datetime'),
    ('concurrent.futures', 'ThreadPoolExecutor'),
    ('googleapiclient', 'google-api-python-client'),
    ('google_auth_oauthlib', 'google-auth-oauthlib'),
]

for mod_name, display_name in modules:
    try:
        __import__(mod_name)
        print(f"   ✅ {display_name}")
    except ImportError as e:
        print(f"   ❌ {display_name}: {e}")

# 4. Verificar imports del proyecto
print("\n4. ✅ IMPORTS DEL PROYECTO")
project_modules = [
    'cooperative_fetcher',
    'cooperative_processor',
    'summary_generator_coop',
    'document_generator_coop',
    'audio_generator',
    'drive_uploader',
    'topic_index',
    'youtube_fetcher'
]

for mod in project_modules:
    try:
        __import__(mod)
        print(f"   ✅ {mod}")
    except ImportError as e:
        print(f"   ❌ {mod}: {e}")

# 5. Verificar archivos
print("\n5. ✅ ARCHIVOS")
files = [
    'main.py',
    'config_countries.json',
    'requirements.txt',
    'cooperative_fetcher.py',
    'cooperative_processor.py',
    'summary_generator_coop.py',
    'document_generator_coop.py',
    'audio_generator.py',
    'drive_uploader.py',
    'topic_index.py',
    'youtube_fetcher.py'
]

for f in files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"   ✅ {f} ({size} bytes)")
    else:
        print(f"   ❌ {f} (No encontrado)")

# 6. Verificar config_countries.json
print("\n6. ✅ CONFIG COUNTRIES")
try:
    import json
    with open('config_countries.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    countries = config.get('countries', [])
    print(f"   ✅ Países configurados: {len(countries)}")
    for c in countries:
        name = c.get('name', 'Desconocido')
        print(f"      - {name}")
except Exception as e:
    print(f"   ❌ Error al cargar config: {e}")

# 7. Probar el fetcher
print("\n7. ✅ TEST FETCHER (solo 1 país, 1 fuente)")
try:
    from cooperative_fetcher import CooperativeFetcher
    
    print("   Inicializando fetcher...")
    fetcher = CooperativeFetcher(max_workers=2)
    
    if fetcher.countries:
        test_country = fetcher.countries[0]
        print(f"   País de prueba: {test_country.get('name', 'Desconocido')}")
        
        print("   Ejecutando fetch...")
        start = time.time()
        result = fetcher.fetch_country_news(test_country)
        elapsed = time.time() - start
        
        print(f"   ✅ Fetch completado en {elapsed:.1f}s")
        print(f"   📊 Noticias encontradas: {result.get('total', 0)}")
    else:
        print("   ❌ No hay países configurados")
        
except Exception as e:
    print(f"   ❌ Error en fetcher: {e}")
    traceback.print_exc()

# 8. Resumen final
print("\n" + "="*70)
print("✅ DIAGNÓSTICO COMPLETADO")
print("="*70)