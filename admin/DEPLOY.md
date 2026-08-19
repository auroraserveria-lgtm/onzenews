# 🚀 Deploy do OnzeNews Admin na Web

## Guia Completo de Deploy

### Opção 1: Render.com (Recomendado)

#### Passo 1: Criar Conta no Render
1. Acesse [render.com](https://render.com)
2. Clique em "Get Started for Free"
3. Crie uma conta com GitHub, Google ou Email

#### Passo 2: Preparar o Repositório
```bash
cd "C:\Users\Casa\Documents\Default Project\ONZE News"
git init
git add admin/
git commit -m "OnzeNews Admin Panel"
```

#### Passo 3: Criar Repositório no GitHub
1. Acesse [github.com](https://github.com)
2. Clique em "New repository"
3. Nome: `onzenews-admin`
4. Público ou Privado (sua escolha)
5. Clique em "Create repository"

#### Passo 4: Push para GitHub
```bash
git remote add origin https://github.com/SEU_USUARIO/onzenews-admin.git
git push -u origin main
```

#### Passo 5: Criar Serviço no Render
1. No Render, clique em "New +"
2. Selecione "Web Service"
3. Conecte seu repositório GitHub
4. Configure:
   - **Name**: `onzenews-admin`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free
5. Clique "Create Web Service"

#### Passo 6: Acessar o Painel
- URL: `https://onzenews-admin.onrender.com`
- Login: `admin`
- Senha: `admin123`

---

### Opção 2: Railway.app

#### Passo 1: Criar Conta
1. Acesse [railway.app](https://railway.app)
2. Crie uma conta com GitHub

#### Passo 2: Criar Projeto
1. Clique em "New Project"
2. Selecione "Deploy from GitHub repo"
3. Selecione seu repositório

#### Passo 3: Configurar
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

#### Passo 4: Gerar Domínio
1. Vá em "Settings"
2. Clique em "Generate Domain"
3. URL: `https://onzenews-admin.up.railway.app`

---

### Opção 3: PythonAnywhere

#### Passo 1: Criar Conta
1. Acesse [pythonanywhere.com](https://www.pythonanywhere.com)
2. Crie uma conta gratuita

#### Passo 2: Fazer Upload
1. Vá em "Files"
2. Clique em "Upload a file"
3. Envie todos os arquivos da pasta `admin/`

#### Passo 3: Configurar Web App
1. Vá em "Web"
2. Clique "Add a new web app"
3. Selecione "Manual configuration"
4. Selecione "Python 3.10"

#### Passo 4: Configurar WSGI
Edite o arquivo WSGI:
```python
import sys
project_home = '/home/SEU_USUARIO/onzenews-admin'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
from app import app as application
```

#### Passo 5: Iniciar
1. Clique em "Reload"
2. Acesse: `https://SEU_USUARIO.pythonanywhere.com`

---

### Opção 4: Fly.io

#### Passo 1: Instalar Fly CLI
```bash
curl -L https://fly.io/install.sh | sh
```

#### Passo 2: Login
```bash
fly auth login
```

#### Passo 3: Iniciar Projeto
```bash
cd admin/
fly launch
```

#### Passo 4: Deploy
```bash
fly deploy
```

#### Passo 5: Acessar
- URL: `https://onzenews-admin.fly.dev`

---

## 🔐 Segurança

### Mudar Senha Padrão
1. Acesse o painel
2. Vá em "Configurações" (futuro)
3. Altere a senha

### Ou manualmente:
```python
# No Python, gere um hash da nova senha
import hashlib
nova_senha = "sua_nova_senha"
hash = hashlib.sha256(nova_senha.encode()).hexdigest()
print(hash)
```

```sql
-- No banco SQLite
UPDATE admin_users SET password_hash = 'HASH_AQUI' WHERE username = 'admin';
```

---

## 🌐 Domínio Personalizado

### No Render.com
1. Vá em "Settings"
2. Clique em "Custom Domains"
3. Adicione seu domínio
4. Configure DNS:
   ```
   CNAME: onzenews-admin.onrender.com
   ```

### No Railway.app
1. Vá em "Settings"
2. Clique em "Networking"
3. Adicione domínio personalizado

---

## 📱 Acesso Mobile

O painel é **100% responsivo** — funciona perfeitamente em:
- 📱 Smartphones
- 📱 Tablets
- 💻 Computadores

Basta acessar a URL em qualquer navegador!

---

## 🔄 Atualizações

### Para atualizar o código:
```bash
git add .
git commit -m "Atualização"
git push
```

O Render/Railway faz deploy automático a cada push!

---

## 🐛 Debug

### Ver logs no Render:
1. Acesse o painel do Render
2. Clique no seu serviço
3. Vá em "Logs"

### Ver logs no Railway:
1. Acesse o painel do Railway
2. Clique no seu serviço
3. Vá em "Deployments"

---

## 💡 Dicas

1. **Use variáveis de ambiente** para senhas e configs sensíveis
2. **Ative o SSL** (já vem por padrão no Render)
3. **Configure backups** do banco SQLite
4. **Monitore o uso** para não estourar o tier gratuito

---

## 🆘 Problemas Comuns

### "Application Error"
- Verifique os logs
- Confirme que o `requirements.txt` está correto
- Verifique se o `startCommand` está correto

### "Database not found"
- O banco é criado automaticamente
- Verifique permissões de escrita

### "Port already in use"
- O Render usa a variável `PORT` automaticamente
- Não defina porta fixa no código

---

## 📞 Suporte

- **Render**: [docs.render.com](https://docs.render.com)
- **Railway**: [docs.railway.app](https://docs.railway.app)
- **PythonAnywhere**: [help.pythonanywhere.com](https://help.pythonanywhere.com)
