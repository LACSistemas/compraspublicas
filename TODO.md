# TODO — Webapp de Scraping + Auditoria LLM

Checklist exaustivo para execução literal pelo Claude Code (VSCode). Siga a ordem das fases. Cada item tem critério de "pronto" implícito na própria descrição — não pule para a fase seguinte sem validar a anterior.

> Referência completa de arquitetura: ver plano salvo na conversa anterior (estrutura de diretórios, schemas, endpoints). Este arquivo é o detalhamento tarefa-a-tarefa.

---

## Fase 0 — Setup do monorepo

- [x] Criar diretório `backend/` na raiz do repo.
- [x] Criar diretório `backend/app/`, `backend/app/routers/`, `backend/app/services/`, `backend/app/scraper/`, `backend/tests/`, `backend/data/`, `backend/downloads/`.
- [x] Criar `backend/app/__init__.py`, `backend/app/routers/__init__.py`, `backend/app/services/__init__.py`, `backend/app/scraper/__init__.py`, `backend/tests/__init__.py` (vazios).
- [x] Criar `backend/data/.gitkeep` e `backend/downloads/.gitkeep` (arquivos vazios, só pra manter as pastas no git).
- [x] Criar `backend/requirements.txt` com:
  ```
  fastapi
  uvicorn[standard]
  sqlalchemy
  pydantic-settings
  selenium
  pypdf
  pdfplumber
  google-genai
  python-dotenv
  ```
  (`google-generativeai` estava deprecado — substituído por `google-genai`, ver nota abaixo.)
- [x] Criar venv: `python3 -m venv backend/.venv` e instalar: `backend/.venv/bin/pip install -r backend/requirements.txt`. (Windows: `backend/.venv/Scripts/pip` em vez de `.venv/bin/pip` — ajustar comandos das fases seguintes.)
- [x] Verificar que o Chrome/Chromedriver está disponível no ambiente (Selenium Manager moderno baixa o driver automaticamente — testar com um script mínimo que abre `iniciar_driver()` headless e navega para `https://www.google.com`).
- [x] Copiar `prompt.md` da raiz para `backend/prompt.md` (cópia, não mover — manter original na raiz).
- [x] Criar `backend/.env.example`:
  ```
  GEMINI_API_KEY=
  GEMINI_MODEL=gemini-2.0-flash
  DATABASE_URL=sqlite:///./data/app.db
  MAX_PROCESSOS=10
  DOWNLOADS_DIR=downloads
  CORS_ORIGINS=http://localhost:3000
  ```
- [x] Copiar `backend/.env.example` para `backend/.env` (não versionado) e preencher `GEMINI_API_KEY` manualmente (pedir a key ao usuário se não tiver). **Pendente: usuário precisa preencher a chave antes da Fase 5** — `.env` da raiz só tinha `OPENAI_API_KEY`, não `GEMINI_API_KEY`.
- [x] Criar `backend/.gitignore`:
  ```
  .venv/
  __pycache__/
  *.pyc
  data/*.db
  downloads/*
  !downloads/.gitkeep
  .env
  ```
- [x] Rodar `npx create-next-app@latest frontend --typescript --app --tailwind --eslint --no-src-dir` na raiz do repo.
- [x] Dentro de `frontend/`, rodar `npx shadcn@latest init` (escolher estilo default, base color neutral ou similar).
- [x] Rodar `npx shadcn@latest add button card input label textarea badge table tabs accordion skeleton alert separator progress` dentro de `frontend/`.
- [x] Criar `frontend/.env.local.example` com `NEXT_PUBLIC_API_URL=http://localhost:8000` e copiar para `frontend/.env.local` (não versionado).
- [x] Atualizar `.gitignore` da raiz do repo para garantir que cobre `backend/.venv/`, `backend/data/*.db`, `backend/downloads/*`, `backend/.env`, `frontend/node_modules/`, `frontend/.next/`, `frontend/.env.local` (Next.js já gera um `.gitignore` razoável dentro de `frontend/`, mas confirmar).
- [x] **Checkpoint Fase 0**: `cd backend && .venv/Scripts/python -c "import fastapi, sqlalchemy, selenium, pypdf, pdfplumber; from google import genai"` sem erro, sem warnings; `cd frontend && npm run dev` sobe em `http://localhost:3000` mostrando a página default do Next.

> **Nota:** `google-generativeai` foi substituído por `google-genai` (o pacote antigo está deprecado e emitia `FutureWarning`). O código de exemplo da Fase 5 (`gemini_service.py`) neste arquivo usa a API antiga (`import google.generativeai as genai`, `genai.configure(...)`, `genai.GenerativeModel(...)`) — ao implementar a Fase 5, adaptar para a API nova: `from google import genai; client = genai.Client(api_key=...); client.models.generate_content(model=..., contents=...)`.

---

## Fase 1 — Adaptar o scraper isoladamente

- [x] Ler `initialscraping.py` da raiz por completo antes de começar a copiar (confirmar que as 340 linhas batem com o esperado). 340 linhas confirmadas.
- [x] Criar `backend/app/scraper/scraping_core.py`.
- [x] Copiar para esse arquivo, sem alterar a lógica interna, as funções: `fechar_banner_cookies`, `buscar_processos`, `parsear_processo`, `extrair_dados_processo`, `aguardar_download`, `baixar_documentos`, `salvar_json` (pode manter ou remover `salvar_json`, já que quem persiste agora é o backend — decisão: remover, pois persistência passa a ser responsabilidade do `scraper_service.py`). `salvar_json` removido.
- [x] Adaptar `iniciar_driver(headless: bool = True)`:
  - Manter `options.add_argument("--start-maximized")` apenas no ramo `else` (quando `headless=False`).
  - Quando `headless=True`, adicionar `options.add_argument("--headless=new")`, `options.add_argument("--disable-gpu")`, `options.add_argument("--window-size=1920,1080")`.
  - Manter toda a configuração de `prefs` de download já existente.
- [x] Adaptar `baixar_documentos(driver, url_processo, pasta_downloads_processo: str)`:
  - Trocar a construção interna do path (`PASTA_DOWNLOADS` + slug) para receber a pasta final já resolvida como parâmetro, em vez de montar a partir de uma constante global.
- [x] Criar a função de entrada nova:
  ```python
  def executar_scraping(termo: str, limite: int = 10, headless: bool = True, pasta_downloads_base: str = "downloads") -> dict:
  ```
  - Dentro: chama `iniciar_driver(headless)`, `buscar_processos(driver, termo)`, faz slice `cards[:limite]`, itera extraindo dados + chamando `baixar_documentos` com `pasta_downloads_base/<slug>`, acumula lista de processos.
  - Garantir `driver.quit()` dentro de `finally`, mesmo se exceção ocorrer no meio do loop.
  - Remover toda chamada a `input(...)`.
  - Retornar sempre `{"termo_busca": termo, "processos": [...], "erro": None}` em caso de sucesso, ou `{"termo_busca": termo, "processos": [...processados até a falha...], "erro": "<mensagem>"}` em caso de exceção capturada.
- [x] Trocar todos os `print(...)` por `logging.getLogger("scraper").info(...)` / `.warning(...)` / `.error(...)` conforme o caso. Adicionar `logging.basicConfig(level=logging.INFO)` apenas no bloco `if __name__ == "__main__":` do próprio arquivo (não no import), para não conflitar com a config de logging do Uvicorn.
- [x] Manter no final do arquivo um bloco `if __name__ == "__main__":` simples que chama `executar_scraping("cafe", limite=2, headless=True)` e faz `print(json.dumps(resultado, ensure_ascii=False, indent=2))`, só para teste manual rápido via terminal.
- [x] Criar `backend/tests/test_scraper_isolated.py`:
  ```python
  from app.scraper.scraping_core import executar_scraping
  import json

  if __name__ == "__main__":
      resultado = executar_scraping(termo="cafe", limite=2, headless=True, pasta_downloads_base="downloads/teste_isolado")
      print(json.dumps(resultado, ensure_ascii=False, indent=2)[:3000])
      print("Erro:", resultado.get("erro"))
      print("Total de processos:", len(resultado["processos"]))
  ```
- [x] Rodar `cd backend && .venv/bin/python -m tests.test_scraper_isolated` (executar da raiz de `backend/` para os imports relativos funcionarem; ajustar `PYTHONPATH` ou usar `python -m` conforme necessário). Windows: `.venv/Scripts/python`.
- [x] **Checkpoint Fase 1**: comando acima roda sem abrir janela visível do Chrome, sem travar esperando input, termina e imprime JSON com 2 processos e `erro: None`. Confirmado que `downloads/teste_isolado/<slug>/` foi criado com PDFs reais (depois removido — era só validação).

> **Bugs encontrados e corrigidos durante o teste headless** (não estavam nem na lógica original nem no enunciado da fase, mas quebravam o checkpoint):
> 1. **Cards duplicados**: `//a[contains(@class, "process-card__link")]` retorna 2 elementos por processo (um no título, outro no botão), ambos com o mesmo `href`. Com `headless=True` e `limite=2`, isso fazia `cards[:2]` apontar duas vezes para o **mesmo** processo. Corrigido deduplicando por `href` dentro de `buscar_processos` antes de retornar.
> 2. **Download de `downloads.htm` (~33MB)**: em modo headless, um dos cliques em `div.document-wrapper button` às vezes salva a própria página (SPA) como HTML em vez do PDF do documento — provavelmente um botão que não é realmente de download sendo capturado pelo mesmo seletor CSS nesse layout/viewport. Mitigado em `baixar_documentos` descartando (deletando do disco e não incluindo em `arquivos_baixados`) qualquer arquivo baixado com extensão `.htm`/`.html` (`EXTENSOES_INVALIDAS`). Esse mesmo bug provavelmente explicava os "Timeout ao baixar" intermitentes vistos antes da correção (o download gigante competia com os downloads reais dentro da janela de 30s do `aguardar_download`).

---

## Fase 2 — Banco de dados e modelos

- [x] Criar `backend/app/config.py`:
  ```python
  from pydantic_settings import BaseSettings, SettingsConfigDict

  class Settings(BaseSettings):
      GEMINI_API_KEY: str = ""
      GEMINI_MODEL: str = "gemini-3.5-flash"
      DATABASE_URL: str = "sqlite:///./data/app.db"
      MAX_PROCESSOS: int = 10
      DOWNLOADS_DIR: str = "downloads"
      CORS_ORIGINS: str = "http://localhost:3000"

      model_config = SettingsConfigDict(env_file=".env")

  settings = Settings()
  ```
  (usado `model_config = SettingsConfigDict(...)` em vez de `class Config:` aninhada — a forma antiga está deprecada no Pydantic v2 instalado aqui.) `.env`/`.env.example` atualizados para `GEMINI_MODEL=gemini-3.5-flash` também.
- [x] Criar `backend/app/database.py`:
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker, declarative_base
  from app.config import settings

  engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
  SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
  Base = declarative_base()

  def get_db():
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```
- [x] Criar `backend/app/models.py` com as classes `Pesquisa` e `Analise` exatamente conforme o schema do plano (colunas: ver plano salvo — `id, termo_busca, quantidade_desejada, limite_processos, status, erro_mensagem, resultado_json, pasta_downloads, criado_em, atualizado_em` para `Pesquisa`; `id, pesquisa_id (FK), status, erro_mensagem, resultado_json, modelo_gemini, criado_em, atualizado_em` para `Analise`, com `relationship` 1:N e `cascade="all, delete-orphan"`).
- [x] Criar `backend/app/schemas.py` com Pydantic models:
  - `PesquisaCreate(BaseModel)`: `termo_busca: str` (min_length=1), `quantidade_desejada: str | None = None`.
  - `PesquisaStatusOut(BaseModel)`: `id: int, status: str, erro_mensagem: str | None`.
  - `PesquisaDetailOut(BaseModel)`: todos os campos de `Pesquisa` + `resultado: dict | None` (parseado de `resultado_json`).
  - `PesquisaListItemOut(BaseModel)`: campos resumidos para listagem.
  - `AnaliseStatusOut(BaseModel)`: `id: int, status: str, erro_mensagem: str | None, resultado: dict | None, modelo_gemini: str | None`.
  - Usar `model_config = {"from_attributes": True}` em todos para permitir `.model_validate(orm_obj)`.
- [x] Criar script utilitário rápido (pode ser dentro de `backend/app/main.py` via evento de startup, ver Fase 3) que chama `Base.metadata.create_all(bind=engine)`.
- [x] Para testar isoladamente nesta fase, criar um script temporário `backend/tests/_check_db.py` (pode deletar depois) que importa `Base`, `engine` e chama `create_all`.
- [x] Rodar `cd backend && .venv/bin/python -m tests._check_db` (ou equivalente) e depois `sqlite3 backend/data/app.db ".tables"` no terminal para confirmar que `pesquisas` e `analises` existem com as colunas certas (`sqlite3 backend/data/app.db ".schema pesquisas"`). Sem `sqlite3` CLI disponível no ambiente — inspecionado via módulo `sqlite3` do Python (`PRAGMA table_info`, `PRAGMA foreign_key_list`) com o mesmo resultado.
- [x] **Checkpoint Fase 2**: tabelas `pesquisas` e `analises` criadas com as colunas e FK corretas, sem erros de import circular entre `models.py`/`database.py`/`config.py`.

---

## Fase 3 — Endpoints de pesquisa (scraping em background)

> **Porta do backend: 8001, não 8000.** Já existe um processo Python alheio (não relacionado a este projeto) ocupando a porta 8000 na máquina de desenvolvimento; por instrução do usuário, esse processo foi deixado intocado e o backend passou a usar **8001** (não usar 8080 também, por instrução do usuário). `frontend/.env.local` e `frontend/.env.local.example` já atualizados para `NEXT_PUBLIC_API_URL=http://localhost:8001`. Todos os comandos abaixo usam `:8001`.

- [x] Criar `backend/app/services/scraper_service.py`:
  - Função `executar_e_persistir(pesquisa_id: int, termo: str, limite: int)`:
    - Abre nova `Session` própria (`SessionLocal()`).
    - Busca a `Pesquisa` pelo id, seta `status="em_andamento"`, commit.
    - Resolve `pasta_downloads = f"downloads/{pesquisa_id}"`.
    - Chama `executar_scraping(termo, limite, headless=True, pasta_downloads_base=pasta_downloads)`.
    - Se `resultado["erro"]` for `None`: seta `status="completo"`, `resultado_json=json.dumps(resultado, ensure_ascii=False)`, `pasta_downloads=pasta_downloads`.
    - Se houver erro: seta `status="erro"`, `erro_mensagem=resultado["erro"]`, ainda salva o `resultado_json` parcial se houver processos.
    - Commit final, fecha sessão em `finally`.
    - Adicionado também um `try/except` externo cobrindo a função inteira (não estava no enunciado): como isso roda numa thread solta sem nenhum caller pra capturar exceção, um erro inesperado antes do `executar_scraping` (ex: falha de DB) deixaria a `Pesquisa` travada em `"em_andamento"` pra sempre. Agora qualquer exceção não tratada marca `status="erro"`.
- [x] Criar `backend/app/services/job_runner.py` (igual ao enunciado).
- [x] Criar `backend/app/routers/pesquisas.py` com `POST /pesquisas`, `GET /pesquisas`, `GET /pesquisas/{id}`, `GET /pesquisas/{id}/status`, `GET /pesquisas/{id}/documentos/{nome_arquivo:path}` (com proteção de path traversal via `os.path.realpath`).
- [x] Criar `backend/app/main.py` — com uma diferença do enunciado: usado `lifespan` (context manager `@asynccontextmanager`) em vez de `@app.on_event("startup")`, que está deprecado nesta versão do FastAPI (0.138.1):
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      Base.metadata.create_all(bind=engine)
      yield

  app = FastAPI(lifespan=lifespan)
  ```
- [x] `analises.py` criado só com `router = APIRouter(tags=["analises"])` vazio (sem endpoints) — será preenchido na Fase 6.
- [x] Rodar `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8001` (Windows: `.venv/Scripts/python -m uvicorn`, sem `--reload` neste teste manual).
- [x] Testar via terminal:
  ```bash
  curl -X POST http://localhost:8001/pesquisas -H "Content-Type: application/json" -d '{"termo_busca":"cafe","quantidade_desejada":"2 toneladas"}'
  ```
  → `{"id":1,"status":"pendente","erro_mensagem":null}`
  ```bash
  curl http://localhost:8001/pesquisas/1/status
  ```
  → `{"id":1,"status":"completo","erro_mensagem":null}` (esperou o scraping de 10 processos terminar em background).
  ```bash
  curl http://localhost:8001/pesquisas/1
  ```
  → `resultado.processos` com 10 itens, mesmas chaves de `resultados.json` da raiz (`url, numero_processo, situacao, comprador, modalidade, objeto, informacoes, datas, documentos, itens, andamento, conteudo_bruto, arquivos_baixados`).
  ```bash
  curl http://localhost:8001/pesquisas
  ```
  → pesquisa aparece na lista.
  Testes extra: download real de documento via `GET /pesquisas/1/documentos/<arquivo>` → 200 OK; tentativa de path traversal (`../../app/config.py`) → 404; pesquisa inexistente (`/pesquisas/999`) → 404.
- [x] **Checkpoint Fase 3**: fluxo completo via curl funciona, dados batem com o formato esperado (10 processos, 35 arquivos reais baixados, sem duplicados, sem `downloads.htm` bogus), downloads aparecem em `backend/downloads/1/<slug>/`.

---

## Fase 4 — Extração de PDF isolada

- [x] Criar `backend/app/services/pdf_extractor.py`:
  ```python
  def _extrair_com_pypdf(caminho: str) -> str: ...
  def _extrair_com_pdfplumber(caminho: str) -> str: ...

  def extrair_texto_pdf(caminho_arquivo: str) -> dict:
      # retorna {"texto": str, "status": "ok"|"vazio_possivelmente_escaneado"|"erro", "metodo": str|None, "erro": str|None}
      ...

  def extrair_textos_da_pasta(pasta: str) -> dict:
      # varre recursivamente todos os .pdf dentro de `pasta`, retorna {nome_relativo: resultado_extrair_texto_pdf}
      ...
  ```
  - Implementado `_extrair_com_pypdf` usando `pypdf.PdfReader`, concatenando `page.extract_text() or ""` de todas as páginas.
  - Implementado `_extrair_com_pdfplumber` usando `pdfplumber.open`, concatenando `page.extract_text() or ""`.
  - Em `extrair_texto_pdf`: tenta pypdf primeiro; se `len(texto.strip()) < 50`, tenta pdfplumber; se ainda `< 50`, status `vazio_possivelmente_escaneado` (usando o texto parcial de qualquer um dos dois que tenha retornado algo); status `erro` só quando **ambos** os métodos lançam exceção (uma exceção isolada em um deles, com o outro retornando texto curto sem erro, ainda conta como `vazio_possivelmente_escaneado`, não `erro` — leitura literal do "se qualquer exceção em ambos").
- [x] Criar `backend/tests/test_pdf_extractor_isolated.py` (igual ao enunciado).
- [x] Rodar apontando para uma pasta real de downloads gerada na Fase 3 (`downloads/1`, com os 35 arquivos baixados naquele teste):
  ```bash
  cd backend && .venv/Scripts/python -m tests.test_pdf_extractor_isolated downloads/1
  ```
- [x] **Checkpoint Fase 4**: todos os 31 PDFs nativos retornaram `status=ok` com `len > 0`; os 2 PDFs escaneados do lote real (`DECISÃO.pdf`, `DECISÃO RECURSO.pdf`, de `rpe-50-2026-2026-490064`) retornaram corretamente `vazio_possivelmente_escaneado` com `len=0` em vez de `erro`. (O `.rar` baixado nesse mesmo processo foi ignorado corretamente por `extrair_textos_da_pasta`, que só varre `.pdf`.)

---

## Fase 5 — Integração Gemini isolada

> **Limites de token (instrução do usuário):** input ≤ 1.000.000 tokens, output ≤ 300.000 tokens por chamada, e consciência explícita do gasto de cada tarefa. `gemini_service.py` usa `google-genai` (não `google-generativeai`, deprecado — ver nota da Fase 0) e implementa os dois limites como guardas reais: `count_tokens` roda **antes** de qualquer chamada de geração (cobrança mínima/gratuita) e aborta com erro se o input estimado passar de 1M; `max_output_tokens=300_000` é passado em todo `generate_content`. O uso real (`usage_metadata.prompt_token_count` / `candidates_token_count` / `total_token_count`) é logado em toda chamada.

- [x] Confirmar `GEMINI_API_KEY` preenchida em `backend/.env`. (já estava preenchida pelo usuário antes desta fase.)
- [x] Criar `backend/app/services/gemini_service.py` — adaptado pra `google-genai`:
  ```python
  from google import genai
  from google.genai import types
  from app.config import settings

  LIMITE_TOKENS_INPUT = 1_000_000
  LIMITE_TOKENS_OUTPUT = 300_000

  def carregar_prompt_base() -> str: ...   # caminho absoluto via os.path.dirname(__file__)
  def montar_prompt_final(...) -> str: ...
  def _extrair_json_da_resposta(texto: str) -> dict: ...

  def contar_tokens_input(prompt: str) -> int:
      client = genai.Client(api_key=settings.GEMINI_API_KEY)
      return client.models.count_tokens(model=settings.GEMINI_MODEL, contents=prompt).total_tokens

  def chamar_gemini(prompt: str) -> dict:
      client = genai.Client(api_key=settings.GEMINI_API_KEY)
      tokens_input = contar_tokens_input(prompt)
      if tokens_input > LIMITE_TOKENS_INPUT:
          raise ValueError(...)  # aborta ANTES de chamar generate_content
      response = client.models.generate_content(
          model=settings.GEMINI_MODEL,
          contents=prompt,
          config=types.GenerateContentConfig(
              response_mime_type="application/json",
              max_output_tokens=LIMITE_TOKENS_OUTPUT,
          ),
      )
      logger.info(f"Tokens reais — input: {response.usage_metadata.prompt_token_count:,} | output: {response.usage_metadata.candidates_token_count:,}")
      return _extrair_json_da_resposta(response.text)
  ```
  - `carregar_prompt_base` usa `os.path.join(os.path.dirname(__file__), "..", "..", "prompt.md")` (caminho absoluto, não depende do cwd), como recomendado.
  - API real do `google-genai` v2.10.0 confirmada por introspecção antes de implementar (`client.models.count_tokens`, `client.models.generate_content(config=GenerateContentConfig(...))`, `CountTokensResponse.total_tokens`, `GenerateContentResponseUsageMetadata.{prompt_token_count,candidates_token_count,total_token_count}`).
- [x] Criar `backend/tests/test_gemini_isolated.py` (igual ao enunciado).
- [x] Rodar `cd backend && .venv/Scripts/python -m tests.test_gemini_isolated`. **Antes de rodar**, fez um dry-run só de `contar_tokens_input` (sem `generate_content`, custo ~zero) pra confirmar a margem de segurança: prompt de teste (1 processo + texto de PDF fictício) = 15.825 tokens de input, bem abaixo do limite.
- [x] Comparar as chaves de topo retornadas com o schema esperado em `prompt.md`: **bateu exatamente** — `metadados, documentos_auditados, documentos_ausentes, itens, classificacao_checklist, constatacoes, dicas_aprimoramento, recomendacoes_consolidadas, quadro_sintese`.
- [x] **Checkpoint Fase 5**: chamada real bem-sucedida, JSON parseado sem exceção, todas as 9 chaves de topo presentes e com conteúdo coerente (não vazio) mesmo com input de teste reduzido.

> **Achado importante para a Fase 6 (ainda não resolvido, decisão pendente do usuário):** o teste isolado usa um texto de PDF fictício (~50 chars) de propósito, pra ficar barato. Comparando com dados reais (PDFs de verdade extraídos na Fase 4, do mesmo processo usado no teste): o prompt com texto fictício deu **15.825 tokens**; o mesmo prompt com os **9 documentos reais** desse único processo (293.100 caracteres extraídos) deu **108.838 tokens** — quase 93k tokens extras só por 1 processo. A Fase 6, como especificada, monta **um único prompt com todos os processos de uma pesquisa (até `MAX_PROCESSOS=10`) + todos os PDFs baixados**. Se a média por processo for parecida, 10 processos podem facilmente ultrapassar os 1.000.000 de tokens de input — o limite duro definido pelo usuário. **Antes de implementar a Fase 6, decidir**: (a) truncar/resumir texto de PDFs muito longos, (b) limitar quantidade de documentos por processo incluídos no prompt, (c) dividir a análise em uma chamada por processo em vez de uma chamada por pesquisa inteira, ou (d) alguma combinação. O guard de `contar_tokens_input > LIMITE_TOKENS_INPUT` em `chamar_gemini` já existe e vai abortar a chamada com erro claro em vez de deixar passar, mas isso só evita gasto indevido — não resolve o problema de a análise falhar pra pesquisas com muitos processos/documentos grandes.

---

## Fase 6 — Endpoints de análise

> **Redesenho pós-Fase 5 (decisão do usuário, 3 iterações):**
> 1. Descartado: 1 chamada Gemini pra pesquisa inteira sem nenhum tratamento — 1 único processo com PDFs reais já consome ~109k tokens, e com `MAX_PROCESSOS=10` estouraria o limite de 1M.
> 2. Descartado: 1 chamada por processo (sem resumo) — usuário achou ruim repetir o overhead do `prompt.md` em N chamadas (estimativa inicial errada de ~45k tokens de overhead — na real são só ~13.5k tokens, confundi caracteres com tokens).
> 3. **Tentativa 3 (parcialmente certa, schema errado):** resumir/comprimir PDFs grandes via Gemini + manter 1 única chamada final consolidada para a pesquisa inteira (todos os processos juntos). Implementado e testado de verdade — **revelou um bug real, não de token**: com `pesquisa_id=2` (2 processos, 10 documentos), a chamada consolidada **ignorou completamente o segundo processo**, retornando dados só do processo com mais documentos. Causa raiz: a Seção 23 do `prompt.md` ("REGRAS ESPECÍFICAS PARA SCRAPING") já instruía o modelo a, havendo múltiplos processos, **selecionar só o mais relevante** — e a Seção 20 (schema de saída) só tinha campos para 1 processo (`metadados`, `itens` etc. todos singulares). Não era questão de token, era o prompt pedindo exatamente esse comportamento.
> 4. **Decisão final:** manter a etapa de resumo de PDFs grandes (funciona bem, validada) + manter 1 única chamada final consolidada, mas **corrigir o `prompt.md`** (raiz do repo e cópia em `backend/prompt.md`, mantidas sincronizadas) pra gerar uma auditoria completa por processo dentro da mesma chamada:
>    - Seção 20: schema de saída agora é `{"processos_auditados": [ {...schema antigo, agora com "url" e dentro de cada item...} ]}` — uma lista com 1 item completo por processo, sempre, mesmo com 1 processo só.
>    - Seção 23, itens 5-8: trocado "selecione o mais relevante" por "audite todos, sem exceção; o critério de relevância da seção 23.7 serve só pra ordenar a apresentação, nunca pra excluir processo da saída JSON"; processo com poucos documentos gera entrada com limitação registrada (seção 27), não é omitido.
>    - Resto do `prompt.md` (checklist, anti-alucinação, classificações etc.) **não foi tocado**.
>
> **Números reais medidos** (pesquisa "cafe" com `MAX_PROCESSOS=2`, 2 processos, 10 documentos, 7 precisando resumo por passarem de `LIMITE_RESUMO_CHARS=6000`): **125.422 tokens** nas 7 chamadas de resumo + **24.558 tokens** na chamada final consolidada (20.736 input + 3.822 output) = **~150k tokens no total** — bem menor que a estimativa inicial de ~230k (a estimativa por "chars/4" enganou; a proporção real ficou mais perto de 3.1-3.3 chars/token, e a chamada final ficou pequena porque os resumos são compactos). Resultado validado: os 2 processos apareceram em `processos_auditados`, inclusive o de 1 documento só (com `documentos_ausentes` listando ETP/TR/Pesquisa de Preços/Mapa de Riscos corretamente, em vez de ser descartado).

- [x] Adicionar em `backend/app/services/gemini_service.py`:
  - `LIMITE_RESUMO_CHARS = 6000` (ajustado de 3000 por pedido do usuário; não reduziu muito a quantidade de chamadas de resumo porque o volume vem de poucos editais enormes, não dos documentos médios).
  - `resumir_documento(nome_arquivo, texto) -> str`: prompt curto de extração/resumo focado em dados relevantes pra auditoria, `max_output_tokens=2000`, loga tokens de cada chamada via `contar_tokens_input` + `usage_metadata`.
  - `resumir_textos_pdfs(textos_pdfs: dict) -> dict`: resume só entradas `status == "ok"` com `len(texto) > LIMITE_RESUMO_CHARS`; passa o resto direto. Validado com 1 documento isolado antes de rodar em lote (custo real: 3.617 input + 696 output = 5.613 tokens pra um PDF de 7.034 chars).
- [x] Editar `prompt.md` (raiz + cópia em `backend/prompt.md`) pra suportar múltiplos processos numa única chamada — Seções 20 e 23, conforme descrito acima.
- [x] Criar `backend/app/services/analise_service.py` com `executar_analise(analise_id, pesquisa_id)`: 1 chamada final por análise (não por processo), usando `resumir_textos_pdfs` antes de `montar_prompt_final`. Mesmo formato de persistência do plano original (`Analise.status`, `resultado_json`, `modelo_gemini`).
- [x] Atualizado `backend/app/services/job_runner.py` com `iniciar_job_analise`.
- [x] Preenchido `backend/app/routers/analises.py`:
  - `POST /pesquisas/{id}/analise`: 404 se pesquisa não existe, 409 se `status != "completo"`, 409 se já há análise pendente/em andamento, senão cria e dispara o job, retorna 202.
  - `GET /pesquisas/{id}/analise`: análise mais recente da pesquisa, 404 se nenhuma existir, `resultado` parseado de `resultado_json`.
- [x] Corrigido um gap de observabilidade encontrado durante o teste: `logger.info(...)` dos services nunca aparecia no console do `uvicorn` (só os loggers `uvicorn.*` tinham handler) — adicionado `logging.basicConfig(...)` em `backend/app/main.py` pra todos os logs de tokens/progresso aparecerem em qualquer execução via servidor, não só nos scripts de teste isolados.
- [x] Testado via curl com pesquisa real (`pesquisa_id=2`, criada com `MAX_PROCESSOS=2` temporário pra controlar custo — restaurado para `10` depois do teste):
  ```bash
  curl -X POST http://localhost:8001/pesquisas/2/analise
  curl http://localhost:8001/pesquisas/2/analise   # repetido até status=completo
  ```
  `processos_auditados` com 2 itens, ambos com conteúdo correto (checklist, constatações, quadro síntese), nenhum processo descartado.
- [x] **Checkpoint Fase 6**: ciclo completo scraping → análise funciona via curl puro, sem frontend. Validado num subconjunto (2 processos) por causa do custo; **a validação no `MAX_PROCESSOS=10` completo (10 processos, 35 documentos) ainda não foi rodada** — ficou pendente, a critério do usuário, dado que o subconjunto já comprovou a correção do schema e deu uma medição real de custo por documento/processo pra extrapolar com confiança.

---

## Fase 7 — Frontend: tipos, client de API e formulário

> **Nota sobre a stack de UI:** o `components.json` deste projeto usa shadcn com Base UI (`@base-ui/react/*`), não Radix UI — `asChild` (padrão Radix) não existe aqui; o padrão correto é a prop `render` (ex.: `<Button render={<Link href="...">Texto</Link>} />`). Confirmado lendo `node_modules/@base-ui/react/button/Button.d.ts` antes de escrever os componentes, por causa do aviso em `frontend/AGENTS.md` de que essa versão (Next.js 16.2.9) pode ter convenções diferentes do treinamento. Também checados localmente: Async Request APIs (`params`/`searchParams` agora sempre assíncronos — não afeta esta fase, nenhuma rota dinâmica ainda) e que `<Link>`/`useRouter` de `next/navigation` seguem iguais.

- [x] Criar `frontend/lib/types.ts` espelhando os schemas Pydantic (`Pesquisa`, `PesquisaDetalhe`, `Processo`, `Documento`, `Item`, `Andamento`, `Analise`). `AnaliseResultado` reflete o schema **corrigido na Fase 6** (`{ processos_auditados: ProcessoAuditado[] }`, não os 9 campos direto no topo — cada `ProcessoAuditado` tem os 9 campos).
- [x] Criar `frontend/lib/api-client.ts` com `criarPesquisa`, `listarPesquisas`, `getPesquisa`, `getPesquisaStatus`, `dispararAnalise`, `getAnalise`, todas via um helper `request<T>()` com `cache: "no-store"` (dados mudam de status com frequência, não dá pra deixar o Next cachear).
- [x] Criar `frontend/components/pesquisa-form.tsx` (`"use client"`) com `Input` + `Textarea` + `Button`, estado de loading e erro (`Alert`), `router.push` para `/pesquisas/${id}` em sucesso.
- [x] Criar `frontend/app/nova-pesquisa/page.tsx` com `<PesquisaForm />` dentro de `Card`.
- [x] Criar `frontend/components/pesquisa-lista.tsx`: `Table` com Termo, Quantidade Desejada, `Badge` colorido por status (`pendente`=outline, `em_andamento`=secondary, `completo`=default, `erro`=destructive), Data formatada em pt-BR, link "Ver".
- [x] Criar `frontend/app/pesquisas/page.tsx` como **server component async** (`await listarPesquisas()` direto, sem necessidade de client-side loading state pra uma listagem simples).
- [x] Ajustado `frontend/app/page.tsx` (home) com título/descrição em português e botões para `/nova-pesquisa` e `/pesquisas`. Também corrigido `frontend/app/layout.tsx`: `lang="en"` → `"pt-BR"`, metadata title/description que ainda eram do template padrão do `create-next-app`.
- [x] `npx tsc --noEmit` sem erros antes de testar no navegador.
- [x] **Checkpoint Fase 7**: com backend rodando (`:8001`) e `npm run dev` (`:3000`), as 3 páginas (`/`, `/nova-pesquisa`, `/pesquisas`) respondem HTTP 200. `/pesquisas` renderiza dados reais do backend via SSR — confirmado via `curl` que a tabela mostra as 2 pesquisas reais já existentes (`termo_busca="cafe"`, `quantidade_desejada="2 toneladas"`, status `completo`, links "Ver"), sem precisar de teste manual no formulário (criação de pesquisa real já validada nas Fases 3/6 via curl direto no backend). Sem ferramenta de browser disponível no ambiente para screenshot/clique interativo — validação feita via SSR + curl + `tsc`.

---

## Fase 8 — Frontend: tela de detalhe com polling

> **Nota:** rota dinâmica nova (`app/pesquisas/[id]/page.tsx`) — primeira a usar `params`. Confirmado nos docs locais (`node_modules/next/dist/docs/.../page.md`) que em Next 16, `params` é `Promise<{...}>` mesmo em Client Component; a forma correta é `const { id } = use(params)` (`use` do React), não `await` (Client Component não pode ser `async`).

- [x] Criar `frontend/lib/use-pesquisa-polling.ts`: hook genérico `usePolling({ fetchFn, intervalMs, shouldStop })`. `fetchFn`/`shouldStop` são guardados em `useRef` e lidos a cada tick em vez de entrarem no array de dependências do `useEffect` — isso evita um bug comum desse tipo de hook (reiniciar o polling do zero a cada render porque o caller passou uma arrow function inline com identidade nova).
- [x] Criar `frontend/components/pesquisa-status-card.tsx`: spinner (`Loader2` do lucide-react, `animate-spin`) + texto por status; `Alert variant="destructive"` se `erro`.
- [x] Criar `frontend/components/processo-card.tsx` com `Card`, `Badge` de situação, tabelas de `informacoes`/`datas` (genérica chave-valor) e tabela de `itens` com cabeçalho próprio.
- [x] Criar `frontend/components/conteudo-bruto-viewer.tsx` com `Accordion` (1 item por processo) + `<pre>` scrollável.
- [x] Criar `frontend/components/documentos-lista.tsx`. **Detalhe importante:** `arquivos_baixados[].pasta` é um caminho absoluto do filesystem do servidor (ex: `C:\...\backend\downloads\2\rpe-33...`) — não pode ser usado para montar a URL do frontend. A rota de download espera o caminho relativo a `pasta_downloads` da pesquisa (`{slug-do-processo}/{nome-do-arquivo}`), então o slug é recalculado a partir de `processo.url` (mesma lógica do `_slug_do_processo` do backend) e cada segmento do caminho é codificado separadamente com `encodeURIComponent` antes de juntar com `/` literal (porque codificar a barra separadora quebraria a rota `{nome_arquivo:path}` do FastAPI).
- [x] Criar `frontend/components/analise-trigger-button.tsx` como placeholder (`disabled`) — implementação real fica pra Fase 9, conforme já previsto no enunciado.
- [x] Criar `frontend/app/pesquisas/[id]/page.tsx` (`"use client"`) com `usePolling` a cada 3000ms parando em `completo`/`erro`; estados tratados: carregando inicial, erro de polling, `erro` da pesquisa, `pendente`/`em_andamento` (via `PesquisaStatusCard`), `completo` com busca adicional de `getPesquisa` (com seu próprio loading/erro), e o resultado final com `Tabs` (Dados Organizados / Dados Brutos / Documentos).
- [x] `npx tsc --noEmit` sem erros.
- [x] **Checkpoint Fase 8**: sem ferramenta de browser no ambiente para clicar de fato no formulário e observar a transição visualmente. Validado por outras vias: (1) a página em `/pesquisas/2` (pesquisa real já `completo`) renderiza sem erro de servidor; (2) o shape de `GET /pesquisas/{id}` foi comparado campo a campo com os tipos TS e bate exatamente; (3) a URL de download montada pela lógica do `documentos-lista.tsx` foi reproduzida manualmente (mesma codificação por segmento) e baixou o arquivo real com sucesso (HTTP 200, 1.2MB) — achei um 404 nesse teste primeiro, mas era um erro de digitação meu no comando de teste (encoding duplicado), não um bug do código; corrigido o teste e confirmado que a lógica está certa. O ciclo `pendente → em_andamento → completo` via polling em si (Fases 3/6) já foi validado via curl com timing real; o que não foi observado diretamente é a transição de UI no navegador.

---

## Fase 9 — Frontend: disparo e exibição da análise

> **Nota:** `AnaliseResultadoView` adaptada pro schema corrigido na Fase 6 — `AnaliseResultado` é `{ processos_auditados: ProcessoAuditado[] }`, não os 9 campos direto no topo. Cada `ProcessoAuditado` (com os 9 campos: `metadados`, `documentos_auditados`, `documentos_ausentes`, `itens`, `classificacao_checklist`, `constatacoes`, `dicas_aprimoramento`, `recomendacoes_consolidadas`, `quadro_sintese`) é renderizado em sequência por um sub-componente interno `ProcessoAuditadoView`.

- [x] Criar `frontend/components/analise-trigger-button.tsx` real: checa `getAnalise` no mount (404 = nenhuma ainda, ignorado), desabilita e mostra "Ver análise em andamento" se já houver uma `pendente`/`em_andamento`; senão chama `dispararAnalise` e navega para a tela de análise.
- [x] Placeholder da Fase 8 substituído (o componente já estava importado em `pesquisas/[id]/page.tsx`; só o conteúdo interno mudou).
- [x] Criar `frontend/components/analise-resultado-view.tsx`. Cores de `classificacao` (C/PC/NC/N/A) e `risco` usam a **mesma paleta hexadecimal da Seção 22 do `prompt.md`** (padrão visual do DOCX: verde `#2e7d32`, laranja `#b45309`, vermelho `#c62828`, cinza `#6b7280`), pra manter consistência entre o webapp e o relatório exportado — decisão de design não pedida explicitamente no enunciado, mas natural dado que o prompt já define essa paleta.
- [x] Criar `frontend/app/pesquisas/[id]/analise/page.tsx`, mesmo padrão de `use(params)` + `usePolling` da Fase 8. Botão "Tentar novamente" no estado de erro recarrega a página via `window.location.reload()` após disparar nova análise (forma simples de reiniciar o polling do zero).
- [x] `npx tsc --noEmit` sem erros. Validado contra a análise real já existente (pesquisa 2, análise 2, da Fase 6): todos os nomes de campo batem exatamente com os tipos TS (`metadados`, `quadro_sintese`, `classificacao_checklist`, `constatacoes` com `risco`/`classificacao` nos valores exatos esperados pelas tabelas de cor).
- [x] **Checkpoint Fase 9**: sem ferramenta de browser disponível pra clicar de fato no botão e ver a navegação — validado por outras vias: rotas `/pesquisas/2/analise` respondem 200 sem erro de servidor, `tsc` limpo, e os dados reais retornados pelo backend foram conferidos campo a campo contra os tipos e a lógica de cor do componente.

> **Achado durante a validação (fora do escopo desta fase, ainda não corrigido):** o campo `grau_risco_geral` de um dos processos veio como `"Cr\xc3\x83\xc2\xadtico"` em vez de `"Crítico"` — um bug real de **duplo encoding UTF-8** (bytes UTF-8 de "í" reinterpretados como Latin-1 e re-codificados). Rastreado até a origem: o mesmo padrão já existe no dado **bruto raspado** guardado em `resultado_json` da `Pesquisa` (`"22/06/2026 �s 16:13"` em vez de `"...às 16:13"`, confirmado direto no SQLite, sem o Gemini no meio) — ou seja, o bug é introduzido em algum ponto da Fase 1 (`scraping_core.py` / texto retornado por `driver.find_element(...).text` do Selenium), não na Fase 9 nem na integração Gemini. A hipótese é que o Gemini só está **reproduzindo** esse padrão de corrupção que já existe no texto raspado fornecido como contexto (LLMs tendem a imitar grafias incomuns vistas no próprio prompt). Não corrigido ainda — decisão de quando/se investigar fica para o usuário, já que envolve reabrir a Fase 1 e não afeta a estrutura do JSON (só a legibilidade de alguns caracteres acentuados específicos: `à`, `í`, e possivelmente outros com o segundo byte UTF-8 na mesma faixa).

---

## Fase 10 — Polimento e documentação

- [ ] Revisar `frontend` e `backend` `.gitignore` mais uma vez, confirmar `git status` não lista `.env`, `.env.local`, `node_modules/`, `.venv/`, `data/*.db`, `downloads/*` (exceto `.gitkeep`).
- [ ] Criar `README.md` na raiz explicando: visão geral do projeto, como instalar backend (`venv` + `pip install -r requirements.txt` + copiar `.env.example`), como instalar frontend (`npm install` + copiar `.env.local.example`), como rodar os dois (`uvicorn app.main:app --reload` e `npm run dev`), e o fluxo de uso (nova pesquisa → aguardar → ver dados → disparar análise → ver relatório).
- [ ] Criar `backend/README.md` com detalhes específicos do backend: comandos de teste isolado de cada fase (scraper, pdf, gemini), variáveis de ambiente necessárias.
- [ ] Revisar mensagens de erro do usuário final (status `erro` em pesquisa/análise) garantindo que `erro_mensagem` não exponha stack trace completo nem a `GEMINI_API_KEY` por acidente em nenhum log/response.
- [ ] **Checkpoint Fase 10**: seguindo só o `README.md` do zero (em uma pasta limpa, se possível, ou mentalmente), é possível rodar o projeto completo ponta a ponta.

---

## Verificação final end-to-end (rodar manualmente após Fase 9/10)

- [ ] Com backend (`:8000`) e frontend (`:3000`) rodando, abrir `/nova-pesquisa`.
- [ ] Preencher termo de busca real (ex: "cafe") e quantidade desejada (ex: "2 toneladas").
- [ ] Confirmar transição automática até a tela de "Pesquisa Completa".
- [ ] Verificar aba "Dados Organizados" mostrando processos com todos os campos.
- [ ] Verificar aba "Dados Brutos" mostrando o `conteudo_bruto`.
- [ ] Verificar aba "Documentos" com links de download funcionando (abrir/baixar um PDF pelo link).
- [ ] Clicar em "Condensar e enviar pra LLM".
- [ ] Aguardar polling da análise e confirmar relatório de auditoria renderizado de forma organizada, com checklist, constatações e quadro síntese visíveis e legíveis.
- [ ] Repetir o fluxo uma segunda vez com termo diferente para confirmar que múltiplas pesquisas convivem sem conflito de dados/pastas.
