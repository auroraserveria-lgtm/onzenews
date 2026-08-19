# OnzeNews — Painel Administrativo

## Visão Geral

O Painel Administrativo do OnzeNews permite controle total sobre o funcionamento do jornal financeiro.

## Funcionalidades

### 📊 Dashboard
- Visão geral do sistema
- Estatísticas de uso
- Ações rápidas (gerar newsletter, notícia extraordinária)

### 📋 Logs de Acesso
- Histórico completo de ações
- Filtros por ação e usuário
- Paginação
- Limpeza de logs

### ⏰ Agendamento
- Configuração de dias da semana
- Horários de atualização
- Controle de máximas atualizações por dia
- Ativação/desativação de podcast e PDF

### 📰 Fontes de Informação
- Cadastro de fontes
- Edição e exclusão
- Controle de prioridade
- Ativação/desativação de fontes

## Instalação

```bash
# Instalar dependências
pip install flask

# Iniciar o painel
python admin/app.py

# Acessar no navegador
http://localhost:5000
```

## Credenciais Padrão

| Usuário | Senha |
|---------|-------|
| admin | admin123 |

## Estrutura

```
admin/
├── app.py              # Backend Flask
├── onzenews.db         # Banco SQLite (criado automaticamente)
├── templates/
│   ├── base.html       # Template base
│   ├── login.html      # Página de login
│   ├── dashboard.html  # Dashboard principal
│   ├── logs.html       # Logs de acesso
│   ├── schedule.html   # Configuração de agendamento
│   └── sources.html    # Gerenciamento de fontes
└── static/
    └── css/
        └── admin.css   # Estilos do admin
```

## API Endpoints

### Configurações
- `GET /api/config` - Obter configurações atuais
- `GET /api/sources` - Listar fontes ativas

### Autenticação
- `POST /login` - Fazer login
- `GET /logout` - Fazer logout

### Dashboard
- `GET /` - Dashboard principal

### Logs
- `GET /logs` - Listar logs
- `POST /logs/clear` - Limpar logs

### Agendamento
- `GET /schedule` - Configurações de agendamento
- `POST /schedule/update` - Atualizar configurações
- `POST /schedule/times` - Gerenciar horários

### Fontes
- `GET /sources` - Listar fontes
- `POST /sources/add` - Adicionar fonte
- `POST /sources/update` - Atualizar fonte
- `POST /sources/delete` - Excluir fonte
- `POST /sources/toggle` - Ativar/desativar fonte

### Geração
- `POST /generate` - Gerar newsletter
- `POST /generate/breaking` - Gerar notícia extraordinária

## Integração com gerar_jornal.py

```python
from admin_config import get_admin_config, should_generate_now

# Verificar se deve gerar
if should_generate_now():
    config = get_admin_config()
    # Usar config['sources'] para buscar notícias
    # Usar config['schedule'] para configurações
```

## Conversão para APK (Android)

Para converter o OnzeNews em aplicativo Android:

### Opção 1: PWA (Progressive Web App)
1. Adicionar manifest.json
2. Adicionar service worker
3. Configurar ícones
4. Usar Lighthouse para auditar

### Opção 2: Apache Cordova
```bash
npm install -g cordova
cordova create onzenews-app
cd onzenews-app
cordova platform add android
# Copiar arquivos HTML/JS/CSS para www/
cordova build android
```

### Opção 3: Capacitor (Recomendado)
```bash
npm install @capacitor/core @capacitor/cli
npx cap init OnzeNews com.onzenews.app
npx cap add android
# Copiar arquivos para www/
npx cap sync
npx cap open android
```

### Opção 4: Bubblewrap (TWA)
```bash
npm install -g @aspect-build/bubblewrap
bubblewrap init --manifest=https://onzenews-public.netlify.app/manifest.json
bubblewrap build
```

## Notificações Push

Para notificações push no Android:

1. **Firebase Cloud Messaging (FCM)**
   - Criar projeto no Firebase
   - Configurar FCM no app
   - Enviar notificações via API

2. **OneSignal (mais fácil)**
   - Criar conta no OneSignal
   - Integrar SDK
   - Enviar notificações pelo painel

## Hospedagem do Admin

O admin pode ser hospedado em:

1. **Render.com** (gratuito)
   - Criar conta
   - Conectar repositório GitHub
   - Deploy automático

2. **Railway.app** (gratuito)
   - Similar ao Render
   - Suporte a Python

3. **Fly.io** (gratuito)
   - Deploy via Docker
   - Mais controle

4. **Heroku** (pago)
   - Mais tradicional
   - Fácil de usar
