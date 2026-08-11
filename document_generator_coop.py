# document_generator_coop.py - CON LOGO, CTA Y LISTADO DE BOLETINES
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from audio_generator import generate_audio

# 🔥 CONFIGURACIÓN DEL LOGO
LOGO_FILE = "logo-ia-coop-lab.png"

def get_logo_html() -> str:
    # ... (código existente) ...
    pass

def find_audio_file(base_name: str, extensions: List[str] = ['.mp3']) -> Optional[str]:
    # ... (código existente) ...
    pass

def get_audio_url(audio_path: str) -> str:
    # ... (código existente) ...
    pass

def get_flag_html(country_code: str, country_name: str) -> str:
    # ... (código existente) ...
    pass

def generate_history_list() -> str:
    """
    🔥 Genera el HTML con el listado de los últimos 10 boletines generados.
    Se asume que los boletines están en la carpeta 'historial_cooperativo'.
    """
    history_folder = "historial_cooperativo"
    if not os.path.exists(history_folder):
        return "<p>No hay boletines históricos disponibles.</p>"
    
    files = [f for f in os.listdir(history_folder) if f.startswith("cooperativo_") and f.endswith(".html")]
    files.sort(reverse=True)  # Más reciente primero
    recent_files = files[:10]
    
    if not recent_files:
        return "<p>No hay boletines históricos disponibles.</p>"
    
    html = "<h2>📚 Últimos 10 Boletines</h2><ul style='list-style: none; padding: 0;'>"
    
    # Asumiendo que el repositorio es público. Ajusta la URL base si es privado o si usas Drive.
    # Para GitHub Pages, la URL base es: https://raw.githubusercontent.com/USUARIO/REPO/main/historial_cooperativo/
    # Cambia 'main' por 'master' si es necesario.
    repo_url = "https://raw.githubusercontent.com/cygnuscooperativo/ia-coop-lab/main/historial_cooperativo/"
    
    for filename in recent_files:
        # Extraer la fecha del nombre del archivo (formato: cooperativo_YYYY-MM-DD.html)
        date_str = filename.replace("cooperativo_", "").replace(".html", "")
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            display_date = date_obj.strftime("%d/%m/%Y")
        except ValueError:
            display_date = date_str
        
        file_url = repo_url + filename
        html += f"<li style='padding: 8px 0; border-bottom: 1px solid #edf2f7;'><a href='{file_url}' target='_blank' style='color: #2b6cb0; text-decoration: none;'>📄 Boletín del {display_date}</a></li>"
    
    html += "</ul>"
    return html

def generate_cooperative_html(summaries: Dict, output_filename="index.html") -> str:
    """Genera el HTML del boletin cooperativo con IA-COOP-LAB, logo, CTA y listado histórico"""
    
    date_str = datetime.now().strftime("%A, %d de %B de %Y")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # ... (código existente para audios y datos) ...
    # (Mantener toda la lógica de audio existente)
    
    # Obtener TIP IA-COOP-LAB
    coop_tip = summaries.get('COOP_TIP', {})
    tip_title = coop_tip.get('title', 'TIP IA-COOP-LAB del dia')
    tip_text = coop_tip.get('summary', '')
    tip_area = coop_tip.get('area', 'General')
    tip_phase = coop_tip.get('phase', 'LABORAR')
    
    # 🔥 Obtener el logo HTML
    logo_html = get_logo_html()
    
    # 🔥 Generar el listado de boletines históricos
    history_html = generate_history_list()
    
    # ... (continuar con el HTML del boletín, pero modificando la sección del TIP y añadiendo el histórico al final) ...
    
    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <!-- ... (código CSS existente) ... -->
</head>
<body>
    <div class="container">
        <header>
            <!-- ... (código header existente) ... -->
        </header>
        
        <!-- SECCION TIP IA-COOP-LAB -->
        <div class="tip-section">
            <h2>💡 TIP IA-COOP-LAB</h2>
            <div class="tip-meta">
                <span>📂 Area: {tip_area}</span>
                <span>🔄 Fase: {tip_phase}</span>
            </div>
            <div class="tip-content">
                <h3 style="color: #744210;">{tip_title}</h3>
                <p>{tip_text}</p>
            </div>
            
            <!-- 🔥 NUEVO: CTA y Etapa -->
            <div style="margin-top: 15px; text-align: center; background: rgba(255,255,255,0.6); padding: 10px; border-radius: 8px; border: 2px solid #dd6b20;">
                <p style="margin: 0; font-weight: bold; color: #744210;">
                    🚀 Esta es una aplicación práctica de la <strong>Fase {tip_phase}</strong> de la metodología IA-COOP-LAB.
                </p>
                <p style="margin: 5px 0 0 0; font-size: 0.9rem;">
                    ¿Quieres aprender más y llevar la inteligencia artificial a tu cooperativa? 
                    <a href="https://www.cygnuscooperativo.com/iacooplab" target="_blank" style="color: #2b6cb0; font-weight: bold; text-decoration: underline;">
                        ¡Inscríbete ahora en IA-COOP-LAB!
                    </a>
                </p>
            </div>
        </div>
        
        <div class="country-grid">
            <!-- ... (código de países existente) ... -->
            # (Mantener el bucle que genera las tarjetas de los países)
        </div>
        
        <!-- SECCION REGIONAL -->
        <div class="regional-section">
            <!-- ... (código regional existente) ... -->
        </div>
        
        <!-- 🔥 NUEVO: LISTADO DE BOLETINES HISTÓRICOS -->
        <div style="margin-top: 40px; background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            {history_html}
        </div>
        
        <div class="footer">
            <!-- ... (código footer existente) ... -->
        </div>
    </div>
    
    <a href="#" class="scroll-top" title="Volver arriba">↑</a>
</body>
</html>
    """
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Documento HTML generado: {output_filename}", flush=True)
    return output_filename

# ... (resto del código existente para generación de audio) ...