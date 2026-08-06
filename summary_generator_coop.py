# summary_generator_coop.py - VERSIÓN OPTIMIZADA CON PARALELISMO
import json
import requests
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


class CooperativeSummaryGenerator:
    """Genera resúmenes de noticias cooperativas usando DeepSeek"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        
    def _get_country_context(self, country: str) -> str:
        contexts = {
            'Colombia': """
            El sector cooperativo colombiano está regulado por la Superintendencia de Economía Solidaria.
            Las principales confederaciones son Confecoop (nacional y regional) y Fecolfin para fondos de empleados.
            El sistema incluye cooperativas de ahorro, crédito, multiactivas y de trabajo asociado.
            """,
            'Panamá': """
            El cooperativismo panameño es supervisado por el IPACOOP (Instituto Panameño Autónomo Cooperativo).
            CONACOOP es la confederación nacional que agrupa a las cooperativas.
            """,
            'Costa Rica': """
            El sector cooperativo costarricense es supervisado por SUGEF e INFOCOOP.
            Las principales federaciones son FECOOPSE y FEDEAC para cooperativas de ahorro y crédito.
            Las asociaciones solidaristas son una figura importante en el sector.
            """,
            'República Dominicana': """
            El cooperativismo dominicano es supervisado por la Superintendencia de Bancos.
            IDECOOP es el instituto de desarrollo y crédito cooperativo.
            """
        }
        return contexts.get(country, "")
    
    def generate_country_summary(self, country_data: Dict) -> Dict:
        """Genera resumen para un país específico"""
        country_name = country_data.get('country', 'Desconocido')
        selected_news = country_data.get('selected_news', [])
        
        if not selected_news:
            return {
                'country': country_name,
                'summary': f"No se encontraron noticias cooperativas para {country_name} en los últimos días.",
                'has_news': False
            }
        
        news_text = ""
        for i, item in enumerate(selected_news[:8]):
            title = item.get('title', 'Sin título')
            source = item.get('source_name', 'Fuente desconocida')
            summary = item.get('summary', '')[:200]
            category = item.get('source_category', 'general')
            
            news_text += f"{i+1}. 📌 Título: {title}\n"
            news_text += f"   📰 Fuente: {source}\n"
            news_text += f"   📂 Categoría: {category}\n"
            news_text += f"   📝 Resumen: {summary}\n\n"
        
        country_context = self._get_country_context(country_name)
        
        system_prompt = f"""
        Eres un periodista especializado en el sector cooperativo de {country_name} y Latinoamérica.
        
        CONTEXTO DEL SECTOR:
        {country_context}
        
        Tu tarea es generar un resumen completo y profesional de las noticias cooperativas del día.
        
        INSTRUCCIONES OBLIGATORIAS:
        1. El resumen debe tener entre 3-4 párrafos (mínimo 250 palabras)
        2. Menciona TODAS las noticias importantes con sus fuentes
        3. Incluye contexto sobre el sector cooperativo en el país
        4. Menciona las entidades oficiales
        5. Destaca eventos, regulaciones, innovaciones y logros del sector
        6. Usa un tono profesional pero accesible
        
        FORMATO DE SALIDA (JSON):
        {{
            "summary": "Resumen completo en español...",
            "key_topics": ["tema1", "tema2", "tema3"],
            "main_sources": ["fuente1", "fuente2"],
            "news_count": Número de noticias
        }}
        """
        
        user_prompt = f"""
        Estas son las noticias cooperativas de {country_name} para hoy:
        
        {news_text}
        
        Genera un resumen completo que cubra las noticias más relevantes del sector cooperativo.
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
                'summary': "No se encontraron noticias cooperativas relevantes en la región.",
                'has_news': False
            }
        
        regional_text = "\n\n".join(summaries)
        
        system_prompt = """
        Eres un experto en el sector cooperativo latinoamericano.
        Genera un resumen regional que integre las noticias cooperativas de varios países.
        
        INSTRUCCIONES:
        1. Identifica tendencias comunes en la región
        2. Destaca diferencias importantes entre países
        3. Menciona el panorama general del cooperativismo en Latinoamérica
        4. El resumen debe tener 2-3 párrafos (mínimo 200 palabras)
        
        FORMATO DE SALIDA (JSON):
        {
            "summary": "Resumen regional...",
            "trends": ["tendencia1", "tendencia2"]
        }
        """
        
        user_prompt = f"""
        Resúmenes de noticias cooperativas por país:
        
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
                'trends': ['Cooperativismo en Latinoamérica']
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
        """Genera un resumen básico si DeepSeek falla"""
        summary = "📊 **Resumen del sector cooperativo:**\n\n"
        for i, item in enumerate(news_items[:6]):
            title = item.get('title', 'Sin título')
            source = item.get('source_name', 'Fuente desconocida')
            summary += f"{i+1}. **{title}**\n   📌 Fuente: {source}\n\n"
        
        summary += f"\n📈 Total de noticias recopiladas: {len(news_items)}"
        return summary


def generate_cooperative_summaries(processed_data: Dict) -> Dict:
    """Genera resúmenes para todos los países (paralelo)"""
    generator = CooperativeSummaryGenerator()
    
    print("\n🧠 Generando resúmenes con IA...")
    print("-" * 50)
    
    summaries = {}
    regional_data = {}
    
    def generate_country_summary_safe(code, data):
        try:
            return code, generator.generate_country_summary(data)
        except Exception as e:
            print(f"  ⚠️ Error en {data.get('country', 'Desconocido')}: {e}")
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
    
    print(f"  🌎 Latinoamérica (regional)...")
    regional_summary = generator.generate_regional_summary(regional_data)
    summaries['REGIONAL'] = {
        'country': 'Latinoamérica',
        **regional_summary
    }
    
    print("✅ Resúmenes generados")
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
        
        print("\n📄 RESUMENES GENERADOS:")
        for code, summary in summaries.items():
            print(f"\n{'='*50}")
            print(f"📄 {summary.get('country', 'Desconocido')}")
            print(f"{'='*50}")
            text = summary.get('summary', '')
            if len(text) > 300:
                text = text[:300] + "..."
            print(text)
    else:
        print("⚠️ No hay datos. Ejecuta cooperative_fetcher.py primero.")