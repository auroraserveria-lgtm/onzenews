#!/usr/bin/env python3
"""
OnzeNews — Scraper de Notícias
Coleta notícias de fontes brasileiras e gera HTMLs para o gerador
"""

import os
import re
import sys
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from html.parser import HTMLParser

# ─── Configuração ────────────────────────────────────────────────────────────
SOURCES = [
    {
        "name": "UOL Economia",
        "url": "https://economia.uol.com.br/noticias/",
        "selector": "h2 a, h3 a"
    },
    {
        "name": "G1 Economia", 
        "url": "https://g1.globo.com/economia/",
        "selector": "a"
    },
    {
        "name": "InfoMoney",
        "url": "https://www.infomoney.com.br/noticias/",
        "selector": "h2 a, h3 a"
    }
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


# ─── HTML Parser ─────────────────────────────────────────────────────────────
class LinkExtractor(HTMLParser):
    """Extrai links e títulos de páginas HTML."""
    
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = None
        self.current_text = []
        self.in_a = False
        self.seen = set()
        
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.in_a = True
            self.current_text = []
            for attr, value in attrs:
                if attr == 'href' and value and not value.startswith('#') and not value.startswith('javascript'):
                    self.current_href = value
                    
    def handle_endtag(self, tag):
        if tag == 'a' and self.in_a:
            self.in_a = False
            title = ' '.join(self.current_text).strip()
            if (self.current_href and title and len(title) > 20 
                and title not in self.seen
                and not any(x in title.lower() for x in ['cookie', 'privacidade', 'termos', 'assine', 'login', 'cadastro'])):
                self.seen.add(title)
                self.links.append({
                    'title': title[:200],
                    'url': self.current_href
                })
            self.current_href = None
            
    def handle_data(self, data):
        if self.in_a:
            self.current_text.append(data.strip())


# ─── Scraping ────────────────────────────────────────────────────────────────
def fetch_url(url):
    """Busca conteúdo de uma URL."""
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8'
        })
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  Erro ao buscar {url}: {e}")
        return ""


def scrape_source(source):
    """Faz scrape de uma fonte de notícias."""
    print(f"  Coletando {source['name']}...")
    html = fetch_url(source['url'])
    if not html:
        return []
    
    parser = LinkExtractor()
    try:
        parser.feed(html)
    except:
        pass
    
    return parser.links[:15]  # Top 15


def collect_all_news():
    """Coleta notícias de todas as fontes."""
    print("📰 Coletando notícias...")
    all_news = []
    
    for source in SOURCES:
        news = scrape_source(source)
        for n in news:
            n['source'] = source['name']
        all_news.extend(news)
        print(f"    {len(news)} notícias de {source['name']}")
    
    print(f"  Total: {len(all_news)} notícias")
    return all_news


# ─── Geração de HTML ────────────────────────────────────────────────────────
def clean_title(title):
    """Limpa e normaliza um título."""
    title = re.sub(r'\s+', ' ', title).strip()
    title = title.encode('latin-1', errors='ignore').decode('latin-1')
    return title


def generate_resumo_anterior(news):
    """Gera HTML do resumo do dia anterior."""
    items = []
    seen = set()
    
    for n in news[:12]:
        title = clean_title(n['title'])
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        if title_hash not in seen:
            seen.add(title_hash)
            items.append(f'<li><a href="{n["url"]}" target="_blank">{title}</a> <span class="source">({n["source"]})</span></li>')
    
    html = f"""<div class="resumo-section">
    <h2>Principais notícias - {ONTEM.strftime('%d/%m/%Y')}</h2>
    <ul class="news-list">
        {chr(10).join(items)}
    </ul>
</div>"""
    
    return html


def generate_agenda(news):
    """Gera HTML da agenda do dia."""
    items = []
    seen = set()
    
    # Eventos financeiros fixos para o dia
    agenda_items = [
        "Mercado financeiro brasileiro abre às 10h (horário de Brasília)",
        "Indicadores econômicos do dia serão divulgados pelo IBGE",
        "Reunião do COPOM pode impactar taxas de juros",
        "Empresas reportam resultados do trimestre"
    ]
    
    for i, item in enumerate(agenda_items, 1):
        items.append(f'<li class="agenda-item"><span class="number">{i}</span> {item}</li>')
    
    # Adicionar notícias como agenda
    for n in news[:5]:
        title = clean_title(n['title'])
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        if title_hash not in seen:
            seen.add(title_hash)
            items.append(f'<li class="agenda-item"><span class="source-tag">{n["source"]}</span> {title}</li>')
    
    html = f"""<div class="agenda-section">
    <h2>Agenda do Dia - {HOJE.strftime('%d/%m/%Y')}</h2>
    <ul class="agenda-list">
        {chr(10).join(items)}
    </ul>
</div>"""
    
    return html


def generate_resumo(news):
    """Gera HTML do resumo do dia (texto narrativo)."""
    paragraphs = []
    seen = set()
    
    # Introdução
    data_extenso = f"{HOJE.day} de {MESES_PT[HOJE.month]} de {HOJE.year}"
    paragraphs.append(f"<p>Bom dia! Hoje é {data_extenso}. Veja o que está movimentando o mercado financeiro.</p>")
    
    # Agrupar por fonte
    by_source = {}
    for n in news:
        src = n['source']
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(n)
    
    # Gerar parágrafos
    for source_name, source_news in by_source.items():
        paragraphs.append(f"<h3>{source_name}</h3>")
        for n in source_news[:4]:
            title = clean_title(n['title'])
            title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
            if title_hash not in seen:
                seen.add(title_hash)
                paragraphs.append(f"<p>{title}. <a href='{n['url']}' target='_blank'>Leia mais</a>.</p>")
    
    # Conclusão
    paragraphs.append(f"<p>Essas são as principais notícias financeiras do dia. Fique atento ao longo do dia para mais atualizações.</p>")
    
    html = f"""<div class="resumo-dia-section">
    <h2>Resumo do Dia</h2>
    {chr(10).join(paragraphs)}
</div>"""
    
    return html


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  OnzeNews — Scraper de Notícias")
    print("=" * 50)
    
    # Coletar notícias
    news = collect_all_news()
    
    if not news:
        print("⚠️  Nenhuma notícia coletada. Usando exemplos...")
        # Fallback com notícias de exemplo
        news = [
            {"title": "Ibovespa sobe 1,5% com otimismo sobre reformas", "url": "#", "source": "UOL Economia"},
            {"title": "Dólar cai e fecha a R$ 4,95 na terça-feira", "url": "#", "source": "G1 Economia"},
            {"title": "Selic pode ser cortada na próxima reunião do COPOM", "url": "#", "source": "InfoMoney"},
            {"title": "Petrobras anuncia novo investimento em refino", "url": "#", "source": "UOL Economia"},
            {"title": "Bitcoin atinge nova máxima histórica de US$ 70 mil", "url": "#", "source": "InfoMoney"},
            {"title": "Produção industrial cresce 2,3% no acumulado do ano", "url": "#", "source": "G1 Economia"},
            {"title": "Inflação fica dentro da meta pelo terceiro mês seguido", "url": "#", "source": "UOL Economia"},
            {"title": "Empresas de tecnologia lideram altas na bolsa", "url": "#", "source": "InfoMoney"},
        ]
    
    # Gerar HTMLs
    print("\n📝 Gerando arquivos HTML...")
    
    resumo_anterior = generate_resumo_anterior(news)
    agenda = generate_agenda(news)
    resumo = generate_resumo(news)
    
    # Salvar arquivos
    (OUTPUT_DIR / "secao_resumo_anterior.html").write_text(resumo_anterior, encoding='utf-8')
    (OUTPUT_DIR / "secao_agenda.html").write_text(agenda, encoding='utf-8')
    (OUTPUT_DIR / "secao_resumo_dia.html").write_text(resumo, encoding='utf-8')
    
    print(f"  ✅ secao_resumo_anterior.html")
    print(f"  ✅ secao_agenda.html")
    print(f"  ✅ secao_resumo_dia.html")
    
    print("\n🎉 Scraping concluído!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
