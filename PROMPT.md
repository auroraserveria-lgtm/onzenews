# OnzeNews — Prompt de Geração do Jornal Financeiro

## Visão Geral

O **OnzeNews** é um informativo periódico estilo jornal financeiro, com atualizações diárias e extras conforme a relevância das notícias do mercado financeiro brasileiro e global. O jornal é gerado em **HTML estilizado** e convertido para **PDF**. O HTML preserva um **botão de player** que, ao clicar, lê o conteúdo em voz alta (Web Speech API — estilo podcast).

---

## Identidade Visual

| Elemento | Especificação |
|----------|---------------|
| **Nome do Jornal** | OnzeNews |
| **Títulos das seções** | Letra **branca**, **negrito**, com fundo em **azul marinho** (#003366) |
| **Corpo do texto / relatório** | **Azul bebê** (#B0E0E6) |
| **Fundo geral do jornal** | Branco ou tom claro neutro |
| **Tipografia** | Sans-serif (Arial, Helvetica, Segoe UI) |

---

## Estrutura do Jornal

### 1. Cabeçalho

- Logo/título **OnzeNews** em destaque.
- Data de publicação (ex: "19 de agosto de 2026 — Quart-feira").
- **Botão de Player (Podcast)**: ícone de play ▶️ estilizado. Ao clicar, inicia a leitura em voz alta de todo o conteúdo do jornal usando a Web Speech API (`speechSynthesis`). O botão deve alternar entre play ▶️ e pause ⏸️.

### 2. RESUMO DO DIA ANTERIOR

- **Título**: `RESUMO DO DIA ANTERIOR` (branco, negrito, fundo azul marinho).
- **Conteúdo**: Principais acontecimentos:
  - **Econômico** — Brasil e global.
  - **Político** — decisões, leis, eleições, cambios de governo.
  - **Empresas do setor financeiro** — bancos, seguradoras de previdência privada, corretoras, gestoras de recursos.
- Formato: texto corrido com parágrafos curtos, sem listas com marcadores.

### 3. AGENDA DO DIA

- **Título**: `AGENDA DO DIA` (branco, negrito, fundo azul marinho).
- **Conteúdo**: Lista **numerada** dos principais acontecimentos previstos para o dia:
  - Agenda política (votações, discursos, reuniões ministeriais).
  - Dados econômicos a serem divulgados (IPCA, PIB, SELIC, balança comercial, etc.).
  - Reuniões do COPOM ou outros comitês de política monetária.
  - Eventos de mercado (IPOs, Ofertas Públicas, results de empresas).
  - Reuniões de bancos centrais (Fed, BCE, etc.).

### 4. RESUMO DO DIA

- **Título**: `RESUMO DO DIA` (branco, negrito, fundo azul marinho).
- **Conteúdo**: Resumo das principais notícias econômicas, políticas e dos players de mercado do dia atual.
- Formato: **texto corrido**, sem tópicos nem listas. Parágrafos narrativos.

---

## Regras de Conteúdo

1. **Neutralidade absoluta**: NÃO conter opiniões, análises, interpretações ou visões do editor/IA sobre as notícias. Apenas fatos reportados de forma objetiva.
2. **Fontes obrigatórias**:
   - [UOL Economia](https://economia.uol.com.br/)
   - [G1 Economia](https://g1.globo.com/economia/)
   - [Valor Econômico](https://valor.globo.com/)
   - [InfoMoney](https://www.infomoney.com.br/)
3. **Atualidade**: Todo conteúdo deve refletir os fatos mais recentes disponíveis.
4. **Relevância**: Incluir apenas notícias de impacto relevante para o mercado financeiro.

---

## Fluxo de Geração

### Passo 1 — Coleta de Notícias
- Acessar as 4 fontes obrigatórias via webfetch ou websearch.
- Extrair manchetes e resumos das matérias mais recentes e relevantes.
- Classificar por categorias: Econômico, Político, Empresas do Setor Financeiro.

### Passo 2 — Montagem do Conteúdo
- Redigir o **Resumo do Dia Anterior** (texto corrido, sem opinião).
- Listar a **Agenda do Dia** (itens numerados, factual).
- Redigir o **Resumo do Dia** (texto corrido, sem opinião).

### Passo 3 — Geração do HTML
- Montar arquivo HTML com a estrutura visual definida.
- Incluir botão de player com JavaScript (Web Speech API):
  ```javascript
  function togglePlayer() {
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
    } else if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    } else {
      const texto = document.getElementById('conteudo-jornal').innerText;
      const utterance = new SpeechSynthesisUtterance(texto);
      utterance.lang = 'pt-BR';
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  }
  ```
- Salvar como `output/OnzeNews_YYYY-MM-DD.html`.

### Passo 4 — Conversão para PDF
- Usar Puppeteer ou Playwright para gerar PDF a partir do HTML.
- Configurar: A4, margens adequadas.
- Salvar como `output/OnzeNews_YYYY-MM-DD.pdf`.

### Passo 5 — Notícia Extraordinária (quando aplicável)
- Se identificada notícia de **impacto extraordinário** (quebra de banco, mudança de SELIC fora de agenda, crise geopolítica, etc.):
  - Gerar PDF separado imediatamente.
  - Título: `NOTICIA EXTRAORDINÁRIA`.
  - Cabeçalho: **OnzeNews — NOTICIA EXTRAORDINÁRIA**.
  - Formato: resumo objetivo dos fatos, sem opinião.
  - Salvar como `OnzeNews_EXTRA_YYYY-MM-DD_HH-MM.pdf`.

---

## Entregáveis

| Arquivo | Descrição |
|---------|-----------|
| `OnzeNews_YYYY-MM-DD.pdf` | Jornal diário gerado às 8h |
| `OnzeNews_YYYY-MM-DD.html` | Versão HTML com player de podcast funcional |
| `OnzeNews_EXTRA_YYYY-MM-DD_HH-MM.pdf` | Notícia extraordinária (quando houver) |

---

## Agendamento

- **Jornal diário**: Todos os dias às **8h da manhã** (horário de Brasília).
- **Notícia extraordinária**: Imediatamente ao identificar notícia de alto impacto.
