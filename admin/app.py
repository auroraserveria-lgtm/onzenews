"""
OnzeNews — Painel Administrativo
Flask + SQLite + GitHub Actions Integration
"""

import os
import re
import json
import sqlite3
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from functools import wraps
from urllib.request import urlopen, Request
from urllib.parse import quote
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash

# ─── Configuração ────────────────────────────────────────────────────────────
# No Vercel, o diretório base é /tmp para escrita
IS_VERCEL = os.path.exists("/tmp")
BASE_DIR = "/tmp" if IS_VERCEL else os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "onzenews.db")
OUTPUT_DIR = os.path.join(APP_DIR, "..", "output")

# GitHub Config (via environment variables)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "auroraserveria-lgtm/onzenews")
GITHUB_WORKFLOW = os.environ.get("GITHUB_WORKFLOW", "gerar-newsletter.yml")

# Caminho para templates e static
TEMPLATE_DIR = os.path.join(APP_DIR, "templates")
STATIC_DIR = os.path.join(APP_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = secrets.token_hex(32)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(BASE_DIR, "flask_session")

# ─── GitHub API Helper ──────────────────────────────────────────────────────
def github_api(endpoint, method="GET", data=None):
    """Faz chamada à API do GitHub."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token não configurado"}
    
    url = f"https://api.github.com{endpoint}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OnzeNews-Admin",
        "Content-Type": "application/json"
    }
    
    body = json.dumps(data).encode('utf-8') if data else None
    
    try:
        req = Request(url, headers=headers, data=body, method=method)
        with urlopen(req, timeout=30) as resp:
            # 204 No Content = sucesso (ex: workflow dispatch)
            if resp.status == 204:
                return None
            raw = resp.read().decode('utf-8')
            if not raw or not raw.strip():
                return None
            return json.loads(raw)
    except Exception as e:
        # Se é HTTPError, tentar extrair a mensagem
        err_str = str(e)
        if hasattr(e, 'code') and e.code == 204:
            return None
        return {"error": err_str}


def get_workflow_content():
    """Busca o conteúdo atual do workflow file."""
    endpoint = f"/repos/{GITHUB_REPO}/contents/.github/workflows/{GITHUB_WORKFLOW}"
    result = github_api(endpoint)
    
    if "error" in result:
        return None, result["error"]
    
    # Decodificar conteúdo
    content = base64.b64decode(result["content"]).decode('utf-8')
    return content, None


def update_workflow_content(new_content, message="chore: update schedule via admin panel"):
    """Atualiza o workflow file no GitHub."""
    # Primeiro, buscar SHA atual
    endpoint = f"/repos/{GITHUB_REPO}/contents/.github/workflows/{GITHUB_WORKFLOW}"
    result = github_api(endpoint)
    
    if "error" in result:
        return False, result["error"]
    
    sha = result["sha"]
    
    # Atualizar
    data = {
        "message": message,
        "content": base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    
    result = github_api(endpoint, method="PUT", data=data)
    
    if "error" in result:
        return False, result["error"]
    
    return True, None


def trigger_workflow():
    """Dispara o workflow manualmente."""
    endpoint = f"/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    data = {"ref": "master"}
    
    result = github_api(endpoint, method="POST", data=data)
    
    # 204 No Content = sucesso (result é None)
    if result is None:
        return True, None
    
    if isinstance(result, dict) and "error" not in result:
        return True, None
    
    return False, result.get("error", "Erro desconhecido")


def update_cron_schedule(times):
    """Atualiza o cron schedule no workflow baseado nos horários configurados."""
    content, error = get_workflow_content()
    if error:
        return False, error
    
    # Converter horários para cron format (UTC)
    # Horário de Brasília = UTC-3
    cron_lines = []
    for time_str in times:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        
        # Converter para UTC (adicionar 3 horas)
        utc_hour = (hour + 3) % 24
        
        cron_lines.append(f"    - cron: '{minute} {utc_hour} * * *'")
    
    if not cron_lines:
        cron_lines = ["    - cron: '0 11 * * *'"]  # Padrão: 8h BRT
    
    # Substituir a seção de schedule no YAML
    new_schedule = "  schedule:\n    # Gerado automaticamente pelo painel admin\n" + "\n".join(cron_lines)
    
    # Encontrar e substituir a seção schedule completamente
    # O padrão deve capturar de "  schedule:" até antes de "  workflow_dispatch:" ou "jobs:"
    pattern = r'  schedule:\s*\n(?:.*\n)*?(?=  [a-z_]|\njobs:)'
    new_content = re.sub(pattern, new_schedule + "\n", content, flags=re.DOTALL)
    
    if new_content == content:
        return False, "Não foi possível atualizar o schedule"
    
    return update_workflow_content(new_content, "feat: update schedule via admin panel")


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
        default_times = ["08:00"]
        for time_val in default_times:
            cursor.execute(
                "INSERT INTO update_times (update_time, is_active) VALUES (?, ?)",
                (time_val, 1)
            )

    # Inserir fontes padrão
    cursor.execute("SELECT COUNT(*) FROM news_sources")
    if cursor.fetchone()[0] == 0:
        default_sources = [
            ("InfoMoney", "https://www.infomoney.com.br/feed/", "economia", 1, 1),
            ("G1 Economia", "https://g1.globo.com/rss/g1/", "economia", 1, 2),
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
    except:
        pass

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

    # Verificar status do GitHub
    github_status = "conectado" if GITHUB_TOKEN else "não configurado"
    
    # Buscar último deploy no Vercel (newsletter)
    last_deploy = None
    vercel_token = os.environ.get("VERCEL_TOKEN", "")
    if vercel_token:
        try:
            from urllib.request import urlopen, Request
            import urllib.error
            req = Request(
                "https://api.vercel.com/v6/deployments?projectId=prj_wSI8kDDsxQlawduD2qxJB8MJc2NC&limit=1&target=production",
                headers={
                    "Authorization": f"Bearer {vercel_token}",
                    "User-Agent": "OnzeNews-Admin"
                }
            )
            with urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                deploys = data.get("deployments", [])
                if deploys:
                    created_ts = deploys[0].get("created", 0)
                    if created_ts:
                        last_deploy = datetime.fromtimestamp(created_ts / 1000).isoformat()
        except Exception:
            pass
    
    # Status do último workflow
    workflow_status = None
    if GITHUB_TOKEN:
        try:
            result = github_api(f"/repos/{GITHUB_REPO}/actions/runs?per_page=1")
            runs = result.get("workflow_runs", [])
            if runs:
                workflow_status = {
                    "status": runs[0]["status"],
                    "conclusion": runs[0].get("conclusion"),
                    "created_at": runs[0]["created_at"]
                }
        except Exception:
            pass

    return render_template('dashboard.html',
        total_logs=total_logs,
        active_sources=active_sources,
        active_times=active_times,
        total_generations=total_generations,
        total_breaking=total_breaking,
        recent_logs=recent_logs,
        recent_generations=recent_generations,
        github_status=github_status,
        github_repo=GITHUB_REPO,
        last_deploy=last_deploy,
        workflow_status=workflow_status
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

    # Atualizar configurações
    for key, value in data.get('configs', {}).items():
        cursor.execute(
            "INSERT OR REPLACE INTO schedule_config (config_key, config_value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, value)
        )

    conn.commit()
    conn.close()

    log_action("update_schedule", f"Configuracoes salvas: {json.dumps(data.get('configs', {}))}")
    return jsonify({"success": True, "message": "Agendamento salvo com sucesso"})

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

    # Retornar horários atualizados
    cursor.execute("SELECT * FROM update_times ORDER BY update_time")
    times = cursor.fetchall()
    conn.close()

    # Horarios salvos - o workflow usa o cron do YAML diretamente
    # Atualizacao do GitHub e feita pelo endpoint /schedule/apply

    return jsonify({
        "success": True,
        "times": [{"id": t['id'], "time": t['update_time'], "active": bool(t['is_active'])} for t in times]
    })

@app.route('/schedule/apply', methods=['POST'])
@login_required
def apply_schedule():
    """Aplica os horarios salvos no GitHub Actions (separado do save pra evitar timeout)."""
    if not GITHUB_TOKEN:
        return jsonify({"success": False, "message": "GitHub token nao configurado"})
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT update_time FROM update_times WHERE is_active = 1 ORDER BY update_time")
    times = [row['update_time'] for row in cursor.fetchall()]
    conn.close()
    
    if not times:
        return jsonify({"success": False, "message": "Nenhum horario ativo"})
    
    try:
        success, error = update_cron_schedule(times)
        if success:
            return jsonify({"success": True, "message": f"Cron atualizado no GitHub: {times}"})
        else:
            return jsonify({"success": False, "message": f"Erro: {error}"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro: {str(e)[:100]}"})

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

# ─── Routes: Generation (GitHub Actions) ─────────────────────────────────────
@app.route('/generate', methods=['POST'])
@login_required
def generate_newsletter():
    """Gera o newsletter via GitHub Actions."""
    if not GITHUB_TOKEN:
        flash('GitHub token não configurado. Configure nas variáveis de ambiente.', 'error')
        return redirect(url_for('dashboard'))
    
    log_action("generate_manual", "Geração manual solicitada via painel")
    
    success, error = trigger_workflow()
    
    if success:
        # Registrar no log
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO generation_logs (generation_type, status, message) VALUES (?, ?, ?)",
            ("manual", "executando", "Workflow disparado via painel admin")
        )
        conn.commit()
        conn.close()
        
        flash('Newsletter sendo gerado! O deploy acontecerá em alguns minutos.', 'success')
        log_action("generate_success", "Workflow disparado com sucesso")
    else:
        flash(f'Erro ao disparar workflow: {error}', 'error')
        log_action("generate_error", f"Erro: {error}")
    
    return redirect(url_for('dashboard'))

@app.route('/generate/status', methods=['GET'])
@login_required
def generate_status():
    """Verifica status do último workflow."""
    if not GITHUB_TOKEN:
        return jsonify({"error": "GitHub não configurado"})
    
    result = github_api(f"/repos/{GITHUB_REPO}/actions/runs?per_page=1")
    
    if "error" in result:
        return jsonify(result)
    
    runs = result.get("workflow_runs", [])
    if runs:
        run = runs[0]
        return jsonify({
            "status": run["status"],
            "conclusion": run.get("conclusion"),
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "url": run["html_url"]
        })
    
    return jsonify({"status": "nenhum", "conclusion": None})

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

# ─── Routes: Settings ────────────────────────────────────────────────────────
@app.route('/settings')
@login_required
def settings():
    """Página de configurações do GitHub."""
    return render_template('settings.html',
        github_token_set=bool(GITHUB_TOKEN),
        github_repo=GITHUB_REPO,
        github_workflow=GITHUB_WORKFLOW
    )

@app.route('/settings/test-github', methods=['POST'])
@login_required
def test_github():
    """Testa conexão com GitHub."""
    if not GITHUB_TOKEN:
        return jsonify({"success": False, "message": "Token não configurado"})
    
    result = github_api("/user")
    
    if "login" in result:
        return jsonify({
            "success": True, 
            "message": f"Conectado como {result['login']}"
        })
    else:
        return jsonify({
            "success": False, 
            "message": f"Erro: {result.get('error', 'Desconhecido')}"
        })

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

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("  OnzeNews — Painel Administrativo")
    print("  http://localhost:5000")
    print("  Login: admin / admin123")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # Para produção (Vercel, Render, etc.)
    init_db()
