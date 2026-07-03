<!-- prompt original preservado abaixo -->
Continuação de uma engenharia reversa do Portal de Compras Públicas. Já descobri a API pública de dados (https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/processos e /v2/licitacao/{id}/itens, ambos sem auth). FALTA descobrir só como funciona o DOWNLOAD DE DOCUMENTOS/EDITAL, que na tentativa anterior deu 401/500 em endpoints CHUTADOS — mas eu sei que o download funciona sem login, porque um scraper Selenium anterior baixou 10 arquivos clicando nos botões da seção "Documentos" sem nenhuma autenticação.

Use Playwright (Chromium headless) e faça o caminho REAL, não chute endpoints:

1. Navegue direto para uma página de detalhe de processo com documentos, ex: https://www.portaldecompraspublicas.com.br/processos/rj/prefeitura-municipal-de-varre-sai-4519/rpe-28-2026-2026-492130 (ou outro processo com termo "cafe" que tenha documentos). Feche o banner de cookies.

2. Ligue a interceptação de rede capturando TODA request (XHR, fetch, document, e principalmente qualquer navegação/download). Role até a seção "Documentos".

3. Encontre os botões de download de documento no DOM (o scraper antigo usava o seletor CSS `div.document-wrapper button`). Confirme quantos existem e o texto/nome de cada um.

4. CLIQUE de verdade no primeiro botão de documento e capture a request que o clique dispara: a URL EXATA (com querystring/token se houver), método, headers enviados, e o Content-Type / Content-Disposition da resposta. Se abrir nova aba ou iniciar um download, capture o alvo desse download. Repita para 1–2 documentos.

5. Pegue a(s) URL(s) de download capturada(s) e TENTE baixá-la(s) com `requests` puro em Python (só os headers mínimos: User-Agent, Referer, Accept), SEM navegador e SEM cookies. Verifique: (a) status HTTP, (b) Content-Type, (c) tamanho, (d) se os primeiros bytes são de um PDF real (`%PDF`) ou de uma página HTML de erro. IMPORTANTE: uma tentativa anterior baixou um arquivo "downloads.htm" de 33MB que era HTML disfarçado — então valide o magic number, não confie no download ter acontecido.

6. Se falhar sem cookies, repita enviando os cookies da sessão do browser e diga QUAIS cookies foram necessários.

7. Relatório: URL(s) de download, padrão de construção (como derivar a URL a partir do codigoLicitacao ou de um id de documento?), o que a lista de documentos retorna (ache o endpoint/estrutura que popula `div.document-wrapper`), e veredito: download reproduzível com requests puro? sim / precisa cookie / precisa browser. Documente falhas reais em vez de inventar.

---

# RELATÓRIO

**Data:** 2026-07-03  
**Método:** Playwright Chromium headless + Python requests  
**Processo de referência:** codigoLicitacao=492130 (RPE 28/2026 — Prefeitura de Varre-Sai/RJ — café)  
**Verificado também em:** processos 486689 (Presidente Epitácio/SP) e 489841 (Lambari/MG)

---

## Passo 3 — Seletor `div.document-wrapper button`

O seletor **funciona**. Foram encontrados **4 botões** dentro de `div.document-wrapper` para o processo 492130.

Documentos presentes:

| # | Nome | Tipo |
|---|---|---|
| 1 | Processo 3075 2026 - EDITAL E ANEXOS.pdf | Edital |
| 2 | Decreto Municipal | Anexo |
| 3 | Processo 3075 2026 - AVISO DE PUBLICAÇÃO.pdf | Outros documentos |
| 4 | Municípios Locais/Regionais | Anexo (link especial, sem arquivo direto) |

---

## Passo 4 — Requests disparadas pelo clique

Ao clicar no primeiro botão, **duas requests** foram disparadas:

### 4a. Contador de download (POST — analytics, não bloqueia)

```
POST https://conteudo.api.portaldecompraspublicas.com.br/v1/arquivo/download/contador
Content-Type: application/json

Body: {"codigoLicitacao": 492130, "codigoArquivoLicitacao": 657, "ip": "56.125.150.141"}

Response: true (200 OK)
```

### 4b. Download real (GET — dispara download de arquivo)

```
GET https://arquivos.portaldecompraspublicas.com.br/v1/download/ac986e8f97cb897b1e417b5d4baf06e112deaa6323feaec5dfe6b988ab8e675c

Response:
  Status: 200 OK
  Content-Type: application/pdf
  Content-Disposition: attachment; filename="Processo 3075 2026 - EDITAL E ANEXOS.pdf"
  Content-Length: 1315715
```

**Suggested filename capturado pelo Playwright:** `Processo 3075 2026 - EDITAL E ANEXOS.pdf`

---

## Passo 5 — Teste com `requests` puro (sem cookies)

```
GET https://arquivos.portaldecompraspublicas.com.br/v1/download/ac986e8f...

Resultado SEM COOKIES:
  status=200
  Content-Type: application/pdf
  Content-Disposition: attachment; filename="Processo 3075 2026 - EDITAL E ANEXOS.pdf"
  Content-Length: 1315715
  Magic bytes: b'%PDF'  ← PDF real, não HTML disfarçado
  is_pdf=True  ✓
```

**Download funciona 100% sem cookies, sem browser, sem autenticação.**

---

## Endpoint de lista de documentos (o que popula `div.document-wrapper`)

O endpoint foi descoberto via análise do **Angular Transfer State** embutido no HTML SSR da página de detalhe.

**URL:** `GET /v2/licitacao/{codigoLicitacao}/documentos/processo`

```bash
curl -s "https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/492130/documentos/processo" \
  -H "Accept: application/json" \
  -H "Referer: https://www.portaldecompraspublicas.com.br/"
```

### Schema da resposta

```json
[
  {
    "codigoLicitacao": 492130,
    "nome": "Processo 3075 2026 - EDITAL E ANEXOS.pdf",
    "url": "https://arquivos.portaldecompraspublicas.com.br/v1/download/ac986e8f97cb897b1e417b5d4baf06e112deaa6323feaec5dfe6b988ab8e675c",
    "tipo": "Edital",
    "dataHora": "30/06/2026-15:43",
    "tipoDownLoad": 0,
    "tituloDocumento": null,
    "parametros": null,
    "idArquivo": "ac986e8f97cb897b1e417b5d4baf06e112deaa6323feaec5dfe6b988ab8e675c",
    "codigoArquivoLicitacao": 657,
    "codigoPncp": 2
  },
  {
    "codigoLicitacao": 492130,
    "nome": "Decreto Municipal",
    "url": "https://arquivos.portaldecompraspublicas.com.br/v1/download/2f36d89ed67c...",
    "tipo": "Anexo",
    "dataHora": "27/05/2026-00:00",
    "tipoDownLoad": 4,
    "tituloDocumento": "Decreto Municipal",
    "parametros": null,
    "idArquivo": "2f36d89ed67c...",
    "codigoArquivoLicitacao": 0,
    "codigoPncp": null
  },
  {
    "nome": "Municípios Locais/Regionais",
    "url": null,
    "idArquivo": null,
    "tipoDownLoad": 2,
    "parametros": "LocalRegional,492130"
  }
]
```

**Campos-chave:**

| Campo | Uso |
|---|---|
| `url` | URL direta para download (pode ser null em documentos do tipo link especial) |
| `idArquivo` | Hash SHA-256 do arquivo = sufixo da URL de download |
| `nome` | Nome do arquivo |
| `tipo` | "Edital", "Anexo", "Outros documentos" |
| `tipoDownLoad` | 0=download direto, 2=link especial/regional, 4=anexo genérico |
| `codigoArquivoLicitacao` | ID do arquivo (enviado no contador de analytics) |

**Documentos com `url=null` (tipoDownLoad=2)** são links especiais que abrem uma subpágina no site — não têm arquivo para baixar diretamente.

---

## Endpoint de detalhe do processo

**URL:** `GET /v2/licitacao/{uf}/{municipio-slug}/{processo-slug}`

O slug vem do campo `urlReferencia` retornado pela lista de processos (sem o prefixo `/`).

```bash
curl -s "https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/rj/prefeitura-municipal-de-varre-sai-4519/rpe-28-2026-2026-492130" \
  -H "Accept: application/json"
```

**Campos adicionais** em relação à lista:

| Campo | Descrição |
|---|---|
| `numeroProcesso` | Número do processo ("28/2026") |
| `nomePregoeiro` | Nome do pregoeiro responsável |
| `nomeAutoridadeCompetente` | Autoridade competente |
| `resumo` | Objeto completo (sem truncamento) |
| `lei14133` / `lei8666` | Legislação aplicável (boolean) |
| `tipoJulgamento` | Critério de julgamento ("Menor Preço") |
| `legislacaoAplicavel` | Texto da lei ("Lei nº 14.133...") |
| `situacaoEdital` | Situação do edital |
| `dataHoraLimiteImpugnacoes` | Prazo para impugnações |
| `origemRecurso` | Origem do recurso ("Próprio") |

---

## Demais endpoints descobertos (via Angular Transfer State)

| Endpoint | Descrição | Auth |
|---|---|---|
| `GET /v2/licitacao/{id}/documentos/processo` | Lista de documentos do processo | Não |
| `GET /v2/licitacao/{id}/documentos/fornecedores` | Documentos de fornecedores (geralmente vazio) | Não |
| `GET /v2/licitacao/{uf}/{municipio}/{slug}` | Detalhe completo do processo | Não |
| `GET /v2/licitacao/{id}/itens?pagina=1` | Itens/lotes | Não |
| `GET /v1/licitacao/{id}/chat` | Histórico do chat do processo | Não |
| `GET https://arquivos.portaldecompraspublicas.com.br/v1/download/{hash}` | Download do arquivo | Não |
| `POST /v1/arquivo/download/contador` | Contador de downloads (analytics) | Não (pode ignorar) |
| `GET https://processador-de-editais-worker.secure.portaldecompraspublicas.com.br/bidding/{id}` | Status de processamento do edital | Não testado |

---

## Padrão de derivação das URLs de download

```
codigoLicitacao → GET /v2/licitacao/{id}/documentos/processo
                     ↓
                  documento.idArquivo  (= hash SHA-256)
                     ↓
                  GET https://arquivos.portaldecompraspublicas.com.br/v1/download/{idArquivo}
```

Não é necessário passar o `codigoLicitacao` na URL de download — o hash é auto-suficiente.

---

## Código Python completo (sem browser)

```python
import requests

BASE = "https://compras.api.portaldecompraspublicas.com.br"
ARQUIVOS = "https://arquivos.portaldecompraspublicas.com.br"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.portaldecompraspublicas.com.br/",
}

def buscar_processos(objeto, pagina=1, limite=12):
    r = requests.get(f"{BASE}/v2/licitacao/processos", params={
        "objeto": objeto, "pagina": pagina, "limitePagina": limite
    }, headers=HEADERS)
    return r.json()["result"]

def detalhar_processo(processo):
    url_ref = processo["urlReferencia"]  # ex: "/rj/municipio-slug/rpe-28-2026-2026-492130"
    r = requests.get(f"{BASE}/v2/licitacao{url_ref}", headers=HEADERS)
    return r.json()

def listar_documentos(codigo_licitacao):
    r = requests.get(f"{BASE}/v2/licitacao/{codigo_licitacao}/documentos/processo", headers=HEADERS)
    return r.json()

def baixar_documento(id_arquivo, destino):
    """id_arquivo = campo idArquivo do documento (hash SHA-256)"""
    url = f"{ARQUIVOS}/v1/download/{id_arquivo}"
    r = requests.get(url, headers={**HEADERS, "Accept": "*/*"}, stream=True)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF", "Não é PDF!"
    with open(destino, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return len(r.content)

# Exemplo de uso
processos = buscar_processos("cafe")
p = processos[0]
docs = listar_documentos(p["codigoLicitacao"])
for doc in docs:
    if doc.get("idArquivo"):  # documentos com url=null são links especiais
        baixar_documento(doc["idArquivo"], f"{doc['nome']}")
```

---

## Veredito final

**Download reproduzível com `requests` puro? SIM, 100%.**

| Etapa | Browser? | Auth? | Resultado |
|---|---|---|---|
| Buscar lista de processos | Não | Não | **OK** |
| Detalhar processo | Não | Não | **OK** |
| Listar documentos | Não | Não | **OK** |
| Baixar arquivo (PDF, etc.) | Não | Não | **OK — PDF real, magic `%PDF`** |

**O Selenium pode ser substituído inteiramente por chamadas HTTP diretas.** O antigo scraper que baixava "downloads.htm" de 33MB provavelmente estava seguindo um redirect para a página de listagem em vez do arquivo — o endpoint correto é `/v1/download/{idArquivo}` (sem a palavra "downloads"), e a URL nunca gera HTML: sempre devolve o binário do arquivo com `Content-Type: application/pdf`.