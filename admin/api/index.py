"""
OnzeNews Admin — Vercel Serverless Function
Importa o Flask app do app.py principal
"""

import os
import sys

# Adicionar o diretório pai ao path para importar app.py
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

# Importar o app do app.py principal
from app import app

# ─── Vercel Handler ──────────────────────────────────────────────────────────
# This is what Vercel calls
def handler(request, response):
    return app(request.environ, response.start)
