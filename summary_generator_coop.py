# summary_generator_coop.py - VERSIÓN ACTUALIZADA CON IA-COOP-LAB
import json
import requests
import os
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


class CooperativeSummaryGenerator:
    """Genera resúmenes de noticias cooperativas usando DeepSeek"""
    
    def __init__(self, topic_index=None):
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        self.topic_index = topic_index
        
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
    
    def _get_ia_coop_lab_prompt(self) -> str:
        """Obtiene el prompt para generar TIPS IA-COOP-LAB"""
        return """
        Eres un experto en la metodologia IA-COOP-LAB, que combina Inteligencia Artificial 
        con el sector cooperativo para generar soluciones innovadoras.
        
        La metodologia IA-COOP-LAB se basa en:
        1. IDENTIFICAR: Detectar oportunidades de mejora en procesos cooperativos
        2. ANALIZAR: Evaluar datos y patrones del sector
        3. CREAR: Disenar soluciones con IA adaptadas al cooperativismo
        4. OPTIMIZAR: Mejorar procesos continuamente
        5. LABORAR: Implementar y compartir conocimiento
        
        Genera un TIP diario de 8-10 lineas que explique como aplicar esta metodologia
        a una situacion concreta de una cooperativa.
        
        El TIP debe ser practico, accionable y especifico para el sector cooperativo.
        """
    
    def generate_country_summary(self, country_data: Dict) -> Dict:
        """Genera resumen para un país específico"""
        country_name = country_data.get('country', 'Desconocido')
        selected_news = country_data.get('selected_news', [])
        
        if not selected_news:
            return {
                'country': country_name,
                'summary': f"No se encontraron noticias cooperativas para {country_name} en los ultimos dias.",
                'has_news': False
            }
        
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
                'summary': self._generate_fallback_summary(selected_news),
                'has_news': True,
                'news_items': selected_news[:8],
                'key_topics': ['Sector cooperativo'],
                'main_sources': ['Fuentes diversas'],
                'news_count': len(selected_news)
            }
    
    def generate_regional_summary(self, all_countries: Dict) -> Dict:
        """Genera un resumen regional de todas las noticias"""
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
        
        INSTRUCCIONES:
        1. Identifica tendencias comunes en la region
        2. Destaca diferencias importantes entre paises
        3. Menciona el panorama general del cooperativismo en Latinoamerica
        4. El resumen debe tener 2-3 parrafos (minimo 200 palabras)
        
        FORMATO DE SALIDA (JSON):
        {
            "summary": "Resumen regional...",
            "trends": ["tendencia1", "tendencia2"]
        }
        """
        
        user_prompt = f"""
        Resumenes de noticias cooperativas por pais:
        
        {regional_text}
        
        Genera un resumen regional que integre estas noticias.
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
        """Genera un TIP diario de IA-COOP-LAB"""
        system_prompt = """
        Eres un experto en la metodologia IA-COOP-LAB, que combina Inteligencia Artificial 
        con el sector cooperativo para generar soluciones innovadoras.
        
        La metodologia IA-COOP-LAB se basa en:
        1. IDENTIFICAR: Detectar oportunidades de mejora en procesos cooperativos
        2. ANALIZAR: Evaluar datos y patrones del sector
        3. CREAR: Disenar soluciones con IA adaptadas al cooperativismo
        4. OPTIMIZAR: Mejorar procesos continuamente
        5. LABORAR: Implementar y compartir conocimiento
        
        Genera un TIP diario de 8-10 lineas que explique como aplicar esta metodologia
        a una situacion concreta de una cooperativa.
        
        El TIP debe ser practico, accionable y especifico para el sector cooperativo.
        Ejemplo de areas: gestion de socios, credito, ahorro, toma de decisiones, 
        analisis de riesgos, comunicacion, educacion financiera.
        
        FORMATO DE SALIDA (JSON):
        {
            "title": "Titulo del TIP (maximo 100 caracteres)",
            "tip": "Texto del TIP (8-10 lineas, 200-300 palabras)",
            "area": "Area de aplicacion",
            "phase": "Fase de IA-COOP-LAB (IDENTIFICAR/ANALIZAR/CREAR/OPTIMIZAR/LABORAR)"
        }
        """
        
        user_prompt = """
        Genera un TIP diario para cooperativas usando la metodologia IA-COOP-LAB.
        """
        
        result = self._call_deepseek(system_prompt, user_prompt)
        
        if result:
            return result
        else:
            return {
                'title': 'IA-COOP-LAB: Transformacion Digital Cooperativa',
                'tip': 'La metodologia IA-COOP-LAB propone usar IA para analizar el comportamiento de los socios y anticipar sus necesidades financieras. Mediante el analisis de datos historicos, las cooperativas pueden ofrecer productos personalizados y mejorar la experiencia del socio, fortaleciendo el vinculo cooperativo.',
                'area': 'Gestion de Socios',
                'phase': 'ANALIZAR'
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
            "temperature": 0.7,
            "max_tokens": 3000
        }
        
        for attempt in range(2):
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
                    
            except Exception:
                if attempt < 1:
                    time.sleep(2)
        
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
    
    # Generar TIP IA-COOP-LAB
    print("  Generando TIP IA-COOP-LAB...")
    coop_tip = generator.generate_coop_tip()
    summaries['COOP_TIP'] = {
        'country': 'IA-COOP-LAB',
        'has_news': True,
        'summary': coop_tip.get('tip', ''),
        'title': coop_tip.get('title', 'TIP del dia'),
        'area': coop_tip.get('area', 'General'),
        'phase': coop_tip.get('phase', 'LABORAR')
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