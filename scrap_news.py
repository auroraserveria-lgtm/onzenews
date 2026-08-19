#!/usr/bin/env python3
"""
OnzeNews — Scraper v4
Foca em RSS financeiros e gera resumos limpos
"""

import os
import re
import sys
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET
from html.parser import HTMLParser

# ─── Configuração ────────────────────────────────────────────────────────────
# Apenas RSS 100% financeiros
RSS_FEEDS = [
    ("InfoMoney", "https://www.infomoney.com.br/feed/"),
]

# EXCLUSÕES rigorosas - qualquer coisa que não é mercado/empresas/economia
EXCLUDE_KEYWORDS = [
    # Crime/Violência
    'crime', 'polícia', 'assassinato', 'morte', 'tráfico', 'drogas',
    'sequestro', 'estupro', 'violência', 'latrocínio', 'homicídio',
    'baleado', 'baleada', 'atirou', 'tiros', 'arma', 'preso',
    # Política (não econômica)
    'candidato', 'campanha', 'votação', 'urna', 'prefeito',
    'governador', 'deputado', 'senador', 'vereador', 'eleiç',
    'turno', 'pleito', 'chapa', 'partido', 'base aliada',
    # Esportes
    'futebol', 'copa', 'jogo', 'campeonato', 'time', 'jogador',
    'gol', 'partida', 'serie', 'brasileirão', 'libertadores',
    'nba', 'nfl', 'f1', 'formula 1', 'tenis', 'mma', 'ufc',
    # Entretenimento
    'celebridade', 'fama', 'namoro', 'casamento', 'divórcio',
    'moda', 'beleza', 'saúde', 'dieta', 'exercício', 'academia',
    'receita', 'culinária', 'comida', 'restaurante', 'menu',
    'filme', 'série', 'netflix', 'música', 'show', 'festival',
    'oscar', 'grammy', 'emmy',
    # Local/Regional (não econômico)
    'prefeitura', 'vagas', 'concurso', 'curso', 'capacitação',
    'vacinação', 'saúde pública', 'hospital', 'upa', 'ubs',
    'enchente', 'desastre', 'incêndio', 'acidente',
    'advogada', 'advogado', 'morre', 'morreu', 'faleceu',
]

# INCLUSÕES - palavras que garantem inclusão
INCLUDE_KEYWORDS = [
    'ibovespa', 'dólar', 'euro', 'selic', 'juros', 'inflação', 'pib',
    'lucro', 'prejuízo', 'bilhão', 'milhão', 'acao', 'ações',
    'investimento', 'dividendo', 'balanço', 'resultado',
    'cotação', 'índice', 'mercado', 'bolsa', 'financeiro',
    'bitcoin', 'cripto', 'criptomoeda', 'fintech',
    'empresas', 'companhia', 'sociedade', 'negócios',
    'banco', 'bancário', 'crédito', 'empréstimo',
    'economia', 'econômico', 'fiscal', 'governo',
    'tesouro', 'renda', 'rendimento', 'fundos',
    'petróleo', 'gás', 'energia', 'mineração',
    'wall street', 'nasdaq', 's&p', 'dow jones',
    'fed', 'fomc', 'tbc', 'copom', 'banco central',
]

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
}

HOJE = datetime.now()
ONTEM = HOJE - timedelta(days=1)


# ─── HTML Stripper ──────────────────────────────────────────────────────────
class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
    def handle_data(self, data):
        self.text.append(data)
    def get_text(self):
        return ' '.join(self.text).strip()

def clean_text(text):
    """Limpa texto de ruído."""
    if not text:
        return ""
    # Remover "The post ... appeared first on"
    text = re.sub(r'The post\s+.*?appeared first on\s+\w+\s*\.?', '', text, flags=re.IGNORECASE)
    # Remover créditos
    text = re.sub(r'Cr[eé]dito:\s*.*?\n?', '', text)
    text = re.sub(r'Fonte:\s*.*?\n?', '', text)
    text = re.sub(r'Divulga[cç][aã]o.*?\n?', '', text)
    # Remover caracteres estranhos
    text = text.replace('?', '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def strip_html(html):
    if not html:
        return ""
    s = HTMLStripper()
    try:
        s.feed(html)
    except:
        pass
    return clean_text(s.get_text())


# ─── RSS Parser ──────────────────────────────────────────────────────────────
def fetch_rss(url):
    """Busca e parseia um RSS feed."""
    items = []
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml'
        })
        with urlopen(req, timeout=15) as resp:
            xml_text = resp.read().decode('utf-8', errors='ignore')
        
        root = ET.fromstring(xml_text)
        
        for item in root.findall('.//item'):
            title = strip_html(item.findtext('title', ''))
            description = strip_html(item.findtext('description', ''))
            link = item.findtext('link', '').strip()
            
            if title and len(title) > 15:
                items.append({
                    'title': title,
                    'description': description[:400],
                    'url': link
                })
    except Exception as e:
        print(f"  Erro: {e}")
    
    return items


def is_financial_news(news):
    """Verificação rigorosa de se é notícia financeira."""
    text = (news['title'] + ' ' + news.get('description', '')).lower()
    
    # Excluir imediatamente
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return False
    
    # Incluir se tiver palavra-chave financeira forte
    for kw in INCLUDE_KEYWORDS:
        if kw in text:
            return True
    
    return False


def collect_news():
    """Coleta notícias financeiras."""
    print("[NEWS] Coletando noticias financeiras (InfoMoney)...")
    all_news = []
    
    for name, url in RSS_FEEDS:
        print(f"  {name}...")
        items = fetch_rss(url)
        financial = [n for n in items if is_financial_news(n)]
        for n in financial:
            n['source'] = name
        all_news.extend(financial)
        print(f"    {len(financial)} noticias financeiras de {len(items)} total")
    
    # Remover duplicatas
    seen = set()
    unique = []
    for n in all_news:
        title_hash = hashlib.md5(n['title'].encode()).hexdigest()[:10]
        if title_hash not in seen:
            seen.add(title_hash)
            unique.append(n)
    
    print(f"  Total: {len(unique)} noticias unicas")
    return unique[:12]


# ─── Geração de Resumos ─────────────────────────────────────────────────────
def get_first_sentences(text, num_sentences=1):
    """Pegar primeiras frases de um texto."""
    if not text:
        return ""
    sentences = text.split('.')
    result = '. '.join(s.strip() for s in sentences[:num_sentences] if s.strip())
    return result + '.' if result else ''


def generate_resumo_anterior(news):
    """Gera resumo narrativo do dia anterior."""
    paragraphs = []
    
    data = ONTEM.strftime('%d/%m/%Y')
    paragraphs.append(f'<p>O mercado financeiro no dia {data} apresentou as seguintes movimentações:</p>')
    
    # Coletar frases limpas
    phrases = []
    for n in news:
        desc = n.get('description', '')
        title = n['title']
        
        # Pegar frase limpa
        text = desc if len(desc) > 50 else title
        sentence = get_first_sentences(text, 1)
        if sentence and len(sentence) > 30:
            phrases.append(sentence)
    
    # Gerar parágrafos (2 frases cada)
    for i in range(0, min(len(phrases), 10), 2):
        group = phrases[i:i+2]
        paragraphs.append(f'<p>{" ".join(group)}</p>')
    
    return '\n'.join(paragraphs)


def generate_agenda(news):
    """Gera agenda do dia."""
    items = []
    
    fixes = [
        "Mercado financeiro brasileiro abre às 10h (horário de Brasília)",
        "Indicadores econômicos serão divulgados ao longo do dia",
    ]
    
    for i, item in enumerate(fixes, 1):
        items.append(f'<li><strong>{i}.</strong> {item}</li>')
    
    count = len(fixes) + 1
    for n in news[:4]:
        title = n['title']
        if len(title) > 15:
            items.append(f'<li><strong>{count}.</strong> {title}</li>')
            count += 1
    
    return '<ul>\n' + '\n'.join(items) + '\n</ul>'


def generate_resumo(news):
    """Gera resumo narrativo do dia."""
    paragraphs = []
    
    data_extenso = f"{HOJE.day} de {MESES_PT[HOJE.month]} de {HOJE.year}"
    paragraphs.append(f'<p>Bom dia! Hoje é {data_extenso}. Veja o que está movimentando o mercado financeiro.</p>')
    
    # Coletar frases
    phrases = []
    for n in news[:8]:
        desc = n.get('description', '')
        title = n['title']
        
        text = desc if len(desc) > 50 else title
        sentence = get_first_sentences(text, 1)
        if sentence and len(sentence) > 30:
            phrases.append(sentence)
    
    # Gerar parágrafos (3 frases cada)
    for i in range(0, min(len(phrases), 9), 3):
        group = phrases[i:i+3]
        paragraphs.append(f'<p>{" ".join(group)}</p>')
    
    paragraphs.append(f'<p>Essas são as principais notícias financeiras do dia.</p>')
    
    return '\n'.join(paragraphs)


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  OnzeNews — Scraper v4 (RSS Financeiro)")
    print("=" * 50)
    
    news = collect_news()
    
    if not news:
        print("[WARN] Nenhuma noticia coletada!")
        return 1
    
    print("\n[WRITE] Gerando resumos...")
    
    resumo_anterior = generate_resumo_anterior(news)
    agenda = generate_agenda(news)
    resumo = generate_resumo(news)
    
    (OUTPUT_DIR / "secao_resumo_anterior.html").write_text(resumo_anterior, encoding='utf-8')
    (OUTPUT_DIR / "secao_agenda.html").write_text(agenda, encoding='utf-8')
    (OUTPUT_DIR / "secao_resumo_dia.html").write_text(resumo, encoding='utf-8')
    
    print(f"  [OK] secao_resumo_anterior.html ({len(resumo_anterior)} chars)")
    print(f"  [OK] secao_agenda.html ({len(agenda)} chars)")
    print(f"  [OK] secao_resumo_dia.html ({len(resumo)} chars)")
    
    print("\n[DONE] Concluido!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
