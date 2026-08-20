#!/usr/bin/env python3
"""
OnzeNews — Scraper v6
Busca artigos inteiros e gera resumos profundos com seções temáticas
"""

import os
import re
import sys
import hashlib
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET
from html.parser import HTMLParser

# ─── Configuração ────────────────────────────────────────────────────────────
# Fontes organizadas por categoria
RSS_FEEDS = {
    "economia": [
        ("InfoMoney", "https://www.infomoney.com.br/feed/"),
        ("G1 Economia", "https://g1.globo.com/rss/g1/"),
        ("UOL Economia", "https://economia.uol.com.br/rss.xml"),
        ("Investing.com", "https://br.investing.com/rss/news.rss"),
    ],
    "rh": [
        ("folha.uol.com.br", "https://feeds.folha.uol.com.br/mercado/rss091.xml"),
        ("R7 Negócios", "https://noticias.r7.com/paraiba/portal-correio/rss.xml"),
        ("ABRH-SP", "https://abrhsp.org.br/feed/"),
    ],
    "tecnologia": [
        ("G1 Tecnologia", "https://g1.globo.com/rss/g1/tecnologia/"),
        ("InfoMoney Tech", "https://www.infomoney.com.br/feed/"),
        ("Finsiders", "https://finsidersbrasil.com.br/feed/"),
    ],
}

EXCLUDE_KEYWORDS = [
    'crime', 'polícia', 'assassinato', 'morte', 'tráfico', 'drogas',
    'sequestro', 'estupro', 'violência', 'baleado', 'baleada',
    'candidato', 'campanha', 'votação', 'urna', 'prefeito',
    'governador', 'deputado', 'senador', 'vereador', 'eleiç',
    'futebol', 'copa', 'jogo', 'campeonato', 'time', 'jogador',
    'celebridade', 'fama', 'namoro', 'casamento', 'divórcio',
    'moda', 'beleza', 'dieta', 'receita', 'culinária',
    'filme', 'série', 'netflix', 'música', 'show',
    'prefeitura', 'vagas', 'concurso', 'curso', 'capacitação',
    'vacinação', 'hospital', 'upa', 'enchente', 'incêndio',
    'advogada', 'advogado', 'morre', 'morreu', 'faleceu',
]

# Palavras-chave por categoria para filtragem inteligente
CATEGORY_KEYWORDS = {
    "economia": [
        'ibovespa', 'dólar', 'euro', 'selic', 'juros', 'inflação', 'pib',
        'lucro', 'prejuízo', 'bilhão', 'milhão', 'ações', 'investimento',
        'dividendo', 'balanço', 'resultado', 'cotação', 'índice', 'mercado',
        'bolsa', 'financeiro', 'bitcoin', 'cripto', 'fintech', 'empresas',
        'banco', 'crédito', 'economia', 'tesouro', 'renda', 'fundos',
        'petróleo', 'energia', 'wall street', 'nasdaq', 'fed', 'fomc', 'copom',
        'recompra', 'títulos', 'soberania', 'risco', ' spread', 'creditício',
    ],
    "rh": [
        'nr-1', 'nr1', 'norma regulamentadora', 'saúde mental', 'trabalho',
        'rh', 'recursos humanos', 'colaborador', 'funcionário', 'empregado',
        'assédio', 'burnout', 'estresse', 'psicossocial', 'bem-estar',
        'capacitação', 'treinamento', 'desenvolvimento', 'carreira',
        'rotatividade', 'absenteísmo', 'engajamento', 'clima organizacional',
        'pgr', 'gro', 'sst', 'segurança do trabalho', 'medicina do trabalho',
    ],
    "tecnologia": [
        'inteligência artificial', 'ia', 'machine learning', 'blockchain',
        'fintech', 'open finance', 'pix', 'pagamento', 'digital',
        'criptomoeda', 'bitcoin', 'ethereum', 'web3', 'defi',
        'cloud', 'software', 'hardware', 'cibersegurança', 'dados',
        'startup', 'inovação', 'transformação digital', 'automação',
    ],
}

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
}

HOJE = datetime.now()
ONTEM = HOJE - timedelta(days=1)


# ─── HTML Parsing ───────────────────────────────────────────────────────────
class ArticleExtractor(HTMLParser):
    """Extrai texto principal de um artigo HTML."""
    
    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self.current_text = []
        self.in_article = False
        self.in_p = False
        self.in_script = False
        self.in_style = False
        self.tag_stack = []
        self.depth = 0
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag in ('script', 'style', 'nav', 'header', 'footer', 'aside'):
            self.in_script = True
            return
            
        if tag == 'article' or (tag == 'div' and 'article' in attrs_dict.get('class', '')):
            self.in_article = True
            self.depth = 0
            
        if self.in_article:
            self.depth += 1
            
        if tag == 'p' and not self.in_script:
            self.in_p = True
            self.current_text = []
            
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'header', 'footer', 'aside'):
            self.in_script = False
            return
            
        if tag == 'p' and self.in_p:
            self.in_p = False
            text = ' '.join(self.current_text).strip()
            if len(text) > 30:  # Só parágrafos significativos
                self.paragraphs.append(text)
                
        if self.in_article:
            self.depth -= 1
            if self.depth <= 0:
                self.in_article = False
                
    def handle_data(self, data):
        if not self.in_script and self.in_p:
            self.current_text.append(data.strip())


def fetch_article_content(url):
    """Busca e extrai conteúdo de um artigo."""
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8'
        })
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        
        # Tentar extrair com parser
        extractor = ArticleExtractor()
        extractor.feed(html)
        
        # Se não encontrou artigo, tentar extrair todos os <p>
        if len(extractor.paragraphs) < 2:
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
            texts = []
            for p in paragraphs:
                text = re.sub(r'<[^>]+>', '', p).strip()
                if len(text) > 40:
                    texts.append(text)
            extractor.paragraphs = texts[:10]
        
        # Limpar e retornar
        result = []
        for p in extractor.paragraphs[:8]:
            p = re.sub(r'\s+', ' ', p).strip()
            if len(p) > 30:
                result.append(p)
        
        return ' '.join(result)[:2000]
    except Exception as e:
        return ""


def clean_text(text):
    """Limpa texto de ruído e spam."""
    if not text:
        return ""
    
    # Padrões de ruído para remover (mais agressivo)
    noise_patterns = [
        r'Gostaria de receber.*?(?=\s|$)',
        r'Acesse seus artigos.*?(?=\s|$)',
        r'Você tem \d+ acessos.*?(?=\s|$)',
        r'Assinantes podem.*?(?=\s|$)',
        r'Tem alguma sugestão.*?(?=\s|$)',
        r'Envie para o.*?(?=\s|$)',
        r'Leia a íntegra.*?(?=\s|$)',
        r'\(Leia a íntegra.*?\)',
        r'Canal do YouTube.*?(?=\s|$)',
        r'(\?|&)utm_.*',
        r'Assine a newsletter.*?(?=\s|$)',
        r'Receba por e-mail.*?(?=\s|$)',
        r'Outras notícias.*?(?=\s|$)',
        r'Veja também.*?(?=\s|$)',
        r'collapsed away.*?(?=\s|$)',
        r'\.html.*?(?=\s|$)',
        r'shareModal.*?(?=\s|$)',
        r'principais notícias do Brasil e do mundo.*?(?=\s|$)',
        r'salvos em Minha Folha.*?(?=\s|$)',
        r'Acesse os artigos.*?(?=\s|$)',
        r'àrea personalizada.*?(?=\s|$)',
        r'por dia para dar de presente.*?(?=\s|$)',
        r'Recurso exclusivo.*?(?=\s|$)',
        r'seguido na Minha.*?(?=\s|$)',
        r' slug \+ ".*?(?=\s|$)',
        r'shareModal\(\).*?(?=\s|$)',
        r'window\._.*?(?=\s|$)',
        r'collapsed away.*?(?=\s|$)',
        r'apsed away.*?(?=\s|$)',
        r'apsed away.*?(?=\s|$)',
        r'apsed away.*?(?=\s|$)',
        r'apsed away.*?(?=\s|$)',
        r'apsed away.*?(?=\s|$)',
        r'apsed away.*?(?=\s|$)',
    ]
    
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remover The post... appeared first on...
    text = re.sub(r'The post\s+.*?appeared first on\s+\w+\s*\.?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Cr[eé]dito:\s*.*?\n?', '', text)
    text = re.sub(r'Fonte:\s*.*?\n?', '', text)
    text = re.sub(r'Foto:\s*.*?\n?', '', text)
    text = re.sub(r'Divulgação\s*/?\s*\w+', '', text)
    text = re.sub(r'\d{2}/\d{2}/\d{4}\s+\d{2}h\d{2}\s+Atualizado.*?(?=\s|$)', '', text)
    text = re.sub(r'\d+ (segundo|minuto|hora|dia|semana|mês|ano)s? atrás.*?(?=\s|$)', '', text)
    
    text = text.replace('?', '').replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remover se muito curto ou se é só ruído
    if len(text) < 50:
        return ""
    
    # Verificar se o texto é majoritariamente ruído
    noise_words = ['assunto seguido', 'minha folha', 'acesse os', 'gostaria de receber', 
                   'principais notícias', 'slug', 'sharemodal', 'window._', 'collapsed away']
    text_lower = text.lower()
    noise_count = sum(1 for w in noise_words if w in text_lower)
    if noise_count >= 2:
        return ""
    
    return text


class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script = False
        self.in_style = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.in_script = True
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.in_script = False
    def handle_data(self, data):
        if not self.in_script:
            self.text.append(data)
    def get_text(self):
        return ' '.join(self.text).strip()

def strip_html(html):
    if not html:
        return ""
    s = HTMLStripper()
    try:
        s.feed(html)
    except:
        pass
    return clean_text(s.get_text())


# ─── RSS ─────────────────────────────────────────────────────────────────────
def fetch_rss(url):
    items = []
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
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
                    'description': description,
                    'url': link
                })
    except Exception as e:
        print(f"  Erro RSS: {e}")
    return items


def is_financial_news(news, category=None):
    """Verifica se a notícia é relevante para a categoria."""
    text = (news['title'] + ' ' + news.get('description', '')).lower()
    
    # Excluir sempre
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return False
    
    # Se tem categoria específica, verificar palavras-chave dessa categoria
    if category and category in CATEGORY_KEYWORDS:
        for kw in CATEGORY_KEYWORDS[category]:
            if kw in text:
                return True
        return False
    
    # Caso geral: verificar todas as categorias
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return True
    
    return False


def collect_news():
    """Coleta notícias categorizadas e busca conteúdo completo."""
    print("[NEWS] Coletando noticias por categoria...")
    categorized_news = {
        "economia": [],
        "rh": [],
        "tecnologia": [],
    }
    
    for category, feeds in RSS_FEEDS.items():
        print(f"\n  [{category.upper()}]")
        for name, url in feeds:
            print(f"    {name}...")
            items = fetch_rss(url)
            relevant = [n for n in items if is_financial_news(n, category)]
            for n in relevant:
                n['source'] = name
                n['category'] = category
            categorized_news[category].extend(relevant)
            print(f"      {len(relevant)} relevantes de {len(items)}")
    
    # Remover duplicatas dentro de cada categoria
    for category in categorized_news:
        seen = set()
        unique = []
        for n in categorized_news[category]:
            h = hashlib.md5(n['title'].encode()).hexdigest()[:10]
            if h not in seen:
                seen.add(h)
                unique.append(n)
        categorized_news[category] = unique
    
    total = sum(len(v) for v in categorized_news.values())
    print(f"\n  Total: {total} noticias categorizadas")
    
    # Buscar conteúdo completo dos artigos mais importantes
    print("\n[FETCH] Buscando artigos inteiros...")
    all_news = []
    for category, news_list in categorized_news.items():
        # Pegar até 5 por categoria
        for i, news in enumerate(news_list[:5]):
            print(f"  [{category}] [{i+1}/5] {news['title'][:50]}...")
            content = fetch_article_content(news['url'])
            if content and len(content) > 100:
                news['full_content'] = content
                print(f"    OK ({len(content)} chars)")
            else:
                news['full_content'] = news.get('description', '')
                print(f"    Fallback para descricao")
            all_news.append(news)
    
    return categorized_news, all_news


# ─── Geração de Resumos ─────────────────────────────────────────────────────
def extract_key_sentences(text, num=3):
    """Extrai frases-chave de um texto de forma mais inteligente."""
    if not text:
        return []
    
    # Padrões de ruído para remover antes de processar
    noise_patterns = [
        r'Gostaria de receber.*?(?=\s|$)',
        r'Acesse seus artigos.*?(?=\s|$)',
        r'Você tem \d+ acessos.*?(?=\s|$)',
        r'Assinantes podem.*?(?=\s|$)',
        r'Tem alguma sugestão.*?(?=\s|$)',
        r'Envie para o.*?(?=\s|$)',
        r'Leia a íntegra.*?(?=\s|$)',
        r'\(Leia a íntegra.*?\)',
        r'Canal do YouTube.*?(?=\s|$)',
        r'(\?|&)utm_.*',
        r'Assine a newsletter.*?(?=\s|$)',
        r'Receba por e-mail.*?(?=\s|$)',
        r'Outras notícias.*?(?=\s|$)',
        r'Veja também.*?(?=\s|$)',
        r'collapsed away.*?(?=\s|$)',
        r'\.html.*?(?=\s|$)',
        r'shareModal.*?(?=\s|$)',
        r'principais notícias do Brasil e do mundo.*?(?=\s|$)',
        r'salvos em Minha Folha.*?(?=\s|$)',
        r'Acesse os artigos.*?(?=\s|$)',
        r'àrea personalizada.*?(?=\s|$)',
        r'por dia para dar de presente.*?(?=\s|$)',
        r'Recurso exclusivo.*?(?=\s|$)',
        r'seguido na Minha.*?(?=\s|$)',
    ]
    
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Limpar ruídos
    text = re.sub(r'\d{2}/\d{2}/\d{4}\s+\d{2}h\d{2}\s+Atualizado.*?atrás\.?\s*', '', text)
    text = re.sub(r'Tá ouvindo.*?\?\s*', '', text)
    text = re.sub(r'Inacreditável.*?\.\s*', '', text)
    text = re.sub(r'São fogos.*?\.\s*', '', text)
    text = re.sub(r'Depois de \d+ sessões.*?\.\s*', '', text)
    text = re.sub(r'Crédito:\s*.*?\n', '', text)
    text = re.sub(r'Fonte:\s*.*?\n', '', text)
    text = re.sub(r'Foto:\s*.*?\n', '', text)
    text = re.sub(r'Divulgação.*?\n', '', text)
    text = re.sub(r'\?\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Verificar se o texto é majoritariamente ruído
    noise_words = ['assunto seguido', 'minha folha', 'acesse os', 'gostaria de receber', 
                   'principais notícias', 'slug', 'sharemodal', 'window._', 'collapsed away']
    text_lower = text.lower()
    noise_count = sum(1 for w in noise_words if w in text_lower)
    if noise_count >= 2:
        return []
    
    # Split em frases
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filtrar frases boas - mais permissivo para content mais completo
    good = []
    for s in sentences:
        s = s.strip()
        if len(s) > 50 and len(s) < 350:
            low = s.lower()
            # Filtrar frases que são ruído
            if not any(x in low for x in ['clique', 'leia mais', 'assine', 'foto:', 'crédito:', 
                                           'atualizado', 'segundos atrás', 'minutos atrás',
                                           'são fogos', 'depois de', 'incrível', 'compartilhe',
                                           'assine nossa', 'newsletter', 'グループ',
                                           'acesse seus', 'gostaria de receber', 'envie para',
                                           'tem alguma sugestão', 'canal do youtube',
                                           'collapsed away', 'window._', 'sharemodal',
                                           'utm_', 'assinantes podem', 'principais notícias',
                                           'minha folha', 'acesse os artigos']):
                good.append(s)
    
    return good[:num]


def generate_resumo_anterior(categorized_news):
    """Gera resumo narrativo do dia anterior com conteúdo real e profundo."""
    paragraphs = []
    
    data = ONTEM.strftime('%d/%m/%Y')
    paragraphs.append(f'<p>O mercado financeiro no dia {data} apresentou as seguintes movimentações:</p>')
    
    # Processar notícias de economia
    economia_news = categorized_news.get('economia', [])
    count = 0
    for n in economia_news[:5]:
        content = n.get('full_content', n.get('description', ''))
        title = n['title']
        
        sentences = extract_key_sentences(content, 3)
        
        if sentences and len(sentences) >= 2:
            text = ' '.join(sentences[:2])
            if len(text) > 100:
                paragraphs.append(f'<p>{text}</p>')
                count += 1
        elif title and len(title) > 20:
            paragraphs.append(f'<p>{title}.</p>')
            count += 1
        
        if count >= 4:
            break
    
    if len(paragraphs) < 2:
        paragraphs.append('<p>Mercado em dia de avaliação com movimentação moderada.</p>')
    
    return '\n'.join(paragraphs)


def generate_agenda(categorized_news):
    """Gera agenda do dia com notícias de todas as categorias."""
    items = []
    
    fixes = [
        "Mercado financeiro brasileiro abre às 10h (horário de Brasília)",
        "Indicadores econômicos serão divulgados ao longo do dia",
    ]
    
    for i, item in enumerate(fixes, 1):
        items.append(f'<li><strong>{i}.</strong> {item}</li>')
    
    count = len(fixes) + 1
    
    # Adicionar notícias de economia (títulos limpos)
    for n in categorized_news.get('economia', [])[:3]:
        title = clean_text(n['title'])
        if title and len(title) > 20 and len(title) < 150:
            items.append(f'<li><strong>{count}.</strong> {title}</li>')
            count += 1
    
    # Adicionar notícias de RH
    for n in categorized_news.get('rh', [])[:2]:
        title = clean_text(n['title'])
        if title and len(title) > 20 and len(title) < 150:
            items.append(f'<li><strong>{count}.</strong> {title}</li>')
            count += 1
    
    # Adicionar notícias de tecnologia
    for n in categorized_news.get('tecnologia', [])[:2]:
        title = clean_text(n['title'])
        if title and len(title) > 20 and len(title) < 150:
            items.append(f'<li><strong>{count}.</strong> {title}</li>')
            count += 1
    
    return '<ul>\n' + '\n'.join(items) + '\n</ul>'


def generate_resumo(categorized_news):
    """Gera resumo narrativo do dia com conteúdo profundo e seções temáticas."""
    paragraphs = []
    
    data_extenso = f"{HOJE.day} de {MESES_PT[HOJE.month]} de {HOJE.year}"
    paragraphs.append(f'<p>Bom dia! Hoje é {data_extenso}. Veja o que está movimentando o mercado financeiro e os principais setores.</p>')
    
    # ─── ECONOMIA ───
    paragraphs.append('<p><strong>Mercado Financeiro:</strong></p>')
    economia_news = categorized_news.get('economia', [])
    count = 0
    for n in economia_news[:4]:
        content = n.get('full_content', n.get('description', ''))
        sentences = extract_key_sentences(content, 3)
        
        if sentences and len(sentences) >= 2:
            text = ' '.join(sentences[:2])
            if len(text) > 100:
                paragraphs.append(f'<p>{text}</p>')
                count += 1
    
    if count == 0:
        paragraphs.append('<p>Mercado operando com volatilidade moderada, investidores avaliam cenário macroeconômico.</p>')
    
    # ─── RH / NR-1 ───
    rh_news = categorized_news.get('rh', [])
    if rh_news:
        paragraphs.append('<p><strong>RH e Gestão de Pessoas:</strong></p>')
        count = 0
        for n in rh_news[:3]:
            content = n.get('full_content', n.get('description', ''))
            sentences = extract_key_sentences(content, 3)
            
            if sentences and len(sentences) >= 2:
                text = ' '.join(sentences[:2])
                if len(text) > 100:
                    paragraphs.append(f'<p>{text}</p>')
                    count += 1
        
        if count == 0:
            paragraphs.append('<p>Setor de RH acompanha atualizações da NR-1 e novas diretrizes de saúde mental no trabalho.</p>')
    
    # ─── TECNOLOGIA ───
    tech_news = categorized_news.get('tecnologia', [])
    if tech_news:
        paragraphs.append('<p><strong>Tecnologia e Inovação:</strong></p>')
        count = 0
        for n in tech_news[:3]:
            content = n.get('full_content', n.get('description', ''))
            sentences = extract_key_sentences(content, 3)
            
            if sentences and len(sentences) >= 2:
                text = ' '.join(sentences[:2])
                if len(text) > 100:
                    paragraphs.append(f'<p>{text}</p>')
                    count += 1
        
        if count == 0:
            paragraphs.append('<p>Setor tecnológico segue em expansão com foco em IA e transformação digital.</p>')
    
    paragraphs.append('<p>Essas são as principais notícias do dia. Fique atento para mais atualizações ao longo do dia.</p>')
    
    return '\n'.join(paragraphs)


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  OnzeNews — Scraper v6 (Categorias + Resumos Profundos)")
    print("=" * 50)
    
    categorized_news, all_news = collect_news()
    
    total = sum(len(v) for v in categorized_news.values())
    if total == 0:
        print("[WARN] Nenhuma noticia coletada!")
        return 1
    
    print(f"\n[WRITE] Gerando resumos profundos...")
    
    resumo_anterior = generate_resumo_anterior(categorized_news)
    agenda = generate_agenda(categorized_news)
    resumo = generate_resumo(categorized_news)
    
    (OUTPUT_DIR / "secao_resumo_anterior.html").write_text(resumo_anterior, encoding='utf-8')
    (OUTPUT_DIR / "secao_agenda.html").write_text(agenda, encoding='utf-8')
    (OUTPUT_DIR / "secao_resumo_dia.html").write_text(resumo, encoding='utf-8')
    
    print(f"  [OK] resumo_anterior ({len(resumo_anterior)} chars)")
    print(f"  [OK] agenda ({len(agenda)} chars)")
    print(f"  [OK] resumo_dia ({len(resumo)} chars)")
    
    # Estatísticas por categoria
    print("\n[STATS] Resumo por categoria:")
    for cat, news_list in categorized_news.items():
        print(f"  {cat}: {len(news_list)} noticias")
    
    print("\n[DONE] Concluido!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
