# cooperative_processor.py - CON LOGS EXTENSIVOS
import json
import os
import re
import sys
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
import time as time_module

# 🔥 Configurar flush de salida
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


class CooperativeProcessor:
    """Procesa y clasifica noticias cooperativas por país y categoría"""
    
    def __init__(self, config_file="config_countries.json"):
        print(f"🔍 CooperativeProcessor.__init__()", flush=True)
        self.config = self._load_config(config_file)
        self.settings = self.config.get("settings", {})
        self.min_news = self.settings.get("min_news_per_country", 2)
        print(f"  ✅ min_news_per_country: {self.min_news}", flush=True)
        
    def _load_config(self, config_file: str) -> Dict:
        print(f"🔍 Cargando config: {config_file}", flush=True)
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error al cargar configuración: {e}", flush=True)
            return {"countries": []}
    
    def _normalize_date(self, date_value) -> datetime:
        """Convierte cualquier formato de fecha a datetime.datetime"""
        if date_value is None:
            return datetime.now()
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, time_module.struct_time):
            try:
                return datetime(*date_value[:6])
            except Exception:
                return datetime.now()
        
        if isinstance(date_value, str):
            try:
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%B %d, %Y']:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except:
                        continue
            except:
                pass
        
        return datetime.now()
    
    def classify_by_category(self, article: Dict) -> str:
        """Clasifica la noticia por categoría temática"""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        text = title + ' ' + summary
        
        categories = {
            'financiero': ['finanzas', 'ahorro', 'crédito', 'préstamo', 'tasa', 'capital', 'inversión', 'rentabilidad'],
            'regulación': ['supervisión', 'regulación', 'normativa', 'ley', 'decreto', 'control', 'superintendencia', 'circular'],
            'eventos': ['congreso', 'seminario', 'taller', 'capacitación', 'evento', 'reunión', 'asamblea', 'conferencia'],
            'innovación': ['digital', 'tecnología', 'innovación', 'app', 'plataforma', 'transformación', 'modernización'],
            'social': ['comunidad', 'desarrollo', 'solidaridad', 'inclusión', 'responsabilidad', 'social'],
            'educación': ['educación', 'formación', 'curso', 'capacitación', 'conocimiento', 'aprendizaje'],
            'gestión': ['gestión', 'administración', 'gobierno', 'directiva', 'consejo', 'presidente']
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        return 'general'
    
    def classify_by_source_type(self, article: Dict) -> str:
        """Clasifica por tipo de fuente"""
        category = article.get('category', '')
        source_name = article.get('source_name', '').lower()
        
        if 'supervision' in category:
            return 'supervision'
        elif 'national_associations' in category or 'confecoop' in source_name or 'federacion' in source_name:
            return 'national_association'
        elif 'regional_associations' in category:
            return 'regional_association'
        elif 'employee_funds' in category or 'analfe' in source_name:
            return 'employee_fund'
        elif 'solidarist_associations' in category or 'solidarismo' in source_name:
            return 'solidarist'
        elif 'media' in category or 'cooperador' in source_name:
            return 'media'
        elif 'cooperatives' in category:
            return 'cooperative'
        elif 'youtube' in category:
            return 'video'
        elif 'insurance_guarantee' in category:
            return 'guarantee'
        elif 'government' in category:
            return 'government'
        else:
            return 'other'
    
    def process_country_news(self, country_data: Dict) -> Dict:
        """Procesa y estructura las noticias de un país"""
        country_name = country_data.get('country', 'Desconocido')
        country_code = country_data.get('code', 'XX')
        
        print(f"  📊 Procesando {country_name} ({country_code})...", flush=True)
        
        if not country_data:
            print(f"  ⚠️ country_data vacío para {country_name}", flush=True)
            return {
                'country': country_name,
                'code': country_code,
                'total_articles': 0,
                'grouped': {},
                'selected_news': [],
                'summary_ready': False
            }
        
        articles = country_data.get('articles', [])
        print(f"  📊 {country_name}: {len(articles)} artículos", flush=True)
        
        # Si no hay artículos, retornar datos vacíos
        if not articles:
            print(f"  ⚠️ {country_name}: sin artículos", flush=True)
            return {
                'country': country_name,
                'code': country_code,
                'total_articles': 0,
                'grouped': {},
                'selected_news': [],
                'summary_ready': False
            }
        
        # Procesar cada artículo
        print(f"  🔍 Procesando {len(articles)} artículos para {country_name}...", flush=True)
        for idx, article in enumerate(articles):
            try:
                if idx % 5 == 0:
                    print(f"    📝 Procesando artículo {idx+1}/{len(articles)}", flush=True)
                article['category_theme'] = self.classify_by_category(article)
                article['source_category'] = self.classify_by_source_type(article)
                
                if article.get('summary'):
                    article['summary'] = re.sub(r'<[^>]+>', '', article['summary'])
                    article['summary'] = article['summary'][:400]
                
                if article.get('published'):
                    article['published'] = self._normalize_date(article['published'])
                else:
                    article['published'] = datetime.now()
            except Exception as e:
                print(f"    ❌ Error procesando artículo {idx+1}: {e}", flush=True)
                continue
        
        # Agrupar por categoría
        print(f"  🔍 Agrupando por categoría para {country_name}...", flush=True)
        grouped = defaultdict(list)
        for article in articles:
            source_cat = article.get('source_category', 'other')
            grouped[source_cat].append(article)
        
        # Seleccionar noticias para el resumen
        print(f"  🔍 Seleccionando noticias para {country_name}...", flush=True)
        selected = self.select_news_for_summary(articles, grouped)
        print(f"  ✅ {country_name}: {len(selected)} noticias seleccionadas", flush=True)
        
        return {
            'country': country_name,
            'code': country_code,
            'total_articles': len(articles),
            'grouped': dict(grouped),
            'selected_news': selected,
            'summary_ready': len(selected) >= self.min_news
        }
    
    def select_news_for_summary(self, articles: List[Dict], grouped: Dict) -> List[Dict]:
        """Selecciona las noticias más relevantes para el resumen"""
        if not articles:
            return []
        
        selected = []
        
        def safe_sort_key(item):
            published = item.get('published')
            if published is None:
                return datetime(1970, 1, 1)
            if isinstance(published, time_module.struct_time):
                try:
                    return datetime(*published[:6])
                except:
                    return datetime(1970, 1, 1)
            return published
        
        priority_order = [
            'supervision', 'national_association', 'government',
            'employee_fund', 'regional_association',
            'solidarist', 'cooperative', 'media', 'other'
        ]
        
        for category in priority_order:
            if category in grouped and grouped[category]:
                sorted_news = sorted(
                    grouped[category], 
                    key=safe_sort_key, 
                    reverse=True
                )
                if sorted_news:
                    selected.append(sorted_news[0])
                    grouped[category] = grouped[category][1:]
        
        # Llenar el resto
        remaining_slots = self.min_news - len(selected)
        if remaining_slots > 0:
            all_remaining = []
            for category, items in grouped.items():
                all_remaining.extend(items)
            
            all_remaining.sort(key=safe_sort_key, reverse=True)
            selected.extend(all_remaining[:remaining_slots])
        
        # Asegurar mínimo de noticias (usando artículos existentes)
        while len(selected) < self.min_news and articles:
            for article in articles:
                if article not in selected:
                    selected.append(article)
                    if len(selected) >= self.min_news:
                        break
        
        return selected[:self.min_news * 2]
    
    def get_all_countries_data(self, raw_data: Dict) -> Dict:
        """Procesa todos los países"""
        print(f"🔍 get_all_countries_data: {len(raw_data) if raw_data else 0} países", flush=True)
        processed = {}
        
        if not raw_data:
            print("⚠️ raw_data vacío", flush=True)
            return processed
        
        # 🔥 Procesar país por país con logs
        for code, data in raw_data.items():
            print(f"\n🔍 Procesando código: {code}", flush=True)
            try:
                if code == 'LATAM':
                    articles = data.get('articles', [])
                    print(f"  📊 LATAM: {len(articles)} artículos", flush=True)
                    processed[code] = {
                        'country': 'Latinoamérica',
                        'code': 'LATAM',
                        'total_articles': len(articles),
                        'selected_news': articles[:3],
                        'summary_ready': True
                    }
                else:
                    print(f"  🔍 Procesando país: {code}", flush=True)
                    processed[code] = self.process_country_news(data)
                    print(f"  ✅ País {code} procesado", flush=True)
            except Exception as e:
                print(f"❌ Error procesando {code}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                processed[code] = {
                    'country': code,
                    'code': code,
                    'total_articles': 0,
                    'grouped': {},
                    'selected_news': [],
                    'summary_ready': False
                }
        
        print(f"✅ Procesamiento completado: {len(processed)} países", flush=True)
        return processed


def process_cooperative_news(raw_data: Dict) -> Dict:
    """Procesa las noticias crudas"""
    print("🔍 Iniciando process_cooperative_news...", flush=True)
    
    if not raw_data:
        print("⚠️ raw_data está vacío", flush=True)
        return {}
    
    print(f"📊 raw_data tiene {len(raw_data)} países", flush=True)
    
    # 🔥 Mostrar qué países están en raw_data
    for code, data in raw_data.items():
        country = data.get('country', 'Desconocido')
        articles = len(data.get('articles', []))
        print(f"  📊 {code} ({country}): {articles} artículos", flush=True)
    
    processor = CooperativeProcessor()
    result = processor.get_all_countries_data(raw_data)
    
    print(f"✅ Procesamiento completado: {len(result)} países", flush=True)
    return result


if __name__ == '__main__':
    print("=== PRUEBA DE COOPERATIVE_PROCESSOR ===")
    
    test_file = f"cooperative_news_{datetime.now().strftime('%Y-%m-%d')}.json"
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        processed = process_cooperative_news(raw_data)
        
        print("\n📊 RESULTADOS PROCESADOS:")
        for code, data in processed.items():
            if code == 'LATAM':
                continue
            print(f"\n{'='*50}")
            print(f"🇨🇴 {data.get('country', 'Desconocido')}")
            print(f"{'='*50}")
            print(f"Total noticias: {data.get('total_articles', 0)}")
            print(f"Listas para resumen: {len(data.get('selected_news', []))}")
            print(f"Resumen disponible: {'✅ Sí' if data.get('summary_ready') else '⚠️ No'}")
    else:
        print("⚠️ No hay datos de prueba.")