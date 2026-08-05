# summary_generator_coop.py
import json
import requests
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

class CooperativeSummaryGenerator:
    """Genera resúmenes de noticias cooperativas usando DeepSeek"""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        self.cache = {}
        
    def _get_country_context(self, country: str) -> str:
        """Obtiene contexto específico del país para el prompt"""
        contexts = {
            'Colombia': """
            El sector cooperativo colombiano está regulado por la Superintendencia de Economía Solidaria.
            Las principales confederaciones son Confecoop (nacional y regional) y Fecolfin para fondos de empleados.
            El sistema incluye cooperativas de ahorro, crédito, multiactivas y de trabajo asociado.
            """,
            'Panamá': """
            El cooperativismo panameño es supervisado por el IPACOOP (Instituto Panameño Autónomo Cooperativo).
            CONACOOP es la confederación nacional que agrupa a las cooperativas.
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
        
        # Preparar texto de noticias
        news_text = ""
        for i, item in enumerate(selected_news[:10]):
            title = item.get('title', 'Sin título')
            source = item.get('source_name', 'Fuente desconocida')
            summary = item.get('summary', '')[:200]
            category = item.get('source_category', 'general')
            date = item.get('published')
            date_str = date.strftime('%d/%m/%Y') if date else 'Fecha desconocida'
            
            news_text += f"{i+1}. 📌 Título: {title}\n"
            news_text += f"   📰 Fuente: {source}\n"
            news_text += f"   📂 Categoría: {category}\n"
            news_text += f"   📅 Fecha: {date_str}\n"
            news_text += f"   📝 Resumen: {summary}\n\n"
        
        # Construir prompts
        country_context = self._get_country_context(country_name)
        
        system_prompt = f"""
        Eres un periodista especializado en el sector cooperativo de {country_name} y Latinoamérica.
        
        CONTEXTO DEL SECTOR:
        {country_context}
        
        Tu tarea es generar un resumen completo y profesional de las noticias cooperativas del día.
        
        INSTRUCCIONES OBLIGATORIAS:
        1. El resumen debe tener entre 4-5 párrafos (mínimo 400 palabras)
        2. Menciona TODAS las noticias importantes con sus fuentes
        3. Incluye contexto sobre el sector cooperativo en el país
        4. Menciona las entidades oficiales (Superintendencias, Confederaciones, etc.)
        5. Destaca eventos, regulaciones, innovaciones y logros del sector
        6. Usa un tono profesional pero accesible para el público general
        7. Al final, menciona el número total de noticias recopiladas
        
        FORMATO DE SALIDA (JSON):
        {{
            "summary": "Resumen completo en español...",
            "key_topics": ["tema1", "tema2", "tema3", "tema4"],
            "main_sources": ["fuente1", "fuente2"],
            "news_count": Número de noticias,
            "has_important_news": true/false
        }}
        """
        
        user_prompt = f"""
        Estas son las noticias cooperativas de {country_name} para hoy:
        
        {news_text}
        
        Genera un resumen completo que cubra las noticias más relevantes del sector cooperativo.
        Asegúrate de mantener la precisión de la información y citar las fuentes.
        """
        
        # Llamar a DeepSeek
        result = self._call_deepseek(system_prompt, user_prompt)
        
        if result:
            return {
                'country': country_name,
                'has_news': True,
                'news_items': selected_news[:10],
                **result
            }
        else:
            return {
                'country': country_name,
                'summary': self._generate_fallback_summary(selected_news),
                'has_news': True,
                'news_items': selected_news[:10],
                'key_topics': ['Sector cooperativo'],
                'main_sources': ['Fuentes diversas'],
                'news_count': len(selected_news),
                'has_important_news': True
            }
    
    def generate_regional_summary(self, all_countries: Dict) -> Dict:
        """Genera un resumen regional de todas las noticias"""
        summaries = []
        for code, data in all_countries.items():
            if data.get('has_news') and data.get('summary'):
                country = data.get('country', 'Desconocido')
                summary = data.get('summary', '')[:300]
                summaries.append(f"**{country}**: {summary}...")
        
        if not summaries:
            return {
                'summary': "No se encontraron noticias cooperativas relevantes en la región para este día.",
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
        4. Señala oportunidades y desafíos compartidos
        5. El resumen debe tener 3-4 párrafos (mínimo 300 palabras)
        
        FORMATO DE SALIDA (JSON):
        {
            "summary": "Resumen regional...",
            "trends": ["tendencia1", "tendencia2"],
            "countries_covered": ["país1", "país2"]
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
                'summary': regional_text[:500],
                'has_news': True,
                'trends': ['Cooperativismo en Latinoamérica'],
                'countries_covered': list(all_countries.keys())
            }
    
    def _call_deepseek(self, system_prompt: str, user_prompt: str) -> Optional[Dict]:
        """Llama a la API de DeepSeek con reintentos"""
        if not self.api_key:
            print("❌ DEEPSEEK_API_KEY no configurada")
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
            "max_tokens": 4000
        }
        
        for attempt in range(3):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Extraer JSON
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return {'summary': content}
                    
            except requests.exceptions.Timeout:
                print(f"  ⚠️ Timeout en intento {attempt+1}")
            except requests.exceptions.RequestException as e:
                print(f"  ⚠️ Error en intento {attempt+1}: {e}")
            except json.JSONDecodeError as e:
                print(f"  ⚠️ Error parseando JSON en intento {attempt+1}: {e}")
            
            if attempt < 2:
                import time
                time.sleep(5)
        
        return None
    
    def _generate_fallback_summary(self, news_items: List[Dict]) -> str:
        """Genera un resumen básico si DeepSeek falla"""
        summary = "📊 **Resumen del sector cooperativo:**\n\n"
        for i, item in enumerate(news_items[:7]):
            title = item.get('title', 'Sin título')
            source = item.get('source_name', 'Fuente desconocida')
            summary += f"{i+1}. **{title}**\n   📌 Fuente: {source}\n\n"
        
        summary += f"\n📈 Total de noticias recopiladas: {len(news_items)}"
        return summary


def generate_cooperative_summaries(processed_data: Dict) -> Dict:
    """Genera resúmenes para todos los países"""
    generator = CooperativeSummaryGenerator()
    
    print("\n🧠 Generando resúmenes con IA...")
    print("-" * 50)
    
    summaries = {}
    regional_data = {}
    
    for code, data in processed_data.items():
        if code == 'LATAM':
            continue
        
        country = data.get('country', 'Desconocido')
        print(f"  📝 {country}...")
        
        summary = generator.generate_country_summary(data)
        summaries[code] = summary
        
        if summary.get('has_news'):
            regional_data[code] = summary
        
        import time
        time.sleep(1)
    
    # Generar resumen regional
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
            print(f"\n📊 Noticias: {summary.get('news_count', 'N/A')}")
    else:
        print("⚠️ No hay datos. Ejecuta cooperative_fetcher.py primero.")