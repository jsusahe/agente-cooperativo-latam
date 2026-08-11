# document_generator_coop.py - CON LOGO, CTA, LISTADO Y VISUALIZACIÓN DE CONTEXTO
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from audio_generator import generate_audio

# 🔥 CONFIGURACIÓN DEL LOGO
LOGO_FILE = "logo-ia-coop-lab.png"

def get_logo_html() -> str:
    """
    Retorna el HTML para mostrar el logo de IA-COOP-LAB.
    Logo a la izquierda y al doble de tamaño (120px).
    """
    logo_style = 'height: 120px; width: auto; margin-right: 20px; border-radius: 10px;'
    
    if os.path.exists(LOGO_FILE):
        return f'<img src="{LOGO_FILE}" alt="IA-COOP-LAB" style="{logo_style}">'
    
    # Fallback: Logo en texto
    return """
    <div style="display: flex; align-items: center; gap: 15px;">
        <div style="background: linear-gradient(135deg, #1a365d, #2b6cb0); 
                    border-radius: 50%; width: 100px; height: 100px; 
                    display: flex; align-items: center; justify-content: center;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
            <span style="font-size: 3.5rem; color: white; font-weight: bold;">IA</span>
        </div>
        <div style="text-align: left;">
            <div style="font-size: 2.2rem; font-weight: bold; color: #1a365d; letter-spacing: 2px;">
                IA-COOP-LAB
            </div>
            <div style="font-size: 1rem; color: #2b6cb0; letter-spacing: 1px;">
                Inteligencia Artificial para el Cooperativismo
            </div>
        </div>
    </div>
    """


def find_audio_file(base_name: str, extensions: List[str] = ['.mp3']) -> Optional[str]:
    """Busca un archivo de audio en múltiples ubicaciones."""
    locations = ['.', 'historial_cooperativo']
    
    for location in locations:
        for ext in extensions:
            filename = f"{base_name}{ext}"
            filepath = os.path.join(location, filename)
            if os.path.exists(filepath):
                return filepath
            
            if '_' in base_name and len(base_name.split('_')) > 2:
                parts = base_name.split('_')
                generic_name = f"{parts[0]}_{parts[1]}{ext}"
                generic_path = os.path.join(location, generic_name)
                if os.path.exists(generic_path):
                    return generic_path
    
    return None


def get_audio_url(audio_path: str) -> str:
    """Obtiene la URL relativa para el audio en el HTML."""
    if not audio_path:
        return None
    
    if audio_path.startswith('historial_cooperativo/'):
        return audio_path
    
    return os.path.basename(audio_path)


def get_flag_html(country_code: str, country_name: str) -> str:
    """
    Retorna el HTML para mostrar la bandera de un país.
    Usa imágenes SVG desde CDN con fallback a emoji.
    """
    flag_urls = {
        'CO': 'https://flagcdn.com/w80/co.png',
        'PA': 'https://flagcdn.com/w80/pa.png',
        'CR': 'https://flagcdn.com/w80/cr.png',
        'DO': 'https://flagcdn.com/w80/do.png',
    }
    
    flag_url = flag_urls.get(country_code)
    if flag_url:
        return f'<img src="{flag_url}" alt="Bandera de {country_name}" style="height: 40px; width: auto; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">'
    
    flags = {
        'CO': '🇨🇴', 'PA': '🇵🇦', 'CR': '🇨🇷', 'DO': '🇩🇴'
    }
    return f'<span style="font-size: 2.5rem; line-height: 1; font-family: \'Segoe UI Emoji\', \'Apple Color Emoji\', \'Noto Color Emoji\', sans-serif;">{flags.get(country_code, "🏳️")}</span>'


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
    
    # 🔥 URL base para acceder a los archivos históricos (usando raw.githubusercontent.com)
    # Ajusta 'cygnuscooperativo' y 'ia-coop-lab' según tu usuario y nombre de repositorio
    repo_url = "https://raw.githubusercontent.com/cygnuscooperativo/ia-coop-lab/main/historial_cooperativo/"
    
    for filename in recent_files:
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
    """Genera el HTML del boletin cooperativo con IA-COOP-LAB y manejo de contenido contextual"""
    
    date_str = datetime.now().strftime("%A, %d de %B de %Y")
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Buscar audio regional
    regional_audio_base = f"resumen_cooperativo_{current_date}"
    regional_audio_found = find_audio_file(regional_audio_base)
    
    if not regional_audio_found:
        regional_audio_found = find_audio_file("resumen_cooperativo")
    
    regional_audio_url = get_audio_url(regional_audio_found) if regional_audio_found else None
    
    # Obtener TIP IA-COOP-LAB
    coop_tip = summaries.get('COOP_TIP', {})
    tip_title = coop_tip.get('title', 'TIP IA-COOP-LAB del dia')
    tip_text = coop_tip.get('summary', '')
    tip_area = coop_tip.get('area', 'General')
    tip_phase = coop_tip.get('phase', 'LABORAR')
    
    # Logo
    logo_html = get_logo_html()
    
    # Listado histórico
    history_html = generate_history_list()
    
    html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IA-COOP-LAB - Boletín Cooperativo {current_date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f0f4f8;
            color: #2d3748;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background: linear-gradient(135deg, #1a365d, #2b6cb0);
            color: white;
            padding: 25px 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
        }}
        header .logo-container {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        header .logo-container img {{
            height: 120px;
            width: auto;
            border-radius: 10px;
            background: white;
            padding: 8px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }}
        header .header-text {{
            text-align: left;
        }}
        header .header-text h1 {{
            font-size: 2.5rem;
            font-weight: bold;
            letter-spacing: 3px;
            margin: 0;
        }}
        header .header-text .subtitle {{
            font-size: 1rem;
            opacity: 0.8;
            letter-spacing: 2px;
        }}
        header .header-right {{
            text-align: right;
        }}
        header .header-right .date {{
            font-size: 1rem;
            opacity: 0.8;
        }}
        header .header-right .badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            margin-top: 5px;
            font-size: 0.8rem;
        }}
        
        .tip-section {{
            background: linear-gradient(135deg, #f6e05e, #ed8936);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            border: 2px solid #dd6b20;
        }}
        .tip-section h2 {{
            color: #744210;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .tip-section .tip-meta {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin: 10px 0;
        }}
        .tip-section .tip-meta span {{
            background: rgba(255,255,255,0.5);
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
            color: #744210;
        }}
        .tip-section .tip-content {{
            background: rgba(255,255,255,0.7);
            padding: 15px;
            border-radius: 10px;
            margin-top: 10px;
            border-left: 4px solid #dd6b20;
        }}
        
        .country-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }}
        .country-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-top: 5px solid #2b6cb0;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .country-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.15);
        }}
        .country-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
            flex-wrap: wrap;
        }}
        .country-flag {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .country-flag img {{
            height: 35px;
            width: auto;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }}
        .country-flag span {{
            font-size: 2.5rem;
            line-height: 1;
        }}
        .country-title {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #2d3748;
        }}
        .country-meta {{
            font-size: 0.85rem;
            color: #718096;
            margin-left: auto;
        }}
        
        .summary-text {{
            background: #f7fafc;
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 4px solid #2b6cb0;
            font-size: 0.95rem;
            max-height: 300px;
            overflow-y: auto;
        }}
        .summary-text p {{ white-space: pre-wrap; }}
        
        .audio-player {{
            background: #edf2f7;
            padding: 10px 15px;
            border-radius: 10px;
            margin: 10px 0;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .audio-player audio {{ flex: 1; min-width: 200px; }}
        .audio-player .download-link {{
            font-size: 0.85rem;
            color: #2b6cb0;
            text-decoration: none;
        }}
        .audio-player .download-link:hover {{ text-decoration: underline; }}
        
        .news-list {{ margin-top: 15px; }}
        .news-list-title {{ font-weight: 600; color: #2d3748; margin-bottom: 10px; display: block; }}
        .news-item {{
            padding: 10px 0;
            border-bottom: 1px solid #edf2f7;
        }}
        .news-item:last-child {{ border-bottom: none; }}
        .news-title {{ font-weight: 600; color: #2d3748; }}
        .news-summary {{ font-size: 0.9rem; color: #4a5568; margin-top: 3px; }}
        .news-source {{
            font-size: 0.8rem;
            color: #718096;
            display: block;
            margin-top: 3px;
        }}
        .news-source .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.65rem;
            font-weight: 600;
            margin-right: 5px;
        }}
        .badge-supervision {{ background: #e53e3e; color: white; }}
        .badge-national_association {{ background: #2b6cb0; color: white; }}
        .badge-regional_association {{ background: #3182ce; color: white; }}
        .badge-employee_fund {{ background: #38a169; color: white; }}
        .badge-solidarist {{ background: #d69e2e; color: white; }}
        .badge-media {{ background: #805ad5; color: white; }}
        .badge-cooperative {{ background: #6b46c1; color: white; }}
        .badge-video {{ background: #e53e3e; color: white; }}
        .badge-guarantee {{ background: #2f855a; color: white; }}
        .badge-government {{ background: #2c5282; color: white; }}
        .badge-other {{ background: #a0aec0; color: white; }}
        
        .regional-section {{
            background: linear-gradient(135deg, #fbd38d, #f6ad55);
            padding: 25px;
            border-radius: 15px;
            margin-top: 30px;
            border: 2px solid #dd6b20;
        }}
        .regional-section h2 {{ color: #744210; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }}
        .regional-section .summary-text {{ background: rgba(255,255,255,0.7); border-left-color: #dd6b20; }}
        .regional-section .audio-player {{ background: rgba(255,255,255,0.7); }}
        
        .trends {{
            margin-top: 15px;
            padding: 15px;
            background: rgba(255,255,255,0.5);
            border-radius: 10px;
        }}
        .trends h4 {{ color: #744210; margin-bottom: 8px; }}
        .trends ul {{ list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }}
        .trends li {{
            background: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
            color: #744210;
            border: 1px solid #dd6b20;
        }}
        
        .no-news {{ color: #718096; font-style: italic; padding: 15px; text-align: center; }}
        .no-audio {{ color: #a0aec0; font-size: 0.85rem; font-style: italic; }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #718096;
            border-top: 1px solid #e2e8f0;
        }}
        .footer .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }}
        .footer .stat-item {{
            background: white;
            padding: 8px 20px;
            border-radius: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        @media (max-width: 768px) {{
            .country-grid {{ grid-template-columns: 1fr; }}
            header {{
                flex-direction: column;
                text-align: center;
            }}
            header .header-text {{
                text-align: center;
            }}
            header .header-right {{
                text-align: center;
                margin-top: 10px;
            }}
            .footer .stats {{ flex-direction: column; align-items: center; gap: 10px; }}
            .audio-player {{ flex-direction: column; }}
            .audio-player audio {{ width: 100%; }}
            .country-header {{ flex-wrap: wrap; }}
            .country-meta {{ margin-left: 0; }}
        }}
        .scroll-top {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #2b6cb0;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            font-size: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: background 0.2s;
        }}
        .scroll-top:hover {{ background: #1a365d; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-container">
                {logo_html}
                <div class="header-text">
                    <h1>IA-COOP-LAB</h1>
                    <div class="subtitle">Inteligencia Artificial para el Cooperativismo</div>
                </div>
            </div>
            <div class="header-right">
                <div class="date">📅 {date_str}</div>
                <div class="badge">🔄 Actualizacion automatica diaria</div>
            </div>
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
            
            <!-- 🔥 CTA y Etapa -->
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
    """
    
    # Procesar cada país
    country_codes = ['CO', 'PA', 'CR', 'DO']
    country_names = {
        'CO': 'Colombia', 
        'PA': 'Panama', 
        'CR': 'Costa Rica', 
        'DO': 'Republica Dominicana'
    }
    
    for code in country_codes:
        summary = summaries.get(code, {})
        country = summary.get('country', country_names.get(code, 'Desconocido'))
        has_news = summary.get('has_news', False)
        is_contextual = summary.get('is_contextual', False)
        
        flag_html = get_flag_html(code, country)
        
        country_audio_base = f"audio_{code}_{current_date}"
        country_audio_found = find_audio_file(country_audio_base)
        country_audio_url = get_audio_url(country_audio_found) if country_audio_found else None
        
        html_content += f"""
            <div class="country-card">
                <div class="country-header">
                    <div class="country-flag">{flag_html}</div>
                    <span class="country-title">{country}</span>
                    <span class="country-meta">{summary.get('news_count', 0)} noticias</span>
                </div>
        """
        
        summary_text = summary.get('summary', '')
        
        if has_news:
            # 🔥 Resumen de noticias
            summary_text = summary_text.replace('\n\n', '</p><p>').replace('\n', ' ')
            
            html_content += f"""
                <div class="summary-text">
                    <p>{summary_text}</p>
                </div>
            """
            
            if country_audio_url:
                html_content += f"""
                    <div class="audio-player">
                        <span>🎧 Escuchar resumen de {country}:</span>
                        <audio controls preload="none">
                            <source src="{country_audio_url}" type="audio/mpeg">
                            Tu navegador no soporta audio.
                        </audio>
                        <a href="{country_audio_url}" download class="download-link">⬇️ Descargar</a>
                    </div>
                """
            else:
                html_content += f"""
                    <div class="audio-player no-audio">
                        ⚠️ Audio no disponible para {country}
                    </div>
                """
            
            key_topics = summary.get('key_topics', [])
            if key_topics:
                html_content += f"""
                    <div style="margin: 10px 0;">
                        <strong>🏷️ Temas destacados:</strong>
                        <span style="display: flex; flex-wrap: wrap; gap: 5px; margin-top: 5px;">
                """
                for topic in key_topics[:4]:
                    html_content += f'<span style="background: #e2e8f0; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem;">{topic}</span>'
                html_content += """
                        </span>
                    </div>
                """
            
            news_items = summary.get('news_items', [])
            if news_items:
                html_content += '<div class="news-list"><span class="news-list-title">📰 Noticias destacadas:</span>'
                for item in news_items[:5]:
                    title = item.get('title', 'Sin titulo')
                    source = item.get('source_name', 'Fuente desconocida')
                    category = item.get('source_category', 'other')
                    summary_text_item = item.get('summary', '')[:200]
                    link = item.get('link', '#')
                    
                    badge_class = f"badge-{category}" if category in ['supervision', 'national_association', 'regional_association', 'employee_fund', 'solidarist', 'media', 'cooperative', 'video', 'guarantee', 'government'] else 'badge-other'
                    category_display = {
                        'supervision': 'Supervision',
                        'national_association': 'Confederacion Nacional',
                        'regional_association': 'Confederacion Regional',
                        'employee_fund': 'Fondo de Empleados',
                        'solidarist': 'Solidarista',
                        'media': 'Medios',
                        'cooperative': 'Cooperativa',
                        'video': 'Video',
                        'guarantee': 'Garantia',
                        'government': 'Gobierno',
                        'other': 'General'
                    }.get(category, 'General')
                    
                    html_content += f"""
                        <div class="news-item">
                            <div class="news-title">{title}</div>
                            {f'<div class="news-summary">{summary_text_item}</div>' if summary_text_item else ''}
                            <span class="news-source">
                                <span class="badge {badge_class}">{category_display}</span>
                                📌 {source}
                                {' <a href="'+link+'" target="_blank" style="color: #2b6cb0;">🔗 Ver fuente</a>' if link and link != '#' else ''}
                            </span>
                        </div>
                    """
                html_content += '</div>'
                
        elif is_contextual and summary_text:
            # 🔥 CONTEXTO: Cuando no hay noticias pero hay un resumen contextual
            summary_text = summary_text.replace('\n\n', '</p><p>').replace('\n', ' ')
            
            html_content += f"""
                <div class="summary-text" style="background: #fff3e0; border-left-color: #ed8936;">
                    <p>{summary_text}</p>
                </div>
                <div style="margin-top: 10px; font-size: 0.9rem; color: #718096; display: flex; gap: 5px; align-items: center;">
                    <span style="font-size: 1.2rem;">ℹ️</span> Información general del sector cooperativo (sin noticias destacadas hoy).
                </div>
            """
            if country_audio_url:
                html_content += f"""
                    <div class="audio-player">
                        <span>🎧 Escuchar resumen de {country}:</span>
                        <audio controls preload="none">
                            <source src="{country_audio_url}" type="audio/mpeg">
                            Tu navegador no soporta audio.
                        </audio>
                        <a href="{country_audio_url}" download class="download-link">⬇️ Descargar</a>
                    </div>
                """
            else:
                html_content += f"""
                    <div class="audio-player no-audio">
                        ⚠️ Audio no disponible para {country}
                    </div>
                """
        else:
            # 🔥 Mensaje vacío tradicional
            html_content += f"""
                <div class="no-news">
                    <p>⚠️ No se encontraron noticias cooperativas para {country} en los ultimos dias.</p>
                </div>
            """
        
        html_content += '</div>'
    
    # Seccion Regional
    regional = summaries.get('REGIONAL', {})
    if regional.get('has_news'):
        summary_text = regional.get('summary', '')
        summary_text = summary_text.replace('\n\n', '</p><p>').replace('\n', ' ')
        
        html_content += f"""
            </div>
            <div class="regional-section">
                <h2>🌎 Panorama Regional</h2>
                <div class="summary-text">
                    <p>{summary_text}</p>
                </div>
        """
        
        if regional_audio_url:
            html_content += f"""
                <div class="audio-player">
                    <span>🎧 Escuchar resumen regional:</span>
                    <audio controls preload="none">
                        <source src="{regional_audio_url}" type="audio/mpeg">
                        Tu navegador no soporta audio.
                    </audio>
                    <a href="{regional_audio_url}" download class="download-link">⬇️ Descargar</a>
                </div>
            """
        else:
            html_content += f"""
                <div class="audio-player no-audio">
                    ⚠️ Audio regional no disponible
                </div>
            """
        
        trends = regional.get('trends', [])
        if trends:
            html_content += f"""
                <div class="trends">
                    <h4>📈 Tendencias Regionales</h4>
                    <ul>
                        {''.join(f'<li>{t}</li>' for t in trends[:5])}
                    </ul>
                </div>
            """
        
        html_content += '</div>'
    
    # Calcular estadisticas
    total_news = sum(s.get('news_count', 0) for s in summaries.values() if isinstance(s, dict) and s.get('has_news') and s.get('country') != 'IA-COOP-LAB')
    
    # 🔥 Añadir sección de histórico
    html_content += f"""
        
        <div style="margin-top: 40px; background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            {history_html}
        </div>
        
        <div class="footer">
            <div class="stats">
                <span class="stat-item">📰 Total noticias: {total_news}</span>
                <span class="stat-item">🌎 Paises: 4</span>
                <span class="stat-item">🔄 Actualizado: {datetime.now().strftime('%H:%M:%S')}</span>
                <span class="stat-item">💡 IA-COOP-LAB</span>
            </div>
            <p>📊 Generado automaticamente por el <strong>Agente IA-COOP-LAB</strong></p>
            <p style="font-size: 0.8rem; margin-top: 10px;">
                Fuentes: Superintendencias, Confederaciones, Federaciones, Fondos de Empleados y medios especializados
            </p>
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


def generate_audio_for_country(country_code: str, country_name: str, summary_text: str) -> Optional[str]:
    """Genera audio para el resumen de un pais"""
    if not summary_text or len(summary_text) < 50:
        print(f"⚠️ Texto muy corto para generar audio de {country_name} ({len(summary_text)} caracteres)", flush=True)
        return None
    
    audio_filename = f"audio_{country_code}_{datetime.now().strftime('%Y-%m-%d')}.mp3"
    
    text_for_audio = summary_text[:4000]
    intro = f"Resumen de noticias cooperativas de {country_name}. "
    full_text = intro + text_for_audio
    
    print(f"  🔊 Generando audio para {country_name} ({len(full_text)} caracteres)...", flush=True)
    audio_file = generate_audio(full_text, audio_filename)
    
    if audio_file and os.path.exists(audio_file):
        print(f"    ✅ Audio generado: {audio_file} ({os.path.getsize(audio_file)} bytes)", flush=True)
        return audio_file
    else:
        print(f"    ❌ Error al generar audio para {country_name}", flush=True)
        return None


def generate_audio_for_region(regional_summary: str) -> Optional[str]:
    """Genera audio para el resumen regional"""
    if not regional_summary or len(regional_summary) < 50:
        print(f"⚠️ Texto regional muy corto para generar audio ({len(regional_summary)} caracteres)", flush=True)
        return None
    
    audio_filename = f"resumen_cooperativo_{datetime.now().strftime('%Y-%m-%d')}.mp3"
    
    intro = "Resumen regional de noticias cooperativas de Latinoamerica. "
    full_text = intro + regional_summary[:4000]
    
    print(f"  🔊 Generando audio regional ({len(full_text)} caracteres)...", flush=True)
    audio_file = generate_audio(full_text, audio_filename)
    
    if audio_file and os.path.exists(audio_file):
        print(f"    ✅ Audio regional generado: {audio_file} ({os.path.getsize(audio_file)} bytes)", flush=True)
        try:
            shutil.copy(audio_file, "resumen_cooperativo.mp3")
            print(f"    ✅ Copiado a resumen_cooperativo.mp3", flush=True)
        except Exception as e:
            print(f"    ⚠️ Error al copiar audio regional: {e}", flush=True)
        return audio_file
    else:
        print(f"    ❌ Error al generar audio regional", flush=True)
        return None


def generate_cooperative_document(summaries: Dict) -> str:
    """Genera el documento completo del boletin cooperativo con audios"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"cooperativo_{date_str}.html"
    
    print("\n" + "="*60, flush=True)
    print("🎧 GENERANDO AUDIOS", flush=True)
    print("="*60, flush=True)
    
    audio_files = []
    
    print("\n📢 Audios por pais:", flush=True)
    country_codes = ['CO', 'PA', 'CR', 'DO']
    for code in country_codes:
        summary = summaries.get(code, {})
        # 🔥 CORRECCIÓN: Generar audio si existe 'summary', independientemente de 'has_news'
        if summary.get('summary'):
            country = summary.get('country', 'Desconocido')
            audio_file = generate_audio_for_country(code, country, summary.get('summary', ''))
            if audio_file:
                audio_files.append(audio_file)
    
    print("\n📢 Audio regional:", flush=True)
    regional = summaries.get('REGIONAL', {})
    if regional.get('has_news') and regional.get('summary'):
        regional_audio = generate_audio_for_region(regional.get('summary', ''))
        if regional_audio:
            audio_files.append(regional_audio)
    else:
        print("  ⚠️ No hay resumen regional para generar audio", flush=True)
    
    print("\n📄 Generando HTML con reproductores de audio...", flush=True)
    generate_cooperative_html(summaries, filename)
    generate_cooperative_html(summaries, "index.html")
    
    print(f"\n✅ Documento generado: {filename}", flush=True)
    print(f"📁 Audios generados: {len(audio_files)}", flush=True)
    for f in audio_files:
        print(f"   - {f}", flush=True)
    
    return filename


if __name__ == '__main__':
    print("=== PRUEBA DE DOCUMENT_GENERATOR_COOP ===")
    
    test_data = {
        'CO': {
            'country': 'Colombia',
            'has_news': True,
            'summary': 'El sector cooperativo colombiano presenta avances significativos en regulacion y supervision.',
            'news_count': 8,
            'key_topics': ['Regulacion', 'Crecimiento'],
            'news_items': []
        },
        'PA': {
            'country': 'Panama',
            'has_news': False,
            'is_contextual': True,
            'summary': 'El cooperativismo en Panama se destaca por su compromiso con el desarrollo local. IPACOOP y CONACOOP trabajan para fortalecer el movimiento.',
            'news_count': 0,
            'key_topics': ['Cooperativismo', 'Desarrollo']
        },
        'REGIONAL': {
            'country': 'Latinoamerica',
            'has_news': True,
            'summary': 'El cooperativismo latinoamericano muestra un crecimiento sostenido.',
            'trends': ['Inclusion financiera', 'Regulacion armonizada']
        },
        'COOP_TIP': {
            'country': 'IA-COOP-LAB',
            'has_news': True,
            'summary': 'La metodologia IA-COOP-LAB propone usar IA para analizar el comportamiento de los socios y anticipar sus necesidades financieras.',
            'title': 'Analisis de Socios con IA',
            'area': 'Gestion de Socios',
            'phase': 'ANALIZAR'
        }
    }
    
    generate_cooperative_document(test_data)
    print("✅ Documento de prueba generado")