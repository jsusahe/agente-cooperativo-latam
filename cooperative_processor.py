# cooperative_processor.py - VERSION SIMPLIFICADA CON RESPALDO
import json
import os
import re
import sys
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict
import time as time_module
from topic_index import TopicIndex, get_topic_index

# 🔥 Configurar flush de salida
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


class CooperativeProcessor:
    """Procesa y clasifica noticias cooperativas por país y categoría"""
    
    def __init__(self, config_file="config_countries.json", topic_index=None):
        print(f"🔍 CooperativeProcessor.__init__()", flush=True)
        self.config = self._load_config(config_file)
        self.settings = self.config.get("settings", {})
        self.min_news = self.settings.get("min_news_per_country", 2)
        self.topic_index = topic_index if topic_index else get_topic_index()
        print(f"  ✅ min_news_per_country: {self.min_news}", flush=True)
        
    def _load_config(self, config_file: str) -> Dict:
        # ... (código existente) ...
        pass
    
    def _normalize_date(self, date_value) -> datetime:
        # ... (código existente) ...
        pass
    
    def classify_by_category(self, article: Dict) -> str:
        # ... (código existente) ...
        pass
    
    def classify_by_source_type(self, article: Dict) -> str:
        # ... (código existente) ...
        pass
    
    def process_country_news(self, country_data: Dict) -> Dict:
        """Procesa y estructura las noticias de un país, usando respaldo si es necesario"""
        country_name = country_data.get('country', 'Desconocido')
        country_code = country_data.get('code', 'XX')
        
        print(f"  📊 Procesando {country_name} ({country_code})...", flush=True)
        
        if not country_data:
            print(f"  ⚠️ country_data vacío para {country_name}", flush=True)
            return self._empty_result(country_name, country_code)
        
        articles = country_data.get('articles', [])
        print(f"  📊 {country_name}: {len(articles)} artículos", flush=True)
        
        # 🔥 SI NO HAY ARTÍCULOS, USAR RESPALDO DEL ÍNDICE
        if not articles:
            print(f"  ⚠️ {country_name}: sin artículos. Buscando en índice...", flush=True)
            backup_news = self.topic_index.get_recent_news(country_code, self.min_news)
            if backup_news:
                print(f"  ✅ {country_name}: {len(backup_news)} noticias recuperadas del histórico", flush=True)
                articles = backup_news
        
        if not articles:
            print(f"  ⚠️ {country_name}: no hay contenido de respaldo", flush=True)
            return self._empty_result(country_name, country_code)
        
        # 🔥 Procesar cada artículo
        print(f"  🔍 Procesando {len(articles)} artículos...", flush=True)
        for idx, article in enumerate(articles):
            try:
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
                print(f"    ❌ Error en artículo {idx+1}: {e}", flush=True)
                continue
        
        # 🔥 SELECCIÓN SIMPLIFICADA
        print(f"  🔍 Seleccionando noticias...", flush=True)
        selected = articles[:self.min_news]
        
        # Si hay menos noticias que el mínimo, duplicar las que hay
        while len(selected) < self.min_news and selected:
            selected.append(selected[0])
        
        print(f"  ✅ {country_name}: {len(selected)} noticias seleccionadas", flush=True)
        
        return {
            'country': country_name,
            'code': country_code,
            'total_articles': len(articles),
            'grouped': {},  # Simplificado
            'selected_news': selected,
            'summary_ready': len(selected) >= self.min_news
        }
    
    def _empty_result(self, country_name: str, country_code: str) -> Dict:
        # ... (código existente) ...
        pass
    
    def get_all_countries_data(self, raw_data: Dict) -> Dict:
        # ... (código existente) ...
        # Se debe pasar el topic_index al procesar cada país
        pass


def process_cooperative_news(raw_data: Dict) -> Dict:
    """Procesa las noticias crudas"""
    print("🔍 Iniciando process_cooperative_news...", flush=True)
    
    if not raw_data:
        print("⚠️ raw_data está vacío", flush=True)
        return {}
    
    print(f"📊 raw_data tiene {len(raw_data)} países", flush=True)
    
    for code, data in raw_data.items():
        country = data.get('country', 'Desconocido')
        articles = len(data.get('articles', []))
        print(f"  📊 {code} ({country}): {articles} artículos", flush=True)
    
    processor = CooperativeProcessor(topic_index=get_topic_index())
    result = processor.get_all_countries_data(raw_data)
    
    print(f"✅ Procesamiento completado: {len(result)} países", flush=True)
    return result