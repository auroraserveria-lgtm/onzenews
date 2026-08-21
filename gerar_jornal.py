#!/usr/bin/env python3
"""
OnzeNews v2 — Gerador de Jornal Financeiro Diario
Layout estilo jornal impresso + podcast com voz natural
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# ─── Configuracao ────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

HOJE = datetime.now()

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "marco", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
}
DIAS_SEMANA = {
    0: "Segunda-feira", 1: "Terca-feira", 2: "Quarta-feira",
    3: "Quinta-feira", 4: "Sexta-feira", 5: "Sabado", 6: "Domingo"
}

DATA_EXTENSO = f"{HOJE.day} de {MESES_PT[HOJE.month]} de {HOJE.year}"
DIA_SEMANA = DIAS_SEMANA[HOJE.weekday()]

# ─── Vozes Edge TTS ──────────────────────────────────────────────────────────
VOZ_AURORA = "pt-BR-ThalitaMultilingualNeural"   # Feminina, natural
VOZ_RICARDO = "pt-BR-AntonioNeural"              # Masculino, natural

# Parametros de voz para pronuncia mais natural
VOZ_PARAMS = {
    "Aurora": {"rate": "-5%", "pitch": "+2Hz"},    # Feminina: um pouco mais rapida, tom levemente mais agudo
    "Ricardo": {"rate": "-8%", "pitch": "-2Hz"}     # Masculino: um pouco mais lento, tom levemente mais grave
}


# ─── Gerador de Script Conversacional ────────────────────────────────────────
def extrair_topicos(html: str, max_topicos: int = 5) -> list:
    """Extrai topicos principais de uma secao HTML (remove tags, pega frases-chave)."""
    import re
    clean = re.sub('<[^<]+?>', ' ', html)
    clean = re.sub('\\s+', ' ', clean).strip()
    if not clean:
        return []
    frases = [f.strip() for f in re.split(r'[.!;]', clean) if len(f.strip()) > 30]
    return frases[:max_topicos]


def gerar_script_conversacional(resumo_anterior: str, agenda_dia: str, resumo_dia: str) -> str:
    """Gera um script de conversa JSON entre Aurora (apresentadora) e Ricardo (analista).
    O conteudo e dinamico, baseado nas noticias reais coletadas."""
    import json

    topicos_ra = extrair_topicos(resumo_anterior, 5)
    topicos_ag = extrair_topicos(agenda_dia, 4)
    topicos_rd = extrair_topicos(resumo_dia, 5)

    script = []

    # --- ABERTURA ---
    script.append({"s": "Aurora", "t": f"Olá! Sejam muito bem-vindos ao OnzeNews Áudio, o podcast do nosso informativo financeiro diário. Hoje é {DIA_SEMANA}, {DATA_EXTENSO}. Eu sou a Aurora e estou aqui com o Ricardo, nosso analista de mercados. Ricardo, bom dia!"})
    script.append({"s": "Ricardo", "t": "Bom dia, Aurora! Obrigado pelo convite. Temos bastante coisa para tratar hoje, o mercado está bem movimentado."})

    # --- RESUMO DO DIA ANTERIOR ---
    if topicos_ra:
        script.append({"s": "Aurora", "t": "Vamos começar pelo que aconteceu ontem. Ricardo, quais foram os principais acontecimentos?"})
        for i, topico in enumerate(topicos_ra[:3]):
            if i == 0:
                script.append({"s": "Ricardo", "t": f"Olha, {topico.strip().rstrip('.')}. Esse foi um dos pontos que mais chamou atenção dos investidores."})
            elif i == 1:
                script.append({"s": "Aurora", "t": "E tem mais alguma notícia importante de ontem?"})
                script.append({"s": "Ricardo", "t": f"Sim! {topico.strip().rstrip('.')}. Isso também pesou no humor do mercado."})
            else:
                script.append({"s": "Aurora", "t": "E no setor de risco?"})
                script.append({"s": "Ricardo", "t": f"Também vale destacar que {topico.strip().rstrip('.')}."})
    else:
        script.append({"s": "Aurora", "t": "Vamos começar pelo resumo de ontem. Ricardo, o que destacou?"})
        script.append({"s": "Ricardo", "t": f"Ontem tivemos um dia movimentado. {resumo_anterior[:200].strip() if resumo_anterior else 'O mercado seguiu o tom global com movimentação moderada'}."})

    # --- AGENDA DO DIA ---
    if topicos_ag:
        script.append({"s": "Aurora", "t": "Agora vamos falar sobre a agenda de hoje. O que os investidores devem acompanhar?"})
        for i, topico in enumerate(topicos_ag[:3]):
            if i == 0:
                script.append({"s": "Ricardo", "t": f"O grande destaque de hoje é: {topico.strip().rstrip('.')}. Isso pode mover bastante os mercados."})
            elif i == 1:
                script.append({"s": "Aurora", "t": "E aqui no Brasil?"})
                script.append({"s": "Ricardo", "t": f"Aqui no Brasil, {topico.strip().rstrip('.')}."})
            else:
                script.append({"s": "Aurora", "t": "E no cenário internacional?"})
                script.append({"s": "Ricardo", "t": f"No cenário internacional, {topico.strip().rstrip('.')}."})
    else:
        script.append({"s": "Aurora", "t": "E a agenda de hoje, o que temos?"})
        script.append({"s": "Ricardo", "t": f"A agenda de hoje traz alguns eventos importantes. {agenda_dia[:200].strip() if agenda_dia else 'Investidores devem ficar atentos aos indicadores do dia'}."})

    # --- RESUMO DO DIA ATUAL ---
    if topicos_rd:
        script.append({"s": "Aurora", "t": "Agora vamos ao resumo do dia de hoje. Ricardo, o que está acontecendo agora?"})
        for i, topico in enumerate(topicos_rd[:3]):
            if i == 0:
                script.append({"s": "Ricardo", "t": f"O mercado está reagindo assim: {topico.strip().rstrip('.')}. Esse é o quadro geral da sessão de hoje."})
            elif i == 1:
                script.append({"s": "Aurora", "t": "E qual foi o impacto disso?"})
                script.append({"s": "Ricardo", "t": f"Na prática, {topico.strip().rstrip('.')}. Os investidores estão processando essas informações."})
            else:
                script.append({"s": "Aurora", "t": "E mais alguma movimentação relevante?"})
                script.append({"s": "Ricardo", "t": f"Também vale notar que {topico.strip().rstrip('.')}."})
    else:
        script.append({"s": "Aurora", "t": "E o resumo do dia, como está?"})
        script.append({"s": "Ricardo", "t": f"Por enquanto, {resumo_dia[:200].strip() if resumo_dia else 'o mercado segue em aberto com expectativa'}."})

    # --- ENCERRAMENTO ---
    script.append({"s": "Aurora", "t": "Ricardo, obrigada pela análise completa! Para nossos ouvintes que quiserem acompanhar as atualizações, o jornal completo está disponível em nosso site. E lembrando que sempre atualizamos quando há notícias extraordinárias."})
    script.append({"s": "Ricardo", "t": "É isso mesmo, Aurora. Fiquem atentos! O mercado financeiro não para e nós também não. Um abraço e até a próxima edição!"})
    script.append({"s": "Aurora", "t": f"Um abraço a todos! O OnzeNews Áudio volta amanhã com mais um resumo completo do mercado. Bom descanso a todos e bons investimentos!"})

    return json.dumps(script, ensure_ascii=False)


# ─── Gerador de Audio do Podcast ─────────────────────────────────────────────
async def gerar_audio_podcast(script_json: str) -> tuple:
    """Gera arquivos de audio para cada trecho do podcast usando Edge TTS.
    Retorna (manifesto_json, duracao_total_segundos).
    """
    import asyncio
    import json
    import edge_tts
    from pathlib import Path

    script = json.loads(script_json)
    podcast_dir = OUTPUT_DIR / "podcast"
    podcast_dir.mkdir(exist_ok=True)

    manifesto = []
    duracao_total = 0.0

    for i, item in enumerate(script):
        speaker = item["s"]
        texto = item["t"]
        voz = VOZ_AURORA if speaker == "Aurora" else VOZ_RICARDO
        params = VOZ_PARAMS.get(speaker, {"rate": "+0%", "pitch": "+0Hz"})

        arquivo_nome = f"seg_{i:03d}.mp3"
        arquivo_path = podcast_dir / arquivo_nome

        # Gera o audio com parametros de pronuncia
        communicate = edge_tts.Communicate(
            texto, 
            voz, 
            rate=params["rate"],
            pitch=params["pitch"]
        )
        await communicate.save(str(arquivo_path))

        # Estima duracao (aprox 150 palavras/min)
        palavras = len(texto.split())
        duracao_estimada = (palavras / 150) * 60
        duracao_total += duracao_estimada + 0.5  # +0.5s de pausa

        manifesto.append({
            "speaker": speaker,
            "text": texto,
            "file": f"podcast/{arquivo_nome}",
            "duration": round(duracao_estimada, 1)
        })

        print(f"  [AUDIO] {speaker} - trecho {i+1}/{len(script)}")

    # Salva o manifesto
    manifesto_path = podcast_dir / "manifesto.json"
    manifesto_path.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  [AUDIO] Total: {len(script)} trechos gerados")
    return json.dumps(manifesto, ensure_ascii=False), round(duracao_total, 0)


# ─── Template HTML — Jornal ──────────────────────────────────────────────────
def gerar_html(resumo_anterior: str, agenda_dia: str, resumo_dia: str) -> str:
    # Gera o script conversacional do podcast
    podcast_script = gerar_script_conversacional(resumo_anterior, agenda_dia, resumo_dia)
    
    # Gera o audio do podcast (async)
    import asyncio
    manifesto_json, duracao_total = asyncio.run(gerar_audio_podcast(podcast_script))
    
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OnzeNews — {HOJE.strftime('%d/%m/%Y')}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Source+Sans+3:wght@300;400;600;700&family=Merriweather:wght@300;400;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --azul-royal: #003366;
      --azul-escuro: #001a33;
      --azul-medio: #0055aa;
      --azul-bebe: #d4eaf7;
      --azul-claro: #e8f4f8;
      --dourado: #c9a84c;
      --vermelho: #b71c1c;
      --texto: #1a1a2e;
      --texto-secundario: #4a5568;
      --borda: #e2e8f0;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: 'Merriweather', Georgia, 'Times New Roman', serif;
      background: #f5f0e8;
      color: var(--texto);
      line-height: 1.7;
    }}

    .jornal {{
      max-width: 1100px;
      margin: 0 auto;
      background: #fff;
      box-shadow: 0 0 40px rgba(0,0,0,0.15);
    }}

    /* ═══ MASTRONE ═══ */
    .mastrone {{
      background: var(--azul-royal);
      color: #fff;
      padding: 0;
      position: relative;
      overflow: hidden;
    }}

    .mastrone-topo {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 30px;
      border-bottom: 1px solid rgba(255,255,255,0.15);
      font-family: 'Source Sans 3', sans-serif;
      font-size: 12px;
      opacity: 0.8;
    }}

    .mastrone-principal {{
      text-align: center;
      padding: 30px 30px 25px;
    }}

    .mastrone-titulo {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 72px;
      font-weight: 900;
      letter-spacing: 6px;
      text-transform: uppercase;
      line-height: 1;
      margin-bottom: 6px;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }}

    .mastrone-titulo span {{
      color: var(--dourado);
    }}

    .mastrone-sub {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 14px;
      font-weight: 300;
      letter-spacing: 4px;
      text-transform: uppercase;
      opacity: 0.75;
      margin-bottom: 15px;
    }}

    .mastrone-linha {{
      height: 3px;
      background: linear-gradient(90deg, transparent, var(--dourado), transparent);
      margin: 0 auto;
      width: 60%;
    }}

    .mastrone-data {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      padding: 10px 30px;
      text-align: center;
      opacity: 0.7;
      letter-spacing: 1px;
    }}

    /* ═══ BARRA DE MERCADO ═══ */
    .barra-mercado {{
      background: var(--azul-escuro);
      color: #fff;
      padding: 10px 30px;
      display: flex;
      justify-content: center;
      gap: 30px;
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      border-bottom: 2px solid var(--dourado);
    }}

    .item-mercado {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .item-mercado .nome {{
      opacity: 0.7;
      font-weight: 400;
    }}

    .item-mercado .valor {{
      font-weight: 700;
    }}

    .item-mercado .variacao {{
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 3px;
      font-weight: 600;
    }}

    .variacao.up {{ background: rgba(46, 125, 50, 0.3); color: #81c784; }}
    .variacao.down {{ background: rgba(198, 40, 40, 0.3); color: #ef9a9a; }}

    /* ═══ PLAYER ═══ */
    .player-bar {{
      background: linear-gradient(135deg, var(--azul-medio), var(--azul-royal));
      padding: 14px 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 15px;
      border-bottom: 1px solid var(--borda);
    }}

    .btn-player {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: rgba(255,255,255,0.15);
      color: #fff;
      border: 1px solid rgba(255,255,255,0.3);
      padding: 10px 24px;
      border-radius: 30px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s ease;
      font-family: 'Source Sans 3', sans-serif;
      backdrop-filter: blur(5px);
    }}

    .btn-player:hover {{
      background: rgba(255,255,255,0.25);
      transform: scale(1.03);
    }}

    .btn-player .icone {{ font-size: 18px; }}

    .btn-player.tocando {{
      background: var(--vermelho);
      border-color: var(--vermelho);
    }}

    .player-info {{
      color: rgba(255,255,255,0.8);
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
    }}

    /* ═══ CONTEUDO ═══ */
    .conteudo {{
      padding: 30px;
    }}

    /* ═══ COLUNAS ═══ */
    .grid-2col {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 30px;
      margin-bottom: 30px;
    }}

    .grid-3col {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 25px;
      margin-bottom: 30px;
    }}

    .coluna-principal {{ min-width: 0; }}
    .coluna-lateral {{ min-width: 0; }}

    /* ═══ SECOES ═══ */
    .secao {{
      margin-bottom: 28px;
      page-break-inside: avoid;
    }}

    .secao-cabecalho {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      padding-bottom: 10px;
      border-bottom: 3px solid var(--azul-royal);
    }}

    .secao-icone {{
      width: 36px;
      height: 36px;
      background: var(--azul-royal);
      color: #fff;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
    }}

    .secao-titulo {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 22px;
      font-weight: 700;
      color: var(--azul-royal);
      text-transform: uppercase;
      letter-spacing: 1px;
    }}

    .secao-subtitulo {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 12px;
      color: var(--texto-secundario);
      text-transform: uppercase;
      letter-spacing: 2px;
    }}

    .secao-texto {{
      font-size: 14.5px;
      line-height: 1.8;
      color: var(--texto);
      text-align: justify;
      hyphens: auto;
    }}

    .secao-texto p {{
      margin-bottom: 14px;
      text-indent: 2em;
    }}

    .secao-texto p:first-child {{
      text-indent: 0;
    }}

    .secao-texto p:first-child::first-letter {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 3.2em;
      float: left;
      line-height: 0.8;
      margin: 4px 10px 0 0;
      color: var(--azul-royal);
      font-weight: 700;
    }}

    /* ═══ AGENDA ═══ */
    .agenda-lista {{
      list-style: none;
      padding: 0;
    }}

    .agenda-lista li {{
      padding: 10px 0 10px 32px;
      position: relative;
      border-bottom: 1px solid var(--borda);
      font-size: 13.5px;
      font-family: 'Source Sans 3', sans-serif;
      line-height: 1.5;
    }}

    .agenda-lista li:last-child {{ border-bottom: none; }}

    .agenda-lista li::before {{
      content: attr(data-num);
      position: absolute;
      left: 0;
      top: 10px;
      width: 22px;
      height: 22px;
      background: var(--azul-royal);
      color: #fff;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 700;
    }}

    .agenda-hora {{
      font-weight: 700;
      color: var(--azul-royal);
    }}

    /* ═══ MANCHETE DESTAQUE ═══ */
    .manchete-destaque {{
      background: var(--azul-claro);
      border-left: 5px solid var(--azul-royal);
      padding: 20px 24px;
      margin-bottom: 25px;
      border-radius: 0 8px 8px 0;
    }}

    .manchete-destaque h2 {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 26px;
      font-weight: 900;
      color: var(--azul-royal);
      line-height: 1.2;
      margin-bottom: 8px;
    }}

    .manchete-destaque .chapeu {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 2px;
      color: var(--vermelho);
      font-weight: 700;
      margin-bottom: 6px;
    }}

    /* ═══ LATERAL ═══ */
    .lateral-box {{
      background: var(--azul-claro);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
    }}

    .lateral-titulo {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 16px;
      font-weight: 700;
      color: var(--azul-royal);
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 2px solid var(--dourado);
    }}

    .lateral-item {{
      padding: 8px 0;
      border-bottom: 1px solid rgba(0,51,102,0.1);
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      line-height: 1.4;
    }}

    .lateral-item:last-child {{ border-bottom: none; }}

    .lateral-item strong {{
      color: var(--azul-royal);
      display: block;
      margin-bottom: 2px;
    }}

    /* ═══ DIVISORIA ═══ */
    .divisoria {{
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--borda), transparent);
      margin: 25px 0;
    }}

    .divisoria-dupla {{
      height: 4px;
      border-top: 1px solid var(--borda);
      border-bottom: 1px solid var(--borda);
      margin: 25px 0;
    }}

    /* ═══ RODAPE ═══ */
    .rodape {{
      background: var(--azul-escuro);
      color: rgba(255,255,255,0.6);
      padding: 20px 30px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: 'Source Sans 3', sans-serif;
      font-size: 11px;
    }}

    .rodape strong {{ color: var(--dourado); }}

    /* ═══ EXTRA ═══ */
    .extra-banner {{
      background: var(--vermelho);
      color: #fff;
      text-align: center;
      padding: 14px;
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 4px;
    }}

    /* ═══ PODCAST PLAYER ═══ */
    .podcast-section {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      border-radius: 12px;
      margin: 0 30px 30px;
      padding: 24px;
      color: #fff;
    }}

    .podcast-header {{
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
    }}

    .podcast-cover {{
      width: 64px;
      height: 64px;
      background: linear-gradient(135deg, var(--azul-royal), var(--azul-medio));
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }}

    .podcast-icon {{ font-size: 28px; }}

    .podcast-info {{ flex: 1; }}

    .podcast-label {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 11px;
      letter-spacing: 3px;
      text-transform: uppercase;
      color: var(--dourado);
      margin-bottom: 4px;
    }}

    .podcast-title {{
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 20px;
      font-weight: 700;
    }}

    .podcast-meta {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 12px;
      opacity: 0.6;
      margin-top: 2px;
    }}

    .podcast-duration {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 14px;
      color: var(--dourado);
      font-weight: 600;
    }}

    .podcast-player {{
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
    }}

    .podcast-btn-play {{
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: var(--dourado);
      color: #1a1a2e;
      border: none;
      font-size: 18px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s;
      flex-shrink: 0;
    }}

    .podcast-btn-play:hover {{
      transform: scale(1.1);
      background: #d4b85a;
    }}

    .podcast-btn-play.playing {{
      background: var(--vermelho);
      color: #fff;
      animation: pulse 1.5s infinite;
    }}

    @keyframes pulse {{
      0%, 100% {{ box-shadow: 0 0 0 0 rgba(183, 28, 28, 0.4); }}
      50% {{ box-shadow: 0 0 0 10px rgba(183, 28, 28, 0); }}
    }}

    .podcast-progress-area {{
      flex: 1;
      height: 40px;
      display: flex;
      align-items: center;
      cursor: pointer;
    }}

    .podcast-progress-bar {{
      width: 100%;
      height: 4px;
      background: rgba(255,255,255,0.15);
      border-radius: 2px;
      position: relative;
    }}

    .podcast-progress-fill {{
      height: 100%;
      background: var(--dourado);
      border-radius: 2px;
      width: 0%;
      transition: width 0.3s;
    }}

    .podcast-progress-thumb {{
      width: 12px;
      height: 12px;
      background: var(--dourado);
      border-radius: 50%;
      position: absolute;
      top: 50%;
      transform: translate(-50%, -50%);
      left: 0%;
      transition: left 0.3s;
      display: none;
    }}

    .podcast-progress-area:hover .podcast-progress-thumb {{
      display: block;
    }}

    .podcast-time {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 12px;
      color: rgba(255,255,255,0.5);
      min-width: 90px;
      text-align: right;
    }}

    .podcast-speakers {{
      display: flex;
      justify-content: center;
      gap: 40px;
      margin-bottom: 20px;
      padding: 16px 0;
      border-top: 1px solid rgba(255,255,255,0.08);
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }}

    .podcast-speaker {{
      text-align: center;
      opacity: 0.4;
      transition: all 0.3s;
    }}

    .podcast-speaker.active {{
      opacity: 1;
    }}

    .speaker-avatar {{
      width: 56px;
      height: 56px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 22px;
      font-weight: 700;
      margin: 0 auto 8px;
      transition: all 0.3s;
    }}

    .speaker-avatar.aurora {{
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: #fff;
    }}

    .speaker-avatar.ricardo {{
      background: linear-gradient(135deg, #f093fb, #f5576c);
      color: #fff;
    }}

    .podcast-speaker.active .speaker-avatar {{
      transform: scale(1.1);
      box-shadow: 0 0 20px rgba(201, 168, 76, 0.4);
    }}

    .speaker-name {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 14px;
      font-weight: 600;
    }}

    .speaker-role {{
      font-family: 'Source Sans 3', sans-serif;
      font-size: 11px;
      opacity: 0.6;
    }}

    .podcast-transcript {{
      max-height: 200px;
      overflow-y: auto;
      padding: 16px;
      background: rgba(0,0,0,0.2);
      border-radius: 8px;
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      line-height: 1.6;
    }}

    .podcast-transcript::-webkit-scrollbar {{
      width: 6px;
    }}

    .podcast-transcript::-webkit-scrollbar-track {{
      background: rgba(255,255,255,0.05);
    }}

    .podcast-transcript::-webkit-scrollbar-thumb {{
      background: rgba(255,255,255,0.15);
      border-radius: 3px;
    }}

    .transcript-line {{
      padding: 6px 0;
      border-bottom: 1px solid rgba(255,255,255,0.05);
    }}

    .transcript-line.aurora strong {{ color: #667eea; }}
    .transcript-line.ricardo strong {{ color: #f5576c; }}
    .transcript-line.info {{ color: rgba(255,255,255,0.4); font-style: italic; text-align: center; }}

    /* ═══ RESPONSIVO ═══ */
    @media (max-width: 768px) {{
      .mastrone-titulo {{ font-size: 36px; letter-spacing: 2px; }}
      .mastrone-sub {{ font-size: 11px; letter-spacing: 2px; }}
      .mastrone-data {{ font-size: 11px; padding: 8px 15px; }}
      .grid-2col {{ grid-template-columns: 1fr; gap: 20px; }}
      .grid-3col {{ grid-template-columns: 1fr; }}
      .barra-mercado {{ flex-wrap: wrap; gap: 10px; padding: 8px 15px; font-size: 11px; }}
      .conteudo {{ padding: 15px; }}
      .secao-titulo {{ font-size: 18px; }}
      .secao-texto {{ font-size: 13.5px; }}
      .manchete-destaque h2 {{ font-size: 20px; }}
      .lateral-box {{ padding: 15px; }}

      /* Podcast responsivo */
      .podcast-section {{ margin: 0 15px 20px; padding: 16px; }}
      .podcast-header {{ flex-wrap: wrap; gap: 12px; }}
      .podcast-cover {{ width: 50px; height: 50px; }}
      .podcast-icon {{ font-size: 22px; }}
      .podcast-title {{ font-size: 16px; }}
      .podcast-player {{ gap: 10px; }}
      .podcast-btn-play {{ width: 42px; height: 42px; font-size: 16px; }}
      .podcast-time {{ font-size: 11px; min-width: 70px; }}
      .podcast-speakers {{ gap: 25px; }}
      .speaker-avatar {{ width: 46px; height: 46px; font-size: 18px; }}
      .podcast-transcript {{ max-height: 150px; font-size: 12px; padding: 12px; }}
    }}

    @media (max-width: 480px) {{
      .mastrone-titulo {{ font-size: 28px; letter-spacing: 1px; }}
      .mastrone-sub {{ font-size: 10px; }}
      .barra-mercado {{ font-size: 10px; gap: 8px; }}
      .item-mercado {{ gap: 4px; }}
      .secao-cabecalho {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
      .podcast-section {{ margin: 0 10px 15px; padding: 12px; }}
      .podcast-speakers {{ gap: 20px; }}
      .speaker-avatar {{ width: 40px; height: 40px; font-size: 16px; }}
      .speaker-name {{ font-size: 12px; }}
      .podcast-transcript {{ max-height: 120px; font-size: 11px; }}
    }}

    @media print {{
      body {{ background: #fff; }}
      .jornal {{ box-shadow: none; }}
      .podcast-section {{ display: none; }}
    }}
  </style>
</head>
<body>

<div class="jornal">

  <!-- MASTRONE -->
  <header class="mastrone">
    <div class="mastrone-principal">
      <div class="mastrone-sub">Informativo Financeiro Diario</div>
      <h1 class="mastrone-titulo">ONZE<span>NEWS</span></h1>
      <div class="mastrone-linha"></div>
    </div>
    <div class="mastrone-data">{DIA_SEMANA}, {DATA_EXTENSO} | Horario de Brasilia</div>
  </header>

  <!-- BARRA DE MERCADO -->
  <div class="barra-mercado">
    <div class="item-mercado">
      <span class="nome">Dolar</span>
      <span class="valor">R$ 5,17</span>
      <span class="variacao down">-0,96%</span>
    </div>
    <div class="item-mercado">
      <span class="nome">Euro</span>
      <span class="valor">R$ 6,03</span>
      <span class="variacao down">-0,23%</span>
    </div>
    <div class="item-mercado">
      <span class="nome">Ibovespa</span>
      <span class="valor">169.642 pts</span>
      <span class="variacao up">+1,99%</span>
    </div>
    <div class="item-mercado">
      <span class="nome">Selic</span>
      <span class="valor">15,00%</span>
      <span class="variacao" style="background:rgba(255,255,255,0.1);color:#fff">ao ano</span>
    </div>
  </div>

  <!-- PLAYER DE PODCAST REMOVIDO — USANDO PLAYER CONVERSACIONAL ABAIXO -->

  <!-- CONTEUDO -->
  <div class="conteudo" id="conteudo-jornal">

    <!-- MANCHETE DESTAQUE -->
    <div class="manchete-destaque">
      <div class="chapeu">Editoria Economia</div>
      <h2>Tesouro dos EUA dobra recompra de titulos longos e acalma mercados globais</h2>
    </div>

    <!-- GRID 2 COLUNAS -->
    <div class="grid-2col">

      <!-- COLUNA PRINCIPAL -->
      <div class="coluna-principal">

        <!-- SECAO 1: RESUMO DO DIA ANTERIOR -->
        <div class="secao">
          <div class="secao-cabecalho">
            <div class="secao-icone">&#128197;</div>
            <div>
              <div class="secao-titulo">Resumo do Dia Anterior</div>
              <div class="secao-subtitulo">O que aconteceu ontem</div>
            </div>
          </div>
          <div class="secao-texto">
            {resumo_anterior}
          </div>
        </div>

        <div class="divisoria-dupla"></div>

        <!-- SECAO 3: RESUMO DO DIA -->
        <div class="secao">
          <div class="secao-cabecalho">
            <div class="secao-icone">&#128240;</div>
            <div>
              <div class="secao-titulo">Resumo do Dia</div>
              <div class="secao-subtitulo">Principais noticias de hoje</div>
            </div>
          </div>
          <div class="secao-texto">
            {resumo_dia}
          </div>
        </div>

      </div>

      <!-- COLUNA LATERAL -->
      <div class="coluna-lateral">

        <!-- AGENDA -->
        <div class="lateral-box">
          <div class="lateral-titulo">&#128198; Agenda do Dia</div>
          {agenda_dia}
        </div>

        <!-- FONTES -->
        <div class="lateral-box">
          <div class="lateral-titulo">&#128214; Fontes</div>
          <div class="lateral-item"><strong>UOL Economia</strong>economia.uol.com.br</div>
          <div class="lateral-item"><strong>G1 Economia</strong>g1.globo.com/economia</div>
          <div class="lateral-item"><strong>Valor Economico</strong>valor.globo.com</div>
          <div class="lateral-item"><strong>InfoMoney</strong>infomoney.com.br</div>
        </div>

        <!-- MERCADO AGORA -->
        <div class="lateral-box" style="background: var(--azul-royal); color: #fff;">
          <div class="lateral-titulo" style="color: var(--dourado); border-color: rgba(255,255,255,0.2);">Mercado Agora</div>
          <div class="lateral-item" style="border-color: rgba(255,255,255,0.1); color: rgba(255,255,255,0.9);">
            <strong style="color: var(--dourado);">Petrobras (PETR4)</strong>
            R$ 43,83 (+2,89%)
          </div>
          <div class="lateral-item" style="border-color: rgba(255,255,255,0.1); color: rgba(255,255,255,0.9);">
            <strong style="color: var(--dourado);">Vale (VALE3)</strong>
            R$ 73,68 (+2,98%)
          </div>
          <div class="lateral-item" style="border-color: rgba(255,255,255,0.1); color: rgba(255,255,255,0.9);">
            <strong style="color: var(--dourado);">Itau (ITUB4)</strong>
            R$ 38,52 (+0,86%)
          </div>
          <div class="lateral-item" style="border-color: rgba(255,255,255,0.1); color: rgba(255,255,255,0.9);">
            <strong style="color: var(--dourado);">Bradesco (BBDC4)</strong>
            R$ 16,28 (+0,99%)
          </div>
        </div>

      </div>

    </div>

  </div>

  <!-- RODAPE -->
  <footer class="rodape">
    <span><strong>OnzeNews</strong> — Informativo Financeiro Diario</span>
    <span>Gerado em {HOJE.strftime('%d/%m/%Y as %H:%M')}</span>
  </footer>

</div>

<!-- PODCAST PLAYER — AUDIO REAL -->
<div class="podcast-section" id="podcastSection">
  <div class="podcast-header">
    <div class="podcast-cover">
      <div class="podcast-icon">&#127911;</div>
    </div>
    <div class="podcast-info">
      <div class="podcast-label">PODCAST</div>
      <div class="podcast-title">OnzeNews Audio</div>
      <div class="podcast-meta">{DIA_SEMANA}, {DATA_EXTENSO}</div>
    </div>
    <div class="podcast-duration" id="podcastDuration">--:--</div>
  </div>

  <div class="podcast-player">
    <button class="podcast-btn-play" id="podcastBtnPlay" onclick="podcastToggle()">
      <span id="podcastIconPlay">&#9654;</span>
    </button>
    <div class="podcast-progress-area" id="podcastProgressArea">
      <div class="podcast-progress-bar">
        <div class="podcast-progress-fill" id="podcastProgressFill"></div>
        <div class="podcast-progress-thumb" id="podcastProgressThumb"></div>
      </div>
    </div>
    <div class="podcast-time" id="podcastTime">0:00 / 0:00</div>
  </div>

  <div class="podcast-speakers">
    <div class="podcast-speaker active" id="speakerAurora">
      <div class="speaker-avatar aurora">A</div>
      <div class="speaker-name">Aurora</div>
      <div class="speaker-role">Apresentadora</div>
    </div>
    <div class="podcast-speaker" id="speakerRicardo">
      <div class="speaker-avatar ricardo">R</div>
      <div class="speaker-name">Ricardo</div>
      <div class="speaker-role">Analista</div>
    </div>
  </div>

  <div class="podcast-transcript" id="podcastTranscript">
    <div class="transcript-line info">Clique em Play para ouvir a conversa sobre as noticias de hoje...</div>
  </div>
</div>

<script>
// ═══ PODCAST — AUDIO REAL (Edge TTS) ═══
const podcastManifesto = {manifesto_json};

(function() {{
  let currentIdx = 0;
  let isPlaying = false;
  let audio = new Audio();
  audio.preload = 'auto';

  function formatTime(sec) {{
    if (isNaN(sec)) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
  }}

  // Estima duracao total
  function duracaoTotal() {{
    let total = 0;
    podcastManifesto.forEach(item => {{ total += item.duration + 0.5; }});
    return total;
  }}

  function updateDuration() {{
    document.getElementById('podcastDuration').textContent = formatTime(duracaoTotal());
  }}

  function highlightSpeaker(name) {{
    document.getElementById('speakerAurora').classList.toggle('active', name === 'Aurora');
    document.getElementById('speakerRicardo').classList.toggle('active', name === 'Ricardo');
  }}

  function addTranscriptLine(speaker, text) {{
    const container = document.getElementById('podcastTranscript');
    const line = document.createElement('div');
    line.className = 'transcript-line ' + (speaker === 'Aurora' ? 'aurora' : speaker === 'Ricardo' ? 'ricardo' : 'info');
    if (speaker) {{
      line.innerHTML = '<strong>' + speaker + ':</strong> ' + text;
    }} else {{
      line.textContent = text;
    }}
    container.appendChild(line);
    container.scrollTop = container.scrollHeight;
  }}

  function updateProgress() {{
    if (!audio.duration) return;
    const progresso = ((currentIdx + (audio.currentTime / audio.duration)) / podcastManifesto.length) * 100;
    document.getElementById('podcastProgressFill').style.width = progresso + '%';
    document.getElementById('podcastProgressThumb').style.left = progresso + '%';

    // Tempo atual estimado
    let tempoAtual = 0;
    for (let i = 0; i < currentIdx; i++) {{
      tempoAtual += podcastManifesto[i].duration + 0.5;
    }}
    tempoAtual += audio.currentTime;
    document.getElementById('podcastTime').textContent = formatTime(tempoAtual) + ' / ' + formatTime(duracaoTotal());
  }}

  function playSegment(idx) {{
    if (idx >= podcastManifesto.length) {{
      // Terminou
      isPlaying = false;
      document.getElementById('podcastIconPlay').innerHTML = '&#9654;';
      document.getElementById('podcastBtnPlay').classList.remove('playing');
      highlightSpeaker(null);
      addTranscriptLine(null, '--- Fim do podcast ---');
      return;
    }}

    currentIdx = idx;
    const item = podcastManifesto[currentIdx];

    // Destaca quem esta falando
    highlightSpeaker(item.speaker);

    // Adiciona ao transcript
    addTranscriptLine(item.speaker, item.text);

    // Carrega e toca o audio
    audio.src = item.file;
    audio.load();

    audio.oncanplay = function() {{
      audio.play().catch(e => {{
        console.log('Autoplay bloqueado, aguardando interacao do usuario');
      }});
    }};

    audio.onended = function() {{
      // Pausa natural entre falantes
      setTimeout(() => playSegment(currentIdx + 1), 300);
    }};

    audio.ontimeupdate = updateProgress;
  }}

  // Controles globais
  window.podcastToggle = function() {{
    if (isPlaying && !audio.paused) {{
      audio.pause();
      isPlaying = false;
      document.getElementById('podcastIconPlay').innerHTML = '&#9654;';
      document.getElementById('podcastBtnPlay').classList.remove('playing');
    }} else if (!isPlaying && audio.paused && audio.src) {{
      audio.play();
      isPlaying = true;
      document.getElementById('podcastIconPlay').innerHTML = '&#9646;&#9646;';
      document.getElementById('podcastBtnPlay').classList.add('playing');
    }} else {{
      // Inicia do comeco
      isPlaying = true;
      currentIdx = 0;
      document.getElementById('podcastIconPlay').innerHTML = '&#9646;&#9646;';
      document.getElementById('podcastBtnPlay').classList.add('playing');
      document.getElementById('podcastTranscript').innerHTML = '';
      playSegment(0);
    }}
  }};

  // Seek (clique na barra)
  document.getElementById('podcastProgressArea').addEventListener('click', function(e) {{
    const rect = this.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    const idx = Math.floor(pct * podcastManifesto.length);
    if (idx >= 0 && idx < podcastManifesto.length) {{
      audio.pause();
      playSegment(idx);
      if (!isPlaying) {{
        isPlaying = true;
        document.getElementById('podcastIconPlay').innerHTML = '&#9646;&#9646;';
        document.getElementById('podcastBtnPlay').classList.add('playing');
      }}
    }}
  }});

  // Inicializa
  updateDuration();
}})();
</script>

</body>
</html>"""


# ─── Template HTML — EXTRA ───────────────────────────────────────────────────
def gerar_html_extra(titulo_extra: str, corpo_extra: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>OnzeNews — NOTICIA EXTRAORDINARIA</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Source+Sans+3:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --azul-royal: #003366;
      --dourado: #c9a84c;
      --vermelho: #b71c1c;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Merriweather', Georgia, serif; background: #f5f0e8; }}
    .jornal {{ max-width: 900px; margin: 0 auto; background: #fff; box-shadow: 0 0 40px rgba(0,0,0,0.15); }}
    .extra-banner {{
      background: var(--vermelho); color: #fff; text-align: center;
      padding: 16px; font-family: 'Playfair Display', serif;
      font-size: 20px; font-weight: 700; letter-spacing: 5px;
    }}
    .mastrone {{
      background: var(--azul-royal); color: #fff; text-align: center; padding: 25px;
    }}
    .mastrone h1 {{
      font-family: 'Playfair Display', serif; font-size: 48px; font-weight: 900; letter-spacing: 4px;
    }}
    .mastrone h1 span {{ color: var(--dourado); }}
    .mastrone .data {{ font-size: 13px; opacity: 0.7; margin-top: 8px; font-family: 'Source Sans 3', sans-serif; }}
    .conteudo {{ padding: 30px; }}
    .secao-texto {{ font-size: 14.5px; line-height: 1.8; text-align: justify; }}
    .secao-texto p {{ margin-bottom: 14px; text-indent: 2em; }}
    .secao-texto p:first-child {{ text-indent: 0; }}
    .rodape {{
      background: #001a33; color: rgba(255,255,255,0.6); padding: 16px 30px;
      text-align: center; font-family: 'Source Sans 3', sans-serif; font-size: 11px;
    }}
    .rodape strong {{ color: var(--dourado); }}
  </style>
</head>
<body>
<div class="jornal">
  <div class="extra-banner">&#9888; NOTICIA EXTRAORDINARIA &#9888;</div>
  <div class="mastrone">
    <h1>ONZE<span>NEWS</span></h1>
    <div class="data">{DIA_SEMANA}, {DATA_EXTENSO} — {HOJE.strftime('%H:%M')}</div>
  </div>
  <div class="conteudo">
    <h2 style="font-family:'Playfair Display',serif; font-size:24px; color:var(--azul-royal); margin-bottom:20px;">{titulo_extra}</h2>
    <div class="secao-texto">{corpo_extra}</div>
  </div>
  <div class="rodape">
    <strong>OnzeNews</strong> — Noticia Extraordinaria | Gerado em {HOJE.strftime('%d/%m/%Y as %H:%M')}
  </div>
</div>
</body>
</html>"""


# ─── Conversao HTML -> PDF ────────────────────────────────────────────────────
def html_para_pdf(html_content: str, nome_arquivo: str) -> Path:
    from playwright.sync_api import sync_playwright

    caminho_html = OUTPUT_DIR / f"{nome_arquivo}.html"
    caminho_pdf = OUTPUT_DIR / f"{nome_arquivo}.pdf"

    caminho_html.write_text(html_content, encoding="utf-8")
    print(f"  [OK] HTML salvo: {caminho_html}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.set_content(html_content, wait_until="networkidle")
        page.wait_for_timeout(1000)  # Espera fonts carregarem
        page.pdf(
            path=str(caminho_pdf),
            format="A4",
            margin={"top": "10mm", "right": "12mm", "bottom": "10mm", "left": "12mm"},
            print_background=True
        )
        browser.close()

    print(f"  [OK] PDF salvo:  {caminho_pdf}")
    return caminho_pdf


# ─── Funcoes principais ──────────────────────────────────────────────────────
def atualizar_index(nome_arquivo: str):
    """Atualiza o index.html para redirecionar para o jornal mais recente."""
    index_path = OUTPUT_DIR / "index.html"
    index_html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OnzeNews - Informativo Financeiro</title>
  <meta http-equiv="refresh" content="0;url={nome_arquivo}.html">
  <style>
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #003366;
      color: #fff;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      text-align: center;
    }}
    .box {{
      background: rgba(255,255,255,0.1);
      padding: 40px 60px;
      border-radius: 12px;
      backdrop-filter: blur(10px);
    }}
    h1 {{ font-size: 42px; margin-bottom: 10px; letter-spacing: 3px; }}
    p {{ opacity: 0.8; font-size: 16px; }}
    a {{ color: #7ec8e3; text-decoration: none; font-weight: bold; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>ONZENEWS</h1>
    <p>Informativo Financeiro Diario</p>
    <p>Redirecionando para o jornal mais recente...</p>
    <p><a href='{nome_arquivo}.html'>Clique aqui se nao redirecionar</a></p>
  </div>
</body>
</html>'''
    index_path.write_text(index_html, encoding='utf-8')
    print(f"  [OK] index.html atualizado -> {nome_arquivo}.html")


def gerar_jornal(resumo_anterior: str, agenda_dia: str, resumo_dia: str):
    print(f"\nGerando OnzeNews v2 - {DATA_EXTENSO}...")
    print("=" * 50)

    html = gerar_html(resumo_anterior, agenda_dia, resumo_dia)
    nome = f"OnzeNews_{HOJE.strftime('%Y-%m-%d')}"
    caminho = html_para_pdf(html, nome)

    # Atualizar index.html para redirecionar para o jornal mais recente
    atualizar_index(nome)

    print("=" * 50)
    print(f"[OK] Jornal gerado com sucesso!\n")
    return caminho


def gerar_extra(titulo: str, corpo: str):
    print(f"\nGerando NOTICIA EXTRAORDINARIA...")
    print("=" * 50)

    html = gerar_html_extra(titulo, corpo)
    nome = f"OnzeNews_EXTRA_{HOJE.strftime('%Y-%m-%d_%H-%M')}"
    caminho = html_para_pdf(html, nome)

    print("=" * 50)
    print(f"[OK] Edicao extra gerada com sucesso!\n")
    return caminho


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python gerar_jornal.py diario <resumo_anterior.html> <agenda.html> <resumo.html>")
        print("  python gerar_jornal.py extra <titulo> <corpo.html>")
        sys.exit(1)

    modo = sys.argv[1]

    if modo == "diario":
        if len(sys.argv) < 5:
            print("Erro: modo 'diario' requer 3 arquivos de conteudo.")
            sys.exit(1)
        ra = Path(sys.argv[2]).read_text(encoding="utf-8")
        ag = Path(sys.argv[3]).read_text(encoding="utf-8")
        rd = Path(sys.argv[4]).read_text(encoding="utf-8")
        gerar_jornal(ra, ag, rd)

    elif modo == "extra":
        if len(sys.argv) < 4:
            print("Erro: modo 'extra' requer titulo e arquivo de corpo.")
            sys.exit(1)
        titulo = sys.argv[2]
        corpo = Path(sys.argv[3]).read_text(encoding="utf-8")
        gerar_extra(titulo, corpo)

    else:
        print(f"Modo desconhecido: {modo}")
        sys.exit(1)
