"""
OnzeNews — Configuração do Admin Panel
Este arquivo permite integrar o admin panel com o gerar_jornal.py
"""

import os
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "admin", "onzenews.db")

def get_admin_config():
    """Busca as configurações do admin para usar no gerar_jornal.py"""
    if not os.path.exists(DB_PATH):
        return get_default_config()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Buscar configurações
    cursor.execute("SELECT * FROM schedule_config")
    configs = {row['config_key']: row['config_value'] for row in cursor.fetchall()}

    # Buscar horários ativos
    cursor.execute("SELECT * FROM update_times WHERE is_active = 1 ORDER BY update_time")
    times = [row['update_time'] for row in cursor.fetchall()]

    # Buscar fontes ativas
    cursor.execute("SELECT * FROM news_sources WHERE is_active = 1 ORDER BY priority")
    sources = [{
        "name": row['name'],
        "url": row['url'],
        "category": row['category']
    } for row in cursor.fetchall()]

    conn.close()

    return {
        "schedule": configs,
        "update_times": times,
        "sources": sources
    }

def get_default_config():
    """Retorna configurações padrão caso o banco não exista"""
    return {
        "schedule": {
            "daily_enabled": "true",
            "daily_time": "08:00",
            "update_days": "1,2,3,4,5",
            "max_updates_per_day": "3",
            "podcast_enabled": "true",
            "pdf_generation": "true",
            "breaking_news_enabled": "true"
        },
        "update_times": ["08:00", "12:00", "18:00"],
        "sources": [
            {"name": "UOL Economia", "url": "https://economia.uol.com.br/", "category": "economia"},
            {"name": "G1 Economia", "url": "https://g1.globo.com/economia/", "category": "economia"},
            {"name": "Valor Econômico", "url": "https://valor.globo.com/", "category": "economia"},
            {"name": "InfoMoney", "url": "https://www.infomoney.com.br/", "category": "economia"}
        ]
    }

def should_generate_now():
    """Verifica se deve gerar o newsletter agora baseado no agendamento"""
    config = get_admin_config()
    schedule = config['schedule']

    # Verificar se está habilitado
    if schedule.get('daily_enabled') != 'true':
        return False

    # Verificar dia da semana
    today = datetime.now().weekday() + 1  # 1=Segunda, 7=Domingo
    allowed_days = [int(d) for d in schedule.get('update_days', '1,2,3,4,5').split(',')]

    if today not in allowed_days:
        return False

    # Verificar horário
    current_time = datetime.now().strftime("%H:%M")
    allowed_times = config.get('update_times', [])

    if current_time in allowed_times:
        return True

    return False

def log_generation(status, message, duration=None):
    """Registra uma geração no log"""
    if not os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO generation_logs (generation_type, status, message, duration_seconds) VALUES (?, ?, ?, ?)",
        ("automatic", status, message, duration)
    )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Testar configurações
    config = get_admin_config()
    print("Configurações atuais:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    print("\nDeve gerar agora?", should_generate_now())
