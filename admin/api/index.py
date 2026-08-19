"""
OnzeNews Admin — Vercel Serverless Function
Adapta o Flask app para rodar no Vercel
"""

import os
import sys
import json
import sqlite3
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash

# ─── Configuração ────────────────────────────────────────────────────────────
# No Vercel, o diretório base é /tmp para escrita
BASE_DIR = "/tmp" if os.path.exists("/tmp") else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "onzenews.db")

# Caminho para templates e static (fora do /tmp)
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(PROJECT_DIR, "templates")
STATIC_DIR = os.path.join(PROJECT_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(BASE_DIR, "flask_session")

# ─── Database Setup ──────────────────────────────────────────────────────────
def get_db():
    """Conecta ao SQLite e retorna a conexão."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Inicializa o banco de dados com todas as tabelas necessárias."""
    conn = get_db()
    cursor = conn.cursor()

    # Tabela de usuários admin
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    # Tabela de logs de acesso
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES admin_users(id)
        )
    ''')

    # Tabela de configuração de agendamento
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de horários de atualização
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS update_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            update_time TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de fontes de informação
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            category TEXT DEFAULT 'economia',
            is_active INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de logs de geração
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            files_generated TEXT,
            duration_seconds REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de notícias extraordinárias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS breaking_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            priority TEXT DEFAULT 'alta',
            status TEXT DEFAULT 'pendente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP
        )
    ''')

    # Inserir usuário admin padrão se não existir
    cursor.execute("SELECT COUNT(*) FROM admin_users")
    if cursor.fetchone()[0] == 0:
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
            ("admin", password_hash)
        )

    # Inserir configurações padrão
    default_configs = [
        ("daily_enabled", "true"),
        ("daily_time", "08:00"),
        ("update_days", "1,2,3,4,5"),
        ("max_updates_per_day", "3"),
        ("breaking_news_enabled", "true"),
        ("podcast_enabled", "true"),
        ("pdf_generation", "true"),
    ]

    for key, value in default_configs:
        cursor.execute(
            "INSERT OR IGNORE INTO schedule_config (config_key, config_value) VALUES (?, ?)",
            (key, value)
        )

    # Inserir horários padrão
    cursor.execute("SELECT COUNT(*) FROM update_times")
    if cursor.fetchone()[0] == 0:
        default_times = ["08:00", "12:00", "18:00"]
        for time_val in default_times:
            cursor.execute(
                "INSERT INTO update_times (update_time, is_active) VALUES (?, ?)",
                (time_val, 1)
            )

    # Inserir fontes padrão
    cursor.execute("SELECT COUNT(*) FROM news_sources")
    if cursor.fetchone()[0] == 0:
        default_sources = [
            ("UOL Economia", "https://economia.uol.com.br/", "economia", 1, 1),
            ("G1 Economia", "https://g1.globo.com/economia/", "economia", 1, 2),
            ("Valor Econômico", "https://valor.globo.com/", "economia", 1, 3),
            ("InfoMoney", "https://www.infomoney.com.br/", "economia", 1, 4),
        ]
        for name, url, category, is_active, priority in default_sources:
            cursor.execute(
                "INSERT INTO news_sources (name, url, category, is_active, priority) VALUES (?, ?, ?, ?, ?)",
                (name, url, category, is_active, priority)
            )

    conn.commit()
    conn.close()

# ─── Auth Decorator ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def log_action(action, details=None):
    """Registra uma ação no log."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO access_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
            (session.get('user_id'), action, details, request.remote_addr)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging action: {e}")

# ─── Routes: Auth ────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute(
            "SELECT * FROM admin_users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']

            cursor.execute(
                "UPDATE admin_users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user['id'],)
            )
            conn.commit()

            log_action("login", f"Usuário {username} fez login")
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'error')

        conn.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    log_action("logout", f"Usuário {session.get('username')} fez logout")
    session.clear()
    flash('Logout realizado com sucesso.', 'success')
    return redirect(url_for('login'))

# ─── Routes: Dashboard ───────────────────────────────────────────────────────
@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM access_logs")
    total_logs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM news_sources WHERE is_active = 1")
    active_sources = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM update_times WHERE is_active = 1")
    active_times = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM generation_logs")
    total_generations = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM breaking_news")
    total_breaking = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 10")
    recent_logs = cursor.fetchall()

    cursor.execute("SELECT * FROM generation_logs ORDER BY created_at DESC LIMIT 5")
    recent_generations = cursor.fetchall()

    conn.close()

    log_action("view_dashboard")

    return render_template('dashboard.html',
        total_logs=total_logs,
        active_sources=active_sources,
        active_times=active_times,
        total_generations=total_generations,
        total_breaking=total_breaking,
        recent_logs=recent_logs,
        recent_generations=recent_generations
    )

# ─── Routes: Logs ────────────────────────────────────────────────────────────
@app.route('/logs')
@login_required
def logs():
    conn = get_db()
    cursor = conn.cursor()

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    action_filter = request.args.get('action', '')
    user_filter = request.args.get('user', '')

    query = "SELECT al.*, au.username FROM access_logs al LEFT JOIN admin_users au ON al.user_id = au.id"
    count_query = "SELECT COUNT(*) FROM access_logs al LEFT JOIN admin_users au ON al.user_id = au.id"
    params = []
    conditions = []

    if action_filter:
        conditions.append("al.action LIKE ?")
        params.append(f"%{action_filter}%")

    if user_filter:
        conditions.append("au.username LIKE ?")
        params.append(f"%{user_filter}%")

    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        query += where_clause
        count_query += where_clause

    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    query += " ORDER BY al.timestamp DESC LIMIT ? OFFSET ?"
    cursor.execute(query, params + [per_page, offset])
    logs_data = cursor.fetchall()

    conn.close()

    log_action("view_logs", f"Filtros: action={action_filter}, user={user_filter}")

    return render_template('logs.html',
        logs=logs_data,
        page=page,
        per_page=per_page,
        total=total,
        action_filter=action_filter,
        user_filter=user_filter
    )

@app.route('/logs/clear', methods=['POST'])
@login_required
def clear_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM access_logs")
    conn.commit()
    conn.close()

    log_action("clear_logs", "Todos os logs foram limpos")
    flash('Logs limpos com sucesso.', 'success')
    return redirect(url_for('logs'))

# ─── Routes: Schedule ────────────────────────────────────────────────────────
@app.route('/schedule')
@login_required
def schedule():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM schedule_config")
    configs = {row['config_key']: row['config_value'] for row in cursor.fetchall()}

    cursor.execute("SELECT * FROM update_times ORDER BY update_time")
    times = cursor.fetchall()

    conn.close()

    log_action("view_schedule")

    return render_template('schedule.html', configs=configs, times=times)

@app.route('/schedule/update', methods=['POST'])
@login_required
def update_schedule():
    data = request.get_json()

    conn = get_db()
    cursor = conn.cursor()

    for key, value in data.get('configs', {}).items():
        cursor.execute(
            "INSERT OR REPLACE INTO schedule_config (config_key, config_value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )

    conn.commit()
    conn.close()

    log_action("update_schedule", f"Configurações atualizadas: {json.dumps(data.get('configs', {}))}")
    return jsonify({"success": True, "message": "Agendamento atualizado com sucesso"})

@app.route('/schedule/times', methods=['POST'])
@login_required
def manage_times():
    data = request.get_json()
    action = data.get('action')

    conn = get_db()
    cursor = conn.cursor()

    if action == 'add':
        time_val = data.get('time')
        cursor.execute(
            "INSERT INTO update_times (update_time, is_active) VALUES (?, ?)",
            (time_val, 1)
        )
        log_action("add_time", f"Horário {time_val} adicionado")

    elif action == 'toggle':
        time_id = data.get('id')
        cursor.execute(
            "UPDATE update_times SET is_active = NOT is_active WHERE id = ?",
            (time_id,)
        )
        log_action("toggle_time", f"Horário ID {time_id} alternado")

    elif action == 'delete':
        time_id = data.get('id')
        cursor.execute("DELETE FROM update_times WHERE id = ?", (time_id,))
        log_action("delete_time", f"Horário ID {time_id} removido")

    conn.commit()

    cursor.execute("SELECT * FROM update_times ORDER BY update_time")
    times = cursor.fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "times": [{"id": t['id'], "time": t['update_time'], "active": bool(t['is_active'])} for t in times]
    })

# ─── Routes: Sources ─────────────────────────────────────────────────────────
@app.route('/sources')
@login_required
def sources():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM news_sources ORDER BY priority, name")
    sources_data = cursor.fetchall()

    conn.close()

    log_action("view_sources")

    return render_template('sources.html', sources=sources_data)

@app.route('/sources/add', methods=['POST'])
@login_required
def add_source():
    data = request.get_json()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO news_sources (name, url, category, is_active, priority) VALUES (?, ?, ?, ?, ?)",
        (data['name'], data['url'], data.get('category', 'economia'), 1, data.get('priority', 1))
    )

    conn.commit()
    source_id = cursor.lastrowid
    conn.close()

    log_action("add_source", f"Fonte '{data['name']}' adicionada")
    return jsonify({"success": True, "id": source_id, "message": "Fonte adicionada com sucesso"})

@app.route('/sources/update', methods=['POST'])
@login_required
def update_source():
    data = request.get_json()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE news_sources SET name=?, url=?, category=?, is_active=?, priority=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (data['name'], data['url'], data.get('category', 'economia'), data.get('is_active', 1), data.get('priority', 1), data['id'])
    )

    conn.commit()
    conn.close()

    log_action("update_source", f"Fonte ID {data['id']} atualizada")
    return jsonify({"success": True, "message": "Fonte atualizada com sucesso"})

@app.route('/sources/delete', methods=['POST'])
@login_required
def delete_source():
    data = request.get_json()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM news_sources WHERE id = ?", (data['id'],))

    conn.commit()
    conn.close()

    log_action("delete_source", f"Fonte ID {data['id']} removida")
    return jsonify({"success": True, "message": "Fonte removida com sucesso"})

@app.route('/sources/toggle', methods=['POST'])
@login_required
def toggle_source():
    data = request.get_json()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE news_sources SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (data['id'],)
    )

    conn.commit()
    conn.close()

    log_action("toggle_source", f"Fonte ID {data['id']} alternada")
    return jsonify({"success": True, "message": "Status da fonte alternado"})

# ─── Routes: Generation ──────────────────────────────────────────────────────
@app.route('/generate', methods=['POST'])
@login_required
def generate_newsletter():
    """Gera o newsletter manualmente."""
    log_action("generate_manual", "Geração manual solicitada")
    flash('Geração de newsletter não disponível no Vercel. Use o script local.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/generate/breaking', methods=['POST'])
@login_required
def generate_breaking_news():
    """Gera uma notícia extraordinária."""
    data = request.get_json()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO breaking_news (title, content, source, priority, status) VALUES (?, ?, ?, ?, ?)",
        (data['title'], data['content'], data.get('source', 'manual'), data.get('priority', 'alta'), 'publicada')
    )

    conn.commit()
    conn.close()

    log_action("generate_breaking", f"Notícia extraordinária: {data['title']}")
    return jsonify({"success": True, "message": "Notícia extraordinária gerada"})

# ─── Routes: API ─────────────────────────────────────────────────────────────
@app.route('/api/config', methods=['GET'])
def get_config():
    """API para obter configurações atuais."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM schedule_config")
    configs = {row['config_key']: row['config_value'] for row in cursor.fetchall()}

    cursor.execute("SELECT * FROM update_times WHERE is_active = 1 ORDER BY update_time")
    times = [row['update_time'] for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM news_sources WHERE is_active = 1 ORDER BY priority")
    sources = [{
        "id": row['id'],
        "name": row['name'],
        "url": row['url'],
        "category": row['category']
    } for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        "schedule": configs,
        "update_times": times,
        "sources": sources
    })

@app.route('/api/sources', methods=['GET'])
def api_sources():
    """API pública para listar fontes ativas."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM news_sources WHERE is_active = 1 ORDER BY priority")
    sources = [{
        "name": row['name'],
        "url": row['url'],
        "category": row['category']
    } for row in cursor.fetchall()]

    conn.close()

    return jsonify(sources)

# ─── Init DB on cold start ──────────────────────────────────────────────────
init_db()

# ─── Vercel Handler ──────────────────────────────────────────────────────────
# This is what Vercel calls
def handler(request, response):
    return app(request.environ, response.start)
