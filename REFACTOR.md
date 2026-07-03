# REFACTOR.md — Migração Selenium → HTTP + OCR

**Documento de delta para o Claude Code (VSCode).** Não é um plano do zero — é o
que **mudar, deletar e adicionar** em cima do que já existe no repo (`initialscraping.py`,
`TODO.md`, `prompt.md`). Onde o `TODO.md` continuar válido, este arquivo aponta
"reaproveitar"; onde ficou obsoleto, aponta "substituir".

> Leia este arquivo inteiro antes de tocar em qualquer código. As mudanças estruturais
> (fonte de dados via HTTP, OCR) invalidam partes grandes do `TODO.md`.

---

## 0. Por que este refactor existe

Fizemos engenharia reversa do Portal de Compras Públicas e descobrimos que **tudo o que
o Selenium fazia é servido por uma API HTTP pública, sem autenticação**: busca, detalhe,
lista de documentos e download de arquivos. O scraper via navegador (`initialscraping.py`)
está inteiramente obsoleto — incluindo a função `parsear_processo` (120 linhas de parsing
posicional de texto renderizado), que agora dá lugar a JSON estruturado e nomeado.

Consequência estratégica: **o scraping deixou de ser o risco do projeto.** O núcleo de
valor e de risco passou a ser **OCR + auditoria por LLM**. É pra lá que o esforço vai.

---

## 1. Decisões travadas

| Decisão | Valor | Observação |
|---|---|---|
| Fonte de dados | **Portal de Compras Públicas (API HTTP)** | PNCP investigado à parte (Apêndice A); fonte fica atrás de interface trocável |
| Modo de uso | **On-demand** | Usuário busca um termo, audita os processos retornados. Sem pipeline de ingestão contínua no v1 |
| OCR | **Tesseract** (local) | `pytesseract` + `pdf2image` + Poppler; idioma `por` |
| Selenium | **Removido por completo** | Nenhum Chrome/chromedriver no projeto |

---

## 2. Arquitetura da fonte de dados (chave para o PNCP entrar depois)

Não acople o resto do sistema ao portal. Defina uma **interface** e uma implementação
concreta. Quando o PNCP for validado, ele vira só mais uma implementação — nada acima
dela muda.

Criar `backend/app/scraper/fonte_base.py`:

```python
from abc import ABC, abstractmethod

class FonteDados(ABC):
    @abstractmethod
    def buscar(self, termo: str, limite: int) -> list[dict]:
        """Retorna lista de processos já no schema interno (ver seção 5)."""

    @abstractmethod
    def listar_documentos(self, processo: dict) -> list[dict]:
        """Retorna [{nome, tipo, data, id_arquivo, url}]."""

    @abstractmethod
    def baixar_documento(self, doc: dict, destino: str) -> int:
        """Baixa o arquivo. Retorna bytes gravados. Valida magic number."""
```

Implementação atual: `backend/app/scraper/fonte_portal.py` → `class FontePortal(FonteDados)`.
Futuro: `fonte_pncp.py` → `class FontePNCP(FonteDados)`. A escolha da fonte fica em
`config.py` (ex.: `FONTE_DADOS = "portal"`), resolvida por uma factory.

---

## 3. O que DELETAR

`initialscraping.py` deixa de existir como está. Não copie nada dele para o backend, com
UMA exceção: a função `aguardar_download` **não é mais necessária** (o download HTTP é
síncrono). Especificamente, some tudo isto:

- `iniciar_driver`, `fechar_banner_cookies` — Selenium.
- `buscar_processos` (versão Selenium) — vira chamada HTTP.
- **`parsear_processo` inteira** — o parsing posicional (`linhas[idx-3]`, "texto mais
  longo antes de 'Informações'", regex de datas em texto) morre. Os campos agora vêm
  nomeados no JSON.
- `extrair_dados_processo` (lê `.text` do `<main>`) — morre.
- `aguardar_download`, `baixar_documentos` (versão Selenium, clique em botão) — morre.
- Todo o conceito de `conteudo_bruto` como "linhas de texto raspado". Se quiser manter
  o campo por compatibilidade com `prompt.md`, preencha-o com o **JSON bruto da API**
  (dump do que a API devolveu), não com texto de tela. Avaliar se vale manter (seção 5).

`initialscraping.py` pode ser mantido na raiz como referência histórica, mas **não é
fonte de código** para o backend.

---

## 4. `requirements.txt` — mudanças

Remover:
```
selenium
```

Adicionar:
```
requests
pytesseract
pdf2image
Pillow
```

Trocar (SDK do Gemini desatualizado):
```
- google-generativeai
+ google-genai
```
> `google-generativeai` está descontinuado. O SDK novo é `google-genai`, com API
> diferente (`from google import genai; client = genai.Client(...)`). Isso muda o
> `gemini_service.py` do `TODO.md` (ver seção 8).

Manter: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic-settings`, `pypdf`,
`pdfplumber`, `python-dotenv`.

**Dependências de sistema (NÃO são pip)** — documentar no README e instalar no ambiente:
```
tesseract-ocr
tesseract-ocr-por      # pacote de idioma português
poppler-utils          # necessário para pdf2image converter PDF→imagem
```
Sem esses três, o OCR não roda. No `SessionStart` hook / setup do repo, garantir que
existem (`tesseract --version`, `pdftoppm -v`).

---

## 5. Novo cliente HTTP do portal (`fonte_portal.py`)

Endpoints confirmados por recon (todos GET, sem auth, sem cookie):

| Função | Endpoint |
|---|---|
| Buscar | `GET https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/processos?objeto={termo}&pagina={n}&limitePagina={k}` |
| Detalhe | `GET https://compras.api.portaldecompraspublicas.com.br/v2/licitacao{urlReferencia}` |
| Itens | `GET https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/{codigoLicitacao}/itens?pagina=1` |
| Documentos | `GET https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/{codigoLicitacao}/documentos/processo` |
| Download | `GET https://arquivos.portaldecompraspublicas.com.br/v1/download/{idArquivo}` |

Headers para todas:
```python
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.portaldecompraspublicas.com.br/",
}
```

Notas de implementação:
- **Busca** devolve `{"result": [...], "totalRegistros": N, "totalPaginas": M}`. Para
  on-demand, paginar até atingir `limite` ou acabar as páginas. `codigoLicitacao` é a
  chave única → **usar para deduplicar** (o scraper antigo trazia duplicatas; aqui,
  dict por `codigoLicitacao` resolve).
- **Detalhe** usa `processo["urlReferencia"]` (ex.: `/rj/prefeitura-.../rpe-28-2026-2026-492130`),
  concatenado direto após `/v2/licitacao` (a `urlReferencia` já começa com `/`). Traz
  campos que a lista não tem: `numeroProcesso`, `nomePregoeiro`,
  `nomeAutoridadeCompetente`, `legislacaoAplicavel`, `dataHoraLimiteImpugnacoes`, etc.
- **Documentos**: cada item tem `idArquivo` (hash SHA-256). A URL de download é
  `.../v1/download/{idArquivo}` — o hash é auto-suficiente, não precisa do
  `codigoLicitacao`. Itens com `url == null` / `tipoDownLoad == 2` são **links especiais
  sem arquivo** (ex.: "Municípios Locais/Regionais") → **pular** no download.
- **Download**: validar `resposta.content[:4] == b"%PDF"` para PDFs (o bug antigo do
  `downloads.htm` de 33MB era redirect para HTML; o endpoint certo nunca devolve HTML).
  Para não-PDF (ex.: `.docx`, `.zip`), validar por `Content-Type`/`Content-Disposition`
  em vez do magic `%PDF`. Usar `filename` do `Content-Disposition` como nome do arquivo.
- **Ignorar** o `POST /v1/arquivo/download/contador` (analytics; não bloqueia nada).
- **Cidadania**: adicionar pequeno `time.sleep` entre chamadas e um retry com backoff.
  É API não-oficial de terceiro — não martelar. Tratar 5xx/timeout com tolerância.

### Camada de mapeamento (API → schema que o `prompt.md` espera)

O `prompt.md` (seção 2.1) espera um schema específico por processo. Criar uma função
`mapear_processo(detalhe, itens, documentos) -> dict` que produz exatamente:

| Campo no schema `prompt.md` | Origem na API |
|---|---|
| `url` | página pública derivada de `urlReferencia` |
| `numero_processo` | `numeroProcesso` (detalhe) / `numero` (lista) |
| `situacao` | `status.descricao` |
| `comprador` | `razaoSocial` / `nomeUnidade` |
| `modalidade` | `tipoLicitacao.modalidadeLicitacao` |
| `objeto` | `resumo` (usar o do detalhe, sem truncar) |
| `informacoes.Tipo` | `tipoLicitacao.tipoLicitacao` / `tipoRealizacao` |
| `informacoes.Pregoeiro` | `nomePregoeiro` |
| `informacoes["Autoridade Competente"]` | `nomeAutoridadeCompetente` |
| `informacoes["Legislação Aplicável"]` | `legislacaoAplicavel` |
| `datas["Data de Publicação"]` | `dataHoraPublicacao` |
| `datas["Limite p/ Impugnações"]` | `dataHoraLimiteImpugnacoes` |
| `datas["Limite p/ Recebimento das Propostas"]` | `dataHoraFinalPropostas` |
| `datas["Abertura das Propostas"]` | `dataHoraInicioPropostas` |
| `documentos[]` | `{nome, tipo, data: dataHora}` de `documentos/processo` |
| `itens[]` | `{numero: codigo, descricao, quantidade, valor_de_referência: valorReferencia, unidade}` |
| `andamento[]` | `GET /v1/licitacao/{id}/chat` — **verificar o shape antes de mapear** |
| `arquivos_baixados[]` | preenchido após o download: `{arquivo, tamanho_bytes, pasta}` |
| `conteudo_bruto` | **decisão**: preencher com o JSON bruto da API, ou remover do schema |

> Datas agora vêm em ISO 8601 (`2026-06-30T18:47:00Z`), não `dd/mm/yyyy`. Decidir se
> normaliza para exibição ou passa ISO ao LLM (o `prompt.md` é tolerante, mas seja
> consistente).

> `conteudo_bruto`: no schema antigo era o texto raspado que o LLM usava como fallback.
> Com dados estruturados limpos, ele perde função. Recomendação: **remover** do schema e
> ajustar `prompt.md` para não depender dele — menos tokens, menos ruído. Se preferir
> manter por segurança, coloque o JSON bruto da API, nunca texto de tela.

---

## 6. OCR — agora é peça central, não detalhe (reescreve a Fase 4 do `TODO.md`)

Baixar documento virou trivial → você vai receber MUITOS editais, e boa parte é **PDF
escaneado**. `pypdf`/`pdfplumber` devolvem vazio nesses. Sem OCR, a auditoria roda cega
no documento mais importante. O fluxo de `extrair_texto_pdf` passa a ter 3 níveis:

1. Tentar `pypdf`. Se `len(texto.strip()) >= 50` → `status="ok"`, `metodo="pypdf"`.
2. Senão, tentar `pdfplumber`. Se `>= 50` → `status="ok"`, `metodo="pdfplumber"`.
3. Senão (provável PDF escaneado) → **OCR com Tesseract**:
   - `pdf2image.convert_from_path(caminho, dpi=200)` para rasterizar as páginas
     (requer Poppler).
   - `pytesseract.image_to_string(img, lang="por")` por página, concatenar.
   - Se `>= 50` → `status="ok_ocr"`, `metodo="tesseract"`.
   - Senão → `status="vazio_apos_ocr"`.
   - Qualquer exceção → `status="erro"`, `erro=str(e)`.

Cuidados:
- OCR é **lento** (segundos por página). Limitar nº de páginas OCR por documento (ex.:
  primeiras N) ou paralelizar com cautela. Isso empurra a etapa de análise ainda mais
  para "job em background" (seção 7).
- `dpi` alto = melhor OCR, mais lento. 200–300 é um bom meio.
- Manter os status distintos (`ok` vs `ok_ocr`) para o LLM/relatório saber a procedência
  do texto e ponderar confiança.

---

## 7. Jobs em background — o gargalo mudou de lugar (ajuste na Fase 3 do `TODO.md`)

No `TODO.md`, a thread em background existia para o scraping Selenium lento. **Agora o
scraping é rápido e síncrono** (HTTP). A parte lenta passou a ser:

1. **Download + OCR** de vários PDFs.
2. **Chamada ao Gemini.**

Então:
- O `POST /pesquisas` ainda dispara job em background, mas o job é
  **buscar (rápido) + baixar docs + extrair/OCR texto**. Manter `status` com estados
  (`pendente` → `em_andamento` → `completo`/`erro`), como no `TODO.md`.
- A preocupação antiga com "um Chrome por job estoura a memória" **desaparece** — sem
  navegador. Threading simples (`threading.Thread`) resolve o v1 on-demand. Só reavalie
  se for concorrência alta (aí, fila de verdade).
- A chamada ao Gemium (Fase 6) continua em job próprio, como planejado.

---

## 8. O que NÃO muda (reaproveitar do `TODO.md`)

Estas partes seguem válidas — não reinventar:

- **Estrutura FastAPI** (Fase 3): routers, `main.py`, CORS, endpoints de pesquisa/análise.
  - ⚠️ Ajuste: `@app.on_event("startup")` está **deprecado**. Usar `lifespan` handler.
- **Modelos e schema do banco** (Fase 2): `Pesquisa`, `Analise`, SQLite. Sem mudança.
- **Extração de PDF** (Fase 4): a estrutura de `pdf_extractor.py` continua, **mas com o
  3º nível de OCR** da seção 6 acima.
- **Serviço Gemini** (Fase 5): a orquestração (montar prompt, parsear JSON de resposta)
  continua, **mas reescrever a chamada para o SDK `google-genai`** (a API `genai.Client`
  substitui `genai.GenerativeModel`). Verificar o nome do modelo atual válido.
- **Frontend Next.js** (Fases 7–9): praticamente intacto. Os tipos em `types.ts` refletem
  o schema mapeado (seção 5), que é o mesmo que o `prompt.md` já esperava — então o
  frontend nem percebe a troca de Selenium por HTTP.

---

## 9. Riscos remanescentes (não resolvidos por este refactor)

1. **OCR de baixa qualidade**: editais escaneados tortos/ruins geram texto sujo → o LLM
   audita sobre lixo. Monitorar `status=ok_ocr` e considerar avisar o usuário.
2. **API não-oficial e instável**: `v2/licitacao/...` pode mudar sem aviso. A interface
   `FonteDados` (seção 2) contém o dano, mas adicione parsing defensivo e um teste de
   fumaça que roda contra a API real e alerta se o schema mudou.
3. **Responsabilidade jurídica do LLM**: o modelo afirmando "não conformidade" sobre
   processo real é passivo se errar. Enquadrar a saída como **rascunho assistivo**, com
   **citação do trecho do documento** que embasa cada constatação (para revisão humana).
   Nunca como parecer autoritativo. (Ajuste a fazer no `prompt.md`.)
4. **Prompt de 46KB por chamada**: custo e latência. Enxugar o `prompt.md` e usar cache
   de prompt do provedor.
5. **ToS/legalidade do scraping**: raspar API interna de marketplace privado tem risco de
   ToS. É parte da motivação para investigar o PNCP (fonte oficial) em paralelo.

---

## 10. Ordem de execução recomendada

1. Ajustar `requirements.txt` + dependências de sistema (Tesseract, Poppler) — seção 4.
2. Criar `fonte_base.py` (interface) + `fonte_portal.py` (cliente HTTP) + mapeamento — seções 2 e 5.
3. **Teste isolado**: buscar "cafe", detalhar 1, listar docs, baixar 1 PDF real
   (validar `%PDF`), imprimir o dict mapeado. Só avançar quando isso rodar ponta a ponta.
4. `pdf_extractor.py` com os 3 níveis + OCR — seção 6. Teste isolado num PDF nativo e
   num escaneado.
5. Reconectar ao backend (Fases 2, 3 do `TODO.md`, com os ajustes das seções 7 e 8).
6. Gemini com `google-genai` (Fase 5/6, ajustada).
7. Frontend (Fases 7–9, praticamente como no `TODO.md`).

---

## Apêndice A — Investigação separada do PNCP (não bloqueia a obra acima)

O PNCP (Portal Nacional de Contratações Públicas) é a fonte **oficial** do governo,
com API documentada e estável — mais defensável juridicamente que o portal privado. O
campo `codigoPncp` visto no JSON do portal sugere que os dados espelham o PNCP.

**Objetivo da investigação:** confirmar se o PNCP consegue manter TODAS as informações
que o portal fornece hoje. O maior risco é a **busca por texto livre**: a API de consulta
do PNCP é orientada a data/modalidade/órgão/UF, e pode **não** suportar `?objeto=cafe`.
Se não suportar, a UX on-demand por palavra-chave quebra — e o portal continua sendo
necessário (pelo menos para a busca).

Prompt de recon para rodar num Claude Code com rede livre (mesmo método que usamos no
portal):

```
Faça engenharia reversa/leitura da API pública oficial do PNCP (Portal Nacional de
Contratações Públicas). Preciso saber se ela substitui a API privada do Portal de
Compras Públicas para um produto de auditoria on-demand por palavra-chave. Descubra e
DOCUMENTE, com exemplos curl reais e amostras de resposta:

1. BUSCA POR TEXTO LIVRE: existe algum endpoint que busque contratações por palavra no
   objeto (ex.: "cafe")? Ou só dá para filtrar por data/modalidade/órgão/UF e paginar?
   Esse é o ponto mais crítico — teste de verdade.
2. METADADOS do processo: número, órgão, modalidade, objeto, datas (publicação,
   impugnação, propostas), legislação, pregoeiro/autoridade. O que a API expõe?
3. ITENS da contratação: descrição, quantidade, unidade, valor de referência.
4. DOCUMENTOS/ARQUIVOS: a API disponibiliza download dos arquivos do processo (edital,
   ETP, TR, anexos) sem autenticação? Qual endpoint, qual formato, precisa de token?
5. Como o codigoPncp do portal privado (visto como "codigoPncp": 2 / null nos JSONs)
   se relaciona com o identificador real do PNCP (cnpj/ano/sequencial)? É possível
   cruzar as duas fontes?

Entregue: tabela de endpoints (URL, método, auth, params), amostras de resposta, e um
veredito claro: "PNCP substitui o portal para busca on-demand por palavra-chave?
sim / não / só como fonte de dados canônicos após achar o processo em outra fonte".
Documente falhas reais em vez de inventar endpoints.
```

Com esse relatório em mãos, decidimos entre: (a) migrar para PNCP, (b) híbrido — busca no
portal, dados canônicos + documentos no PNCP via `codigoPncp`, ou (c) manter só o portal.
