# summary_generator_coop.py - VERSIÓN CON TIP INTELIGENTE, CONTROL DE REPETICIÓN Y ENFOQUE FINANCIERO
import json
import requests
import os
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🔥 Importamos el cargador de PDF
from pdf_loader import load_pdf_text

load_dotenv()

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


class CooperativeSummaryGenerator:
    """Genera resúmenes de noticias cooperativas usando DeepSeek"""
    
    def __init__(self, topic_index=None):
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        self.topic_index = topic_index
        # 🔥 Cargamos el texto del documento IA-COOP-LAB (primeros 15.000 caracteres para más contexto)
        self.pdf_context = load_pdf_text(max_chars=15000)
        
    def _get_country_context(self, country: str) -> str:
        contexts = {
            'Colombia': """
            El sector cooperativo colombiano esta regulado por la Superintendencia de Economia Solidaria.
            Las principales confederaciones son Confecoop (nacional y regional) y Fecolfin para fondos de empleados.
            El sistema incluye cooperativas de ahorro, credito, multiactivas y de trabajo asociado.
            """,
            'Panama': """
            El cooperativismo panameno es supervisado por el IPACOOP (Instituto Panameno Autonomo Cooperativo).
            CONACOOP es la confederacion nacional que agrupa a las cooperativas.
            """,
            'Costa Rica': """
            El sector cooperativo costarricense es supervisado por SUGEF e INFOCOOP.
            Las principales federaciones son FECOOPSE y FEDEAC para cooperativas de ahorro y credito.
            Las asociaciones solidaristas son una figura importante en el sector.
            """,
            'Republica Dominicana': """
            El cooperativismo dominicano es supervisado por la Superintendencia de Bancos.
            IDECOOP es el instituto de desarrollo y credito cooperativo.
            """
        }
        return contexts.get(country, "")
    
    def generate_country_summary(self, country_data: Dict) -> Dict:
        """Genera resumen para un país específico. Si no hay noticias, genera contexto por IA."""
        country_name = country_data.get('country', 'Desconocido')
        country_code = country_data.get('code', 'XX')
        selected_news = country_data.get('selected_news', [])
        
        # 🔥 CASO 1: Hay noticias (nuevas o del índice)
        if selected_news:
            news_text = ""
            for i, item in enumerate(selected_news[:8]):
                title = item.get('title', 'Sin titulo')
                source = item.get('source_name', 'Fuente desconocida')
                summary = item.get('summary', '')[:200]
                category = item.get('source_category', 'general')
                
                news_text += f"{i+1}. Titulo: {title}\n"
                news_text += f"   Fuente: {source}\n"
                news_text += f"   Categoria: {category}\n"
                news_text += f"   Resumen: {summary}\n\n"
            
            country_context = self._get_country_context(country_name)
            
            system_prompt = f"""
            Eres un periodista especializado en el sector cooperativo de {country_name} y Latinoamerica.
            
            CONTEXTO DEL SECTOR:
            {country_context}
            
            Tu tarea es generar un resumen completo y profesional de las noticias y contenido cooperativo del dia.
            
            INSTRUCCIONES OBLIGATORIAS:
            1. El resumen debe tener entre 3-4 parrafos (minimo 250 palabras)
            2. Menciona TODAS las noticias importantes con sus fuentes
            3. Incluye contexto sobre el sector cooperativo en el pais
            4. Menciona las entidades oficiales
            5. Destaca eventos, regulaciones, innovaciones y logros del sector
            6. Usa un tono profesional pero accesible
            
            FORMATO DE SALIDA (JSON):
            {{
                "summary": "Resumen completo en espanol...",
                "key_topics": ["tema1", "tema2", "tema3"],
                "main_sources": ["fuente1", "fuente2"],
                "news_count": Numero de noticias
            }}
            """
            
            user_prompt = f"""
            Estas son las noticias cooperativas de {country_name} para hoy:
            
            {news_text}
            
            Genera un resumen completo que cubra las noticias mas relevantes del sector cooperativo.
            """
            
            result = self._call_deepseek(system_prompt, user_prompt)
            
            if result:
                return {
                    'country': country_name,
                    'has_news': True,
                    'news_items': selected_news[:8],
                    **result
                }
            else:
                return {
                    'country': country_name,
                    'has_news': True,
                    'summary': self._generate_fallback_summary(selected_news),
                    'news_items': selected_news[:8],
                    'key_topics': ['Sector cooperativo'],
                    'main_sources': ['Fuentes diversas'],
                    'news_count': len(selected_news)
                }
        
        # 🔥 CASO 2: No hay noticias. Generar un resumen contextual del sector con IA.
        else:
            country_context = self._get_country_context(country_name)
            
            system_prompt = f"""
            Eres un periodista especializado en el sector cooperativo de {country_name} y Latinoamerica.
            
            CONTEXTO DEL SECTOR:
            {country_context}
            
            Tu tarea es generar un resumen informativo y profesional de 4-5 lineas (aproximadamente 150-200 palabras) 
            sobre el estado actual del cooperativismo en {country_name} para el día de hoy.
            
            INSTRUCCIONES:
            1. Menciona las entidades reguladoras y confederaciones principales.
            2. Destaca la importancia del sector en la economia local.
            3. Menciona los desafios que enfrenta el cooperativismo en el pais.
            4. Usa un tono profesional, positivo y accesible.
            5. Este resumen se usará cuando no haya noticias especificas del día.
            
            FORMATO DE SALIDA (JSON):
            {{
                "summary": "Resumen contextual del sector cooperativo...",
                "key_topics": ["tema1", "tema2", "tema3"],
                "main_sources": ["Fuentes institucionales"],
                "news_count": 0
            }}
            """
            
            user_prompt = f"""
            Genera un resumen general e informativo del sector cooperativo de {country_name} para el día de hoy.
            No hay noticias destacadas, por lo que el resumen debe ser un panorama general del sector.
            """
            
            result = self._call_deepseek(system_prompt, user_prompt)
            
            if result and result.get('summary'):
                return {
                    'country': country_name,
                    'has_news': False,
                    'is_contextual': True,
                    'summary': result.get('summary'),
                    'news_items': [],
                    'key_topics': result.get('key_topics', ['Sector cooperativo']),
                    'main_sources': result.get('main_sources', ['Fuentes institucionales']),
                    'news_count': 0
                }
            else:
                # 🔥 Fallback en caso de que la IA falle
                return {
                    'country': country_name,
                    'has_news': False,
                    'is_contextual': True,
                    'summary': f"Resumen general del sector cooperativo de {country_name}. El cooperativismo en {country_name} se caracteriza por su compromiso con el desarrollo local, la inclusión financiera y la solidaridad. Las entidades reguladoras y las confederaciones trabajan para fortalecer el movimiento, promoviendo la educación cooperativa y la sostenibilidad. A pesar de los desafíos, el sector sigue siendo un pilar fundamental para las comunidades.",
                    'news_items': [],
                    'key_topics': ['Sector cooperativo'],
                    'main_sources': ['Fuentes institucionales'],
                    'news_count': 0
                }
    
    def generate_regional_summary(self, all_countries: Dict) -> Dict:
        """Genera un resumen regional de todas las noticias (siempre en español)"""
        summaries = []
        for code, data in all_countries.items():
            if data.get('has_news') and data.get('summary'):
                country = data.get('country', 'Desconocido')
                summary = data.get('summary', '')[:200]
                summaries.append(f"**{country}**: {summary}...")
        
        if not summaries:
            return {
                'summary': "No se encontraron noticias cooperativas relevantes en la region.",
                'has_news': False
            }
        
        regional_text = "\n\n".join(summaries)
        
        system_prompt = """
        Eres un experto en el sector cooperativo latinoamericano.
        Genera un resumen regional que integre las noticias cooperativas de varios paises.
        **ESCRIBE TU RESPUESTA EXCLUSIVAMENTE EN ESPAÑOL LATINOAMERICANO.**
        
        INSTRUCCIONES:
        1. Identifica tendencias comunes en la region
        2. Destaca diferencias importantes entre paises
        3. Menciona el panorama general del cooperativismo en Latinoamerica
        4. El resumen debe tener 2-3 parrafos (minimo 200 palabras)
        
        FORMATO DE SALIDA (JSON):
        {
            "summary": "Resumen regional en español...",
            "trends": ["tendencia1", "tendencia2"]
        }
        """
        
        user_prompt = f"""
        Resumenes de noticias cooperativas por pais:
        
        {regional_text}
        
        Genera un resumen regional en español que integre estas noticias.
        """
        
        result = self._call_deepseek(system_prompt, user_prompt)
        
        if result:
            return {
                'has_news': True,
                **result
            }
        else:
            return {
                'summary': regional_text[:400],
                'has_news': True,
                'trends': ['Cooperativismo en Latinoamerica']
            }
    
    def generate_coop_tip(self) -> Dict:
        """
        Genera un TIP diario de IA-COOP-LAB basado en el documento oficial.
        - Siempre enfocado en una sola fase y una sola decisión.
        - Siempre con un ejemplo práctico para cooperativas financieras o multiactivas.
        - Consulta el topic_index para evitar repetir fases y decisiones.
        """
        
        # 🔥 1. Obtener las etapas y decisiones ya usadas desde el topic_index
        used_phases = set()
        used_decisions = set()
        
        if self.topic_index:
            for tip in self.topic_index.tips:
                # Extraer fase y decisión del campo 'phase' si está guardado con formato "Etapa X - Decisión Y"
                phase_info = tip.get('phase', '')
                if phase_info:
                    # Intentar extraer fase y decisión del string guardado
                    # Ejemplo: "Proceso Cooperativo - Decisión 1: Orientación Estratégica"
                    parts = phase_info.split(' - ')
                    if len(parts) >= 1:
                        used_phases.add(parts[0].strip())
                    if len(parts) >= 2:
                        used_decisions.add(parts[1].strip())
        
        # 🔥 2. Definir el catálogo de fases y decisiones oficiales (sin incluir las usadas)
        available_content = []
        
        # Lista completa de fases y decisiones (solo 5 etapas, 10 decisiones)
        all_phases = [
            {
                "fase": "Proceso Cooperativo",
                "decisiones": [
                    "Decisión 1: Orientación Estratégica – El Modelo Delta Cooperativo",
                    "Decisión 2: Determinación de Procesos y Grupos de Interés"
                ]
            },
            {
                "fase": "Comportamiento Inteligente",
                "decisiones": [
                    "Decisión 3: Métricas de Desempeño e Indicadores de Gestión",
                    "Decisión 4: Alcance y Análisis de Información"
                ]
            },
            {
                "fase": "Talento Humano, Ética y Gobernanza",
                "decisiones": [
                    "Decisión 5: Ética de la IA – Principios y Aplicación",
                    "Decisión 6: Gobernanza de la IA – Estructuras y Responsabilidades"
                ]
            },
            {
                "fase": "Tecnología de la IA",
                "decisiones": [
                    "Decisión 7: Gestión del Capital Intelectual y Propiedad Intelectual",
                    "Decisión 8: Gestión de la Información y la Base Social"
                ]
            },
            {
                "fase": "Implementación",
                "decisiones": [
                    "Decisión 9: Implementación y Evaluación - Desarrollo de Software",
                    "Decisión 10: Gestión de Riesgos de la IA"
                ]
            }
        ]
        
        # Filtrar las que no se han usado
        for item in all_phases:
            if item["fase"] not in used_phases:
                available_content.append(item)
            else:
                # Si la fase ya se usó, revisar si hay decisiones no usadas dentro de ella
                nuevas_decisiones = []
                for dec in item["decisiones"]:
                    if dec not in used_decisions:
                        nuevas_decisiones.append(dec)
                if nuevas_decisiones:
                    available_content.append({
                        "fase": item["fase"],
                        "decisiones": nuevas_decisiones
                    })
        
        # 🔥 3. Si ya se usaron todas, reiniciar el contador (permitir repetir)
        if not available_content:
            available_content = all_phases
            used_phases = set()
            used_decisions = set()
        
        # 🔥 4. Seleccionar una fase y decisión aleatoriamente de las disponibles
        import random
        selected_fase_data = random.choice(available_content)
        selected_fase = selected_fase_data["fase"]
        selected_decision = random.choice(selected_fase_data["decisiones"])
        
        # 🔥 5. Construir el prompt para DeepSeek
        context_part = ""
        if self.pdf_context:
            context_part = f"""
            --- EXTRACTO DEL DOCUMENTO OFICIAL IA-COOP-LAB ---
            {self.pdf_context}
            --- FIN DEL EXTRACTO ---
            """
        
        system_prompt = f"""
        Eres un experto en la metodología IA-COOP-LAB para el sector cooperativo latinoamericano.
        {context_part}
        
        Tu tarea es generar un TIP práctico y accionable basado EXCLUSIVAMENTE en el documento oficial.
        
        **INSTRUCCIONES OBLIGATORIAS (NO LAS IGNORES):**
        1. El TIP debe enfocarse en una cooperativa de ahorro y crédito, financiera o multiactiva.
        2. El TIP debe abordar únicamente la siguiente fase y decisión:
           - Fase: {selected_fase}
           - Decisión: {selected_decision}
        3. Incluye un ejemplo práctico y concreto de cómo aplicar esta decisión en una cooperativa real.
        4. El TIP debe tener 8-10 líneas (aproximadamente 200-250 palabras).
        5. Usa un tono profesional, práctico y alentador.
        
        **FORMATO DE SALIDA (JSON):**
        {{
            "title": "Título atractivo (máximo 90 caracteres)",
            "tip": "Texto del TIP (8-10 líneas, 200-250 palabras)",
            "area": "Área de aplicación (ej: Crédito, Gestión de Socios, Riesgos)",
            "phase": "{selected_fase} - {selected_decision}"
        }}
        """
        
        user_prompt = f"""
        Genera un TIP para hoy aplicando la Fase '{selected_fase}' y la Decisión '{selected_decision}'.
        El ejemplo debe ser sobre una cooperativa financiera o multiactiva.
        """
        
        result = self._call_deepseek(system_prompt, user_prompt)
        
        if result:
            # 🔥 Asegurar que la fase guardada tenga el formato completo
            result['phase'] = f"{selected_fase} - {selected_decision}"
            return result
        else:
            # 🔥 Fallback de emergencia si DeepSeek falla
            return {
                'title': f'IA-COOP-LAB: Aplicando la {selected_decision}',
                'tip': f'En la fase de {selected_fase}, la decisión {selected_decision} es crucial para el éxito. Por ejemplo, una cooperativa financiera puede aplicar esta decisión para mejorar la inclusión de sus asociados y fortalecer la confianza. Es fundamental documentar cada paso y mantener un enfoque centrado en la persona.',
                'area': 'Gestión Estratégica',
                'phase': f"{selected_fase} - {selected_decision}"
            }
    
    def _call_deepseek(self, system_prompt: str, user_prompt: str) -> Optional[Dict]:
        """Llama a la API de DeepSeek con reintentos optimizados"""
        if not self.api_key:
            return None
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "deepseek-v4-flash",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.8,  # 🔥 Aumentamos temperatura para más creatividad y variedad
            "max_tokens": 3000
        }
        
        for attempt in range(3):  # 🔥 3 intentos para asegurar generación
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return {'summary': content}
                    
            except Exception as e:
                print(f"  ⚠️ Intento {attempt+1} fallido: {e}", flush=True)
                if attempt < 2:
                    time.sleep(3)
        
        return None
    
    def _generate_fallback_summary(self, news_items: List[Dict]) -> str:
        """Genera un resumen basico si DeepSeek falla"""
        summary = "Resumen del sector cooperativo:\n\n"
        for i, item in enumerate(news_items[:6]):
            title = item.get('title', 'Sin titulo')
            source = item.get('source_name', 'Fuente desconocida')
            summary += f"{i+1}. **{title}**\n   Fuente: {source}\n\n"
        
        summary += f"\nTotal de noticias recopiladas: {len(news_items)}"
        return summary


def generate_cooperative_summaries(processed_data: Dict, topic_index=None) -> Dict:
    """Genera resumenes para todos los paises (paralelo)"""
    generator = CooperativeSummaryGenerator(topic_index)
    
    print("\nGenerando resumenes con IA...")
    print("-" * 50)
    
    summaries = {}
    regional_data = {}
    
    def generate_country_summary_safe(code, data):
        try:
            return code, generator.generate_country_summary(data)
        except Exception as e:
            print(f"  Error en {data.get('country', 'Desconocido')}: {e}")
            return code, None
    
    country_tasks = []
    for code, data in processed_data.items():
        if code == 'LATAM':
            continue
        country_tasks.append((code, data))
    
    with ThreadPoolExecutor(max_workers=min(len(country_tasks), 4)) as executor:
        futures = {
            executor.submit(generate_country_summary_safe, code, data): code
            for code, data in country_tasks
        }
        
        for future in as_completed(futures):
            code, summary = future.result()
            if summary:
                summaries[code] = summary
                if summary.get('has_news'):
                    regional_data[code] = summary
            else:
                country_name = next((c.get('name', 'Desconocido') for c in generator.countries if c.get('code') == code), 'Desconocido')
                summaries[code] = {
                    'country': country_name,
                    'has_news': False,
                    'summary': 'No se pudo generar resumen'
                }
    
    # Generar resumen regional
    print("  Latinoamerica (regional)...")
    regional_summary = generator.generate_regional_summary(regional_data)
    summaries['REGIONAL'] = {
        'country': 'Latinoamerica',
        **regional_summary
    }
    
    # 🔥 Generar TIP IA-COOP-LAB (ahora con control de repetición y enfoque financiero)
    print("  Generando TIP IA-COOP-LAB inteligente...")
    coop_tip = generator.generate_coop_tip()
    summaries['COOP_TIP'] = {
        'country': 'IA-COOP-LAB',
        'has_news': True,
        'summary': coop_tip.get('tip', ''),
        'title': coop_tip.get('title', 'TIP del dia'),
        'area': coop_tip.get('area', 'General'),
        'phase': coop_tip.get('phase', 'Comportamiento Inteligente - Decisión 3')
    }
    
    print("Resumenes generados")
    return summaries


if __name__ == '__main__':
    print("=== PRUEBA DE SUMMARY_GENERATOR_COOP ===")
    
    test_file = f"cooperative_news_{datetime.now().strftime('%Y-%m-%d')}.json"
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        from cooperative_processor import process_cooperative_news
        processed = process_cooperative_news(raw_data)
        summaries = generate_cooperative_summaries(processed)
        
        print("\nRESUMENES GENERADOS:")
        for code, summary in summaries.items():
            print(f"\n{'='*50}")
            print(f"{summary.get('country', 'Desconocido')}")
            print(f"{'='*50}")
            text = summary.get('summary', '')
            if len(text) > 300:
                text = text[:300] + "..."
            print(text)
    else:
        print("No hay datos. Ejecuta cooperative_fetcher.py primero.")