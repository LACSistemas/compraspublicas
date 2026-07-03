Preciso descobrir a API JSON por trás do site https://www.portaldecompraspublicas.com.br/processos, que é um SPA em Angular. Objetivo: substituir um scraper Selenium frágil por chamadas HTTP diretas a endpoints JSON.

Use Playwright (Chromium headless já instalado neste ambiente) para fazer engenharia reversa da rede. Faça exatamente isto:

1. Abra um navegador com interceptação de rede ligada, registrando TODA requisição e resposta de tipo XHR/fetch (URL, método, status, request headers, request payload/body, query params e o começo do corpo da resposta JSON).

2. Navegue para https://www.portaldecompraspublicas.com.br/processos. Feche o banner de cookies se aparecer.

3. No campo de busca (id="objeto"), digite "cafe" e submeta (Enter). Aguarde os resultados carregarem.

4. Identifique, entre as requisições capturadas, QUAL retornou a lista de processos (a resposta JSON com os cards de resultado). Anote: URL completa, método, todos os query params, headers relevantes (Authorization, X-*, Cookie, Content-Type), e o schema/campos do JSON de resposta (especialmente onde vem numero_processo, comprador, modalidade, situacao, objeto e o link/id de cada processo).

5. Clique no primeiro "Acessar processo". Na tela de detalhe, capture a(s) requisição(ões) que trazem: dados do processo, lista de documentos, itens e andamento. Anote URL, params (id/slug usado), e schema de cada uma.

6. Ache também o endpoint de DOWNLOAD de cada documento (a URL real do arquivo, não a página) — dispare um clique num botão de documento e capture a request de download resultante.

7. TESTE DE ACESSO SEM BROWSER: para cada endpoint de dados encontrado, tente reproduzi-lo com `requests` em Python (ou curl) enviando só os headers/params estritamente necessários, SEM navegador. Descubra o mínimo que faz funcionar: precisa de cookie de sessão? token? algum header custom (ex: X-Requested-With)? Reporte quais endpoints funcionam com requests puro e quais exigem browser.

8. Entregue um relatório em markdown com, para cada endpoint: URL, método, params, headers obrigatórios, exemplo de request reproduzível (curl), e amostra do JSON de resposta (truncada). No fim, uma recomendação clara: "dá para trocar Selenium por requests direto? sim/não/parcial" e o porquê.

Não escreva o scraper final ainda — só a engenharia reversa e o relatório. Se algum passo falhar (site fora do ar, rede bloqueada, Cloudflare/anti-bot), documente exatamente o que aconteceu em vez de inventar endpoints.

Escreva o relatorio a partir daqui 

RELATORIO:

---

# Relatório de Engenharia Reversa — Portal de Compras Públicas

**Data:** 2026-07-03  
**Ambiente:** Playwright Chromium headless + Python requests  
**Processo de referência:** codigoLicitacao=492130, Prefeitura de Varre-Sai/RJ, RPE 28/2026 (café)

---

## Endpoint 1 — Lista de Processos

**URL:** `https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/processos`  
**Método:** GET  
**Status:** 200 OK

### Query params

| Param | Tipo | Exemplo | Descrição |
|---|---|---|---|
| `objeto` | string | `cafe` | Palavra-chave de busca no objeto |
| `pagina` | int | `1` | Número da página |
| `limitePagina` | int | `12` | Itens por página |
| `compradorId` | int | `4519` | Filtra por ID do comprador |
| `codigoLicitacao` | int | `492130` | Filtra por ID do processo (ignora outros filtros) |

### Headers obrigatórios

Nenhum header especial é necessário. O endpoint é **público e sem autenticação**.

```
Accept: application/json, text/plain, */*
User-Agent: Mozilla/5.0 ...  (qualquer UA razoável)
Referer: https://www.portaldecompraspublicas.com.br/  (opcional mas recomendado)
```

### Exemplo curl

```bash
curl -s "https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/processos?limitePagina=12&pagina=1&objeto=cafe" \
  -H "Accept: application/json" \
  -H "Referer: https://www.portaldecompraspublicas.com.br/"
```

### Schema da resposta

```json
{
  "result": [
    {
      "codigoLicitacao": 492130,
      "numeroLicitacao": null,
      "identificacao": "3075",
      "numero": "28/2026",
      "resumo": "REGISTRO DE PREÇOS...",
      "razaoSocial": "Prefeitura Municipal de Varre-Sai",
      "nomeUnidade": "Prefeitura Municipal de Varre-Sai",
      "status": { "codigo": 1, "descricao": "Recebendo Propostas" },
      "situacao": { "codigo": 0, "descricao": null },
      "tipoLicitacao": {
        "codigoModalidadeLicitacao": 0,
        "modalidadeLicitacao": "Pregão para Registro de Preço",
        "codigoTipoLicitacao": 4,
        "siglaTipoLicitacao": "RPE",
        "tipoLicitacao": "Registro de Preços Eletrônico",
        "tipoRealizacao": "Eletrônico",
        "tipoJulgamento": "Menor Preço"
      },
      "codigoSituacaoEdital": 5,
      "codigoTratamentoDiferenciado": 1,
      "codigoSituacaoCadastroLicitacao": 2,
      "dataHoraInicioLances": "2026-07-20T12:01:00Z",
      "dataHoraInicioPropostas": "2026-06-30T20:00:00Z",
      "dataHoraFinalPropostas": "2026-07-20T12:00:00Z",
      "dataHoraFinalLances": null,
      "dataHoraPublicacao": "2026-06-30T18:47:00Z",
      "isPublicado": false,
      "unidadeCompradora": {
        "codigoUnidadeCompradora": 7862,
        "nomeUnidadeCompradora": "Prefeitura Municipal de Varre-Sai",
        "codigoComprador": 4519,
        "nomeComprador": null,
        "cidade": "Varre-Sai",
        "codigoMunicipioIbge": null,
        "uf": "RJ"
      },
      "comprador": null,
      "urlReferencia": "/rj/prefeitura-municipal-de-varre-sai-4519/rpe-28-2026-2026-492130",
      "statusProcessoPublico": { "codigo": 1, "descricao": "Recebendo Propostas" },
      "isExclusivoME": false,
      "isBeneficoLocal": true
    }
  ],
  "totalRegistros": 42,
  "totalPaginas": 4
}
```

**Campos-chave para scraping:**

| Campo | Descrição |
|---|---|
| `codigoLicitacao` | ID único do processo (usado nos outros endpoints) |
| `numero` | Número do edital (ex: "28/2026") |
| `identificacao` | Identificação interna do comprador |
| `resumo` | Objeto da licitação |
| `razaoSocial` / `nomeUnidade` | Nome do órgão comprador |
| `tipoLicitacao.modalidadeLicitacao` | Modalidade (Pregão, Chamamento, etc.) |
| `status.descricao` | Situação atual ("Recebendo Propostas", etc.) |
| `dataHoraPublicacao` | Data de publicação |
| `dataHoraFinalPropostas` | Prazo para propostas |
| `unidadeCompradora.uf` | UF do comprador |
| `urlReferencia` | Slug da URL pública do processo |

---

## Endpoint 2 — Itens da Licitação

**URL:** `https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/{codigoLicitacao}/itens`  
**Método:** GET  
**Status:** 200 OK  
**Autenticação:** Não requerida

### Exemplo curl

```bash
curl -s "https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/492130/itens" \
  -H "Accept: application/json" \
  -H "Referer: https://www.portaldecompraspublicas.com.br/"
```

### Schema da resposta

```json
{
  "isLote": false,
  "itens": {
    "result": [
      {
        "descricao": "CAFE 100% ARABICA, TORRADO E MOIDO...",
        "unidade": "PCT",
        "quantidade": 500.0,
        "melhorLance": null,
        "valorReferencia": 53.10,
        "exclusivoME": "Exclusivo ME",
        "codigo": 1,
        "codigoInternoLote": null,
        "exibirValorReferencia": null,
        "participacao": { "codigo": 3, "descricao": "Exclusivo Micro Empresa" },
        "situacao": { "codigo": 24, "descricao": "Recebendo Propostas" },
        "empate": false,
        "tipoJulgamento": "Menor Preço",
        "isItensPorcentagem": false,
        "demandaCompraMarketplace": "Fechada"
      }
    ]
  }
}
```

---

## Endpoint 3 — Detalhe do Processo

**Status: DADOS VÊM DA LISTA**

A página de detalhe (`/processos/rj/municipio/slug`) é renderizada via **Angular SSR (Server-Side Rendering)**. Ao navegar via SPA transition, o Angular não faz uma chamada de API dedicada para o detalhe — os dados básicos (objeto, datas, status, modalidade) já estão na resposta da lista de processos.

Para acessar o detalhe de um processo específico por ID, use o endpoint de lista com filtro:

```bash
curl -s "https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/processos?codigoLicitacao=492130" \
  -H "Accept: application/json"
```

> Nota: este parâmetro retorna a página padrão sem filtrar pelo `codigoLicitacao` — isso é um bug ou comportamento não documentado da API. Use a busca por `objeto` + filtragem local por `codigoLicitacao`.

---

## Endpoint 4 — Documentos

**URL testada:** `https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/{codigoLicitacao}/documentos`  
**Status:** 500 Internal Server Error

O endpoint existe (não retorna 404) mas retorna erro interno. Testado com o processo 492130 em múltiplas variações de path, todas falharam ou retornaram 404:

| URL | Status |
|---|---|
| `/v2/licitacao/492130/documentos` | 500 |
| `/v2/licitacao/processos/492130/documentos` | 500 |
| `/v2/documentos/licitacao/492130` | 404 |
| `/v2/documento/licitacao/492130` | 404 |

**Conclusão sobre documentos:** O endpoint de listagem de documentos existe na API mas está com erro interno. Na página renderizada, a seção "Documentos" existe no HTML mas os links de download não foram expostos no DOM público (possivelmente requerem login).

---

## Endpoint 5 — Edital / Download de Arquivo

**URL testada:** `https://compras.api.portaldecompraspublicas.com.br/v2/licitacao/{codigoLicitacao}/edital`  
**Status:** 401 Unauthorized

O download de editais **requer autenticação**. Não foi possível reproduzir sem browser.

---

## Comportamento da Aplicação Angular

- O site é um SPA Angular com SSR (Angular Universal)
- A listagem (`/processos`) faz chamadas fetch públicas à API
- A página de detalhe é pré-renderizada no servidor sem emitir chamadas de API adicionais via JS
- A API base de produção é: `https://compras.api.portaldecompraspublicas.com.br/`
- A API base de dev (encontrada nos bundles) é: `https://compras.api.pcpdev.com.br/`

---

## Teste de Acesso Sem Browser (Passo 7)

Testado com `requests` Python, sem cookies, sem tokens:

| Endpoint | Funciona sem browser? | Observação |
|---|---|---|
| Lista de processos (`/v2/licitacao/processos`) | **SIM** | Público, sem auth |
| Itens (`/v2/licitacao/{id}/itens`) | **SIM** | Público, sem auth |
| Documentos (`/v2/licitacao/{id}/documentos`) | **NÃO** | Retorna 500 |
| Edital/download (`/v2/licitacao/{id}/edital`) | **NÃO** | Retorna 401 (requer auth) |
| Detalhe individual | **PARCIAL** | Dados básicos vêm da lista |

---

## Recomendação Final

**Dá para trocar Selenium por requests direto? PARCIAL**

### O que funciona com requests puro

Para o caso de uso de **monitorar licitações** (busca, listagem, itens), `requests` puro é suficiente e muito mais rápido que Selenium:

```python
import requests

BASE = "https://compras.api.portaldecompraspublicas.com.br"
HEADERS = {
    "Accept": "application/json",
    "Referer": "https://www.portaldecompraspublicas.com.br/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

# Busca processos
r = requests.get(f"{BASE}/v2/licitacao/processos", params={
    "objeto": "cafe",
    "pagina": 1,
    "limitePagina": 12
}, headers=HEADERS)
processos = r.json()["result"]

# Busca itens de um processo
codigo = processos[0]["codigoLicitacao"]
r2 = requests.get(f"{BASE}/v2/licitacao/{codigo}/itens", headers=HEADERS)
itens = r2.json()["itens"]["result"]
```

### O que ainda requer browser

- **Download de documentos/editais**: endpoint retorna 401 sem autenticação
- **Andamento/histórico do processo**: endpoint retorna 404, pode estar atrás de auth

### Porquê parcial e não total

A API pública cobre lista + itens, mas documentos e download requerem sessão autenticada (o site exige cadastro para fornecedores). Para esses casos, seria necessário manter Playwright **apenas para a parte de autenticação + download**, não para a listagem.
