# pdf_loader.py - Cargador del documento IA-COOP-LAB
import os
import sys
from pypdf import PdfReader

# 🔥 Configurar flush de salida para que los logs se vean en tiempo real
sys.stdout.reconfigure(line_buffering=True)

# Archivos esperados (las partes en las que dividirás el PDF)
# Asegúrate de que estos archivos estén en la raíz del repositorio
PDF_PARTS = [
    "ia_coop_lab_part1.pdf",
    "ia_coop_lab_part2.pdf",
    "ia_coop_lab_part3.pdf"
]

def load_pdf_text(max_chars: int = 12000) -> str:
    """
    Carga el texto de los archivos PDF y lo devuelve concatenado.
    Por defecto, limita a los primeros 12,000 caracteres para no saturar el prompt de la IA.
    Si no encuentra ningún archivo, retorna una cadena vacía.
    """
    full_text = ""
    parts_loaded = 0
    
    for path in PDF_PARTS:
        if not os.path.exists(path):
            print(f"⚠️ No se encontró: {path}", flush=True)
            continue
        
        try:
            print(f"📖 Leyendo {path}...", flush=True)
            reader = PdfReader(path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                    # Si ya alcanzamos el límite, cortamos y retornamos
                    if len(full_text) >= max_chars:
                        return full_text[:max_chars]
            parts_loaded += 1
        except Exception as e:
            print(f"❌ Error al leer {path}: {e}", flush=True)
    
    if parts_loaded == 0:
        print("⚠️ No se pudo cargar ningún archivo PDF. El TIP usará el contenido predeterminado.", flush=True)
        return ""
    
    print(f"✅ Cargados {len(full_text)} caracteres del documento IA-COOP-LAB.", flush=True)
    return full_text