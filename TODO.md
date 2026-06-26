# TODO — Webapp de Scraping + Auditoria LLM

Checklist exaustivo para execução literal pelo Claude Code (VSCode). Siga a ordem das fases. Cada item tem critério de "pronto" implícito na própria descrição — não pule para a fase seguinte sem validar a anterior.

> Referência completa de arquitetura: ver plano salvo na conversa anterior (estrutura de diretórios, schemas, endpoints). Este arquivo é o detalhamento tarefa-a-tarefa.

---

## Fase 0 — Setup do monorepo

- [ ] Criar diretório `backend/` na raiz do repo.
- [ ] Criar diretório `backend/app/`, `backend/app/routers/`, `backend/app/services/`, `backend/app/scraper/`, `backend/tests/`, `backend/data/`, `backend/downloads/`.
- [ ] Criar `backend/app/__init__.py`, `backend/app/routers/__init__.py`, `backend/app/services/__init__.py`, `backend/app/scraper/__init__.py`, `backend/tests/__init__.py` (vazios).
- [ ] Criar `backend/data/.gitkeep` e `backend/downloads/.gitkeep` (arquivos vazios, só pra manter as pastas no git).
- [ ] Criar `backend/requirements.txt` com:
  ```
  fastapi
  uvicorn[standard]
  sqlalchemy
  pydantic-settings
  selenium
  pypdf
  pdfplumber
  google-generativeai
  python-dotenv
  ```
- [ ] Criar venv: `python3 -m venv backend/.venv` e instalar: `backend/.venv/bin/pip install -r backend/requirements.txt`.
- [ ] Verificar que o Chrome/Chromedriver está disponível no ambiente (Selenium Manager moderno baixa o driver automaticamente — testar com um script mínimo que abre `iniciar_driver()` headless e navega para `https://www.google.com`).
- [ ] Copiar `prompt.md` da raiz para `backend/prompt.md` (cópia, não mover — manter original na raiz).
- [ ] Criar `backend/.env.example`:
  ```
  GEMINI_API_KEY=
  GEMINI_MODEL=gemini-2.0-flash
  DATABASE_URL=sqlite:///./data/app.db
  MAX_PROCESSOS=10
  DOWNLOADS_DIR=downloads
  CORS_ORIGINS=http://localhost:3000
  ```
- [ ] Copiar `backend/.env.example` para `backend/.env` (não versionado) e preencher `GEMINI_API_KEY` manualmente (pedir a key ao usuário se não tiver).
- [ ] Criar `backend/.gitignore`:
  ```
  .venv/
  __pycache__/
  *.pyc
  data/*.db
  downloads/*
  !downloads/.gitkeep
  .env
  ```
- [ ] Rodar `npx create-next-app@latest frontend --typescript --app --tailwind --eslint --no-src-dir` na raiz do repo.
- [ ] Dentro de `frontend/`, rodar `npx shadcn@latest init` (escolher estilo default, base color neutral ou similar).
- [ ] Rodar `npx shadcn@latest add button card input label textarea badge table tabs accordion skeleton alert separator progress` dentro de `frontend/`.
- [ ] Criar `frontend/.env.local.example` com `NEXT_PUBLIC_API_URL=http://localhost:8000` e copiar para `frontend/.env.local` (não versionado).
- [ ] Atualizar `.gitignore` da raiz do repo para garantir que cobre `backend/.venv/`, `backend/data/*.db`, `backend/downloads/*`, `backend/.env`, `frontend/node_modules/`, `frontend/.next/`, `frontend/.env.local` (Next.js já gera um `.gitignore` razoável dentro de `frontend/`, mas confirmar).
- [ ] **Checkpoint Fase 0**: `cd backend && .venv/bin/python -c "import fastapi, sqlalchemy, selenium, pypdf, pdfplumber, google.generativeai"` sem erro; `cd frontend && npm run dev` sobe em `http://localhost:3000` mostrando a página default do Next.

---

## Fase 1 — Adaptar o scraper isoladamente

- [ ] Ler `initialscraping.py` da raiz por completo antes de começar a copiar (confirmar que as 340 linhas batem com o esperado).
- [ ] Criar `backend/app/scraper/scraping_core.py`.
- [ ] Copiar para esse arquivo, sem alterar a lógica interna, as funções: `fechar_banner_cookies`, `buscar_processos`, `parsear_processo`, `extrair_dados_processo`, `aguardar_download`, `baixar_documentos`, `salvar_json` (pode manter ou remover `salvar_json`, já que quem persiste agora é o backend — decisão: remover, pois persistência passa a ser responsabilidade do `scraper_service.py`).
- [ ] Adaptar `iniciar_driver(headless: bool = True)`:
  - Manter `options.add_argument("--start-maximized")` apenas no ramo `else` (quando `headless=False`).
  - Quando `headless=True`, adicionar `options.add_argument("--headless=new")`, `options.add_argument("--disable-gpu")`, `options.add_argument("--window-size=1920,1080")`.
  - Manter toda a configuração de `prefs` de download já existente.
- [ ] Adaptar `baixar_documentos(driver, url_processo, pasta_downloads_processo: str)`:
  - Trocar a construção interna do path (`PASTA_DOWNLOADS` + slug) para receber a pasta final já resolvida como parâmetro, em vez de montar a partir de uma constante global.
- [ ] Criar a função de entrada nova:
  ```python
  def executar_scraping(termo: str, limite: int = 10, headless: bool = True, pasta_downloads_base: str = "downloads") -> dict:
  ```
  - Dentro: chama `iniciar_driver(headless)`, `buscar_processos(driver, termo)`, faz slice `cards[:limite]`, itera extraindo dados + chamando `baixar_documentos` com `pasta_downloads_base/<slug>`, acumula lista de processos.
  - Garantir `driver.quit()` dentro de `finally`, mesmo se exceção ocorrer no meio do loop.
  - Remover toda chamada a `input(...)`.
  - Retornar sempre `{"termo_busca": termo, "processos": [...], "erro": None}` em caso de sucesso, ou `{"termo_busca": termo, "processos": [...processados até a falha...], "erro": "<mensagem>"}` em caso de exceção capturada.
- [ ] Trocar todos os `print(...)` por `logging.getLogger("scraper").info(...)` / `.warning(...)` / `.error(...)` conforme o caso. Adicionar `logging.basicConfig(level=logging.INFO)` apenas no bloco `if __name__ == "__main__":` do próprio arquivo (não no import), para não conflitar com a config de logging do Uvicorn.
- [ ] Manter no final do arquivo um bloco `if __name__ == "__main__":` simples que chama `executar_scraping("cafe", limite=2, headless=True)` e faz `print(json.dumps(resultado, ensure_ascii=False, indent=2))`, só para teste manual rápido via terminal.
- [ ] Criar `backend/tests/test_scraper_isolated.py`:
  ```python
  from app.scraper.scraping_core import executar_scraping
  import json

  if __name__ == "__main__":
      resultado = executar_scraping(termo="cafe", limite=2, headless=True, pasta_downloads_base="downloads/teste_isolado")
      print(json.dumps(resultado, ensure_ascii=False, indent=2)[:3000])
      print("Erro:", resultado.get("erro"))
      print("Total de processos:", len(resultado["processos"]))
  ```
- [ ] Rodar `cd backend && .venv/bin/python -m tests.test_scraper_isolated` (executar da raiz de `backend/` para os imports relativos funcionarem; ajustar `PYTHONPATH` ou usar `python -m` conforme necessário).
- [ ] **Checkpoint Fase 1**: comando acima roda sem abrir janela visível do Chrome, sem travar esperando input, termina e imprime JSON com 2 processos e `erro: None` (ou erro tratado, se o portal estiver fora do ar — nesse caso documentar e tentar de novo). Confirmar que `downloads/teste_isolado/<slug>/` foi criado com PDFs reais.

---

## Fase 2 — Banco de dados e modelos

- [ ] Criar `backend/app/config.py`:
  ```python
  from pydantic_settings import BaseSettings

  class Settings(BaseSettings):
      GEMINI_API_KEY: str = ""
      GEMINI_MODEL: str = "gemini-2.0-flash"
      DATABASE_URL: str = "sqlite:///./data/app.db"
      MAX_PROCESSOS: int = 10
      DOWNLOADS_DIR: str = "downloads"
      CORS_ORIGINS: str = "http://localhost:3000"

      class Config:
          env_file = ".env"

  settings = Settings()
  ```
- [ ] Criar `backend/app/database.py`:
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
- [ ] Criar `backend/app/models.py` com as classes `Pesquisa` e `Analise` exatamente conforme o schema do plano (colunas: ver plano salvo — `id, termo_busca, quantidade_desejada, limite_processos, status, erro_mensagem, resultado_json, pasta_downloads, criado_em, atualizado_em` para `Pesquisa`; `id, pesquisa_id (FK), status, erro_mensagem, resultado_json, modelo_gemini, criado_em, atualizado_em` para `Analise`, com `relationship` 1:N e `cascade="all, delete-orphan"`).
- [ ] Criar `backend/app/schemas.py` com Pydantic models:
  - `PesquisaCreate(BaseModel)`: `termo_busca: str` (min_length=1), `quantidade_desejada: str | None = None`.
  - `PesquisaStatusOut(BaseModel)`: `id: int, status: str, erro_mensagem: str | None`.
  - `PesquisaDetailOut(BaseModel)`: todos os campos de `Pesquisa` + `resultado: dict | None` (parseado de `resultado_json`).
  - `PesquisaListItemOut(BaseModel)`: campos resumidos para listagem.
  - `AnaliseStatusOut(BaseModel)`: `id: int, status: str, erro_mensagem: str | None, resultado: dict | None, modelo_gemini: str | None`.
  - Usar `model_config = {"from_attributes": True}` em todos para permitir `.model_validate(orm_obj)`.
- [ ] Criar script utilitário rápido (pode ser dentro de `backend/app/main.py` via evento de startup, ver Fase 3) que chama `Base.metadata.create_all(bind=engine)`.
- [ ] Para testar isoladamente nesta fase, criar um script temporário `backend/tests/_check_db.py` (pode deletar depois) que importa `Base`, `engine` e chama `create_all`.
- [ ] Rodar `cd backend && .venv/bin/python -m tests._check_db` (ou equivalente) e depois `sqlite3 backend/data/app.db ".tables"` no terminal para confirmar que `pesquisas` e `analises` existem com as colunas certas (`sqlite3 backend/data/app.db ".schema pesquisas"`).
- [ ] **Checkpoint Fase 2**: tabelas criadas e visíveis via `sqlite3`, sem erros de import circular entre `models.py`/`database.py`/`config.py`.

---

## Fase 3 — Endpoints de pesquisa (scraping em background)

- [ ] Criar `backend/app/services/scraper_service.py`:
  - Função `executar_e_persistir(pesquisa_id: int, termo: str, limite: int)`:
    - Abre nova `Session` própria (`SessionLocal()`).
    - Busca a `Pesquisa` pelo id, seta `status="em_andamento"`, commit.
    - Resolve `pasta_downloads = f"downloads/{pesquisa_id}"`.
    - Chama `executar_scraping(termo, limite, headless=True, pasta_downloads_base=pasta_downloads)`.
    - Se `resultado["erro"]` for `None`: seta `status="completo"`, `resultado_json=json.dumps(resultado, ensure_ascii=False)`, `pasta_downloads=pasta_downloads`.
    - Se houver erro: seta `status="erro"`, `erro_mensagem=resultado["erro"]`, ainda salva o `resultado_json` parcial se houver processos.
    - Commit final, fecha sessão em `finally`.
- [ ] Criar `backend/app/services/job_runner.py`:
  ```python
  import threading
  from app.services.scraper_service import executar_e_persistir

  def iniciar_job_scraping(pesquisa_id: int, termo: str, limite: int):
      thread = threading.Thread(target=executar_e_persistir, args=(pesquisa_id, termo, limite), daemon=True)
      thread.start()
  ```
- [ ] Criar `backend/app/routers/pesquisas.py` com:
  - `POST /pesquisas` — recebe `PesquisaCreate`, cria `Pesquisa(status="pendente", limite_processos=settings.MAX_PROCESSOS, ...)`, commit, chama `iniciar_job_scraping(...)`, retorna 201 com `PesquisaStatusOut`-like payload incluindo o `id`.
  - `GET /pesquisas` — `db.query(Pesquisa).order_by(Pesquisa.criado_em.desc()).all()`, retorna lista de `PesquisaListItemOut`.
  - `GET /pesquisas/{id}` — busca por id, 404 se não existir; monta `PesquisaDetailOut` fazendo `json.loads(resultado_json)` se não for `None`.
  - `GET /pesquisas/{id}/status` — versão leve, só `id, status, erro_mensagem`.
  - `GET /pesquisas/{id}/documentos/{nome_arquivo:path}` — resolve `pasta_downloads` da pesquisa, usa `os.path.realpath` pra validar que o arquivo resolvido está dentro da pasta esperada (proteção contra path traversal com `..`), retorna `FileResponse` ou 404.
- [ ] Criar `backend/app/main.py`:
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from app.database import Base, engine
  from app.routers import pesquisas, analises
  from app.config import settings

  app = FastAPI()

  app.add_middleware(
      CORSMiddleware,
      allow_origins=[settings.CORS_ORIGINS],
      allow_methods=["*"],
      allow_headers=["*"],
  )

  @app.on_event("startup")
  def startup():
      Base.metadata.create_all(bind=engine)

  app.include_router(pesquisas.router)
  app.include_router(analises.router)  # router vazio/placeholder até a Fase 7
  ```
- [ ] Na Fase 3, `analises.py` pode existir só com um `router = APIRouter()` vazio (sem endpoints ainda) para não quebrar o import em `main.py` — será preenchido na Fase 7.
- [ ] Rodar `cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000`.
- [ ] Testar via terminal:
  ```bash
  curl -X POST http://localhost:8000/pesquisas -H "Content-Type: application/json" -d '{"termo_busca":"cafe","quantidade_desejada":"2 toneladas"}'
  ```
  Anotar o `id` retornado.
  ```bash
  curl http://localhost:8000/pesquisas/<id>/status
  ```
  Repetir até `status` virar `completo` (ou `erro`).
  ```bash
  curl http://localhost:8000/pesquisas/<id>
  ```
  Confirmar que `resultado.processos` tem itens com a mesma estrutura de `resultados.json` da raiz.
  ```bash
  curl http://localhost:8000/pesquisas
  ```
  Confirmar que a pesquisa aparece na lista.
- [ ] **Checkpoint Fase 3**: fluxo completo via curl funciona, dados batem com o formato esperado, downloads aparecem em `backend/downloads/<id>/`.

---

## Fase 4 — Extração de PDF isolada

- [ ] Criar `backend/app/services/pdf_extractor.py`:
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
  - Implementar `_extrair_com_pypdf` usando `pypdf.PdfReader`, concatenando `page.extract_text() or ""` de todas as páginas.
  - Implementar `_extrair_com_pdfplumber` usando `pdfplumber.open`, concatenando `page.extract_text() or ""`.
  - Em `extrair_texto_pdf`: tentar pypdf primeiro; se `len(texto.strip()) < 50`, tentar pdfplumber; se ainda `< 50`, status `vazio_possivelmente_escaneado`; se qualquer exceção em ambos, status `erro`.
- [ ] Criar `backend/tests/test_pdf_extractor_isolated.py`:
  ```python
  from app.services.pdf_extractor import extrair_textos_da_pasta
  import sys, json

  if __name__ == "__main__":
      pasta = sys.argv[1] if len(sys.argv) > 1 else "downloads"
      resultados = extrair_textos_da_pasta(pasta)
      for nome, r in resultados.items():
          print(nome, "->", r["status"], "len=", len(r["texto"]))
  ```
- [ ] Rodar apontando para uma pasta real de downloads gerada na Fase 3/1:
  ```bash
  cd backend && .venv/bin/python -m tests.test_pdf_extractor_isolated downloads/<id_da_pesquisa>
  ```
- [ ] **Checkpoint Fase 4**: PDFs de texto nativo (ex: Edital, ETP) retornam `status=ok` com `len > 0`; se algum PDF escaneado existir no exemplo, confirmar que vem `vazio_possivelmente_escaneado` em vez de erro.

---

## Fase 5 — Integração Gemini isolada

- [ ] Confirmar `GEMINI_API_KEY` preenchida em `backend/.env`.
- [ ] Criar `backend/app/services/gemini_service.py`:
  ```python
  import json, re, google.generativeai as genai
  from app.config import settings

  def carregar_prompt_base() -> str:
      with open("prompt.md", "r", encoding="utf-8") as f:
          return f.read()

  def montar_prompt_final(pesquisa_dict: dict, textos_pdfs: dict, quantidade_desejada: str | None, prompt_base: str) -> str:
      ...

  def _extrair_json_da_resposta(texto: str) -> dict:
      try:
          return json.loads(texto)
      except json.JSONDecodeError:
          match = re.search(r"```json\s*(.*?)\s*```", texto, re.DOTALL)
          if match:
              return json.loads(match.group(1))
          raise

  def chamar_gemini(prompt: str) -> dict:
      genai.configure(api_key=settings.GEMINI_API_KEY)
      model = genai.GenerativeModel(settings.GEMINI_MODEL)
      response = model.generate_content(
          prompt,
          generation_config={"response_mime_type": "application/json"},
      )
      return _extrair_json_da_resposta(response.text)
  ```
  - Caminho de `prompt.md` deve ser resolvido relativo ao diretório de trabalho do processo backend (rodar sempre com `cwd = backend/`) ou usar caminho absoluto via `os.path.join(os.path.dirname(__file__), "..", "..", "prompt.md")` — preferir esta segunda forma para não depender do cwd.
- [ ] Criar `backend/tests/test_gemini_isolated.py`:
  ```python
  import json
  from app.services.gemini_service import montar_prompt_final, chamar_gemini, carregar_prompt_base

  if __name__ == "__main__":
      with open("../resultados.json", "r", encoding="utf-8") as f:
          pesquisa_dict = json.load(f)
      pesquisa_dict["processos"] = pesquisa_dict["processos"][:1]  # só 1 processo pra teste rápido/barato
      textos_pdfs = {"documento_teste.pdf": {"texto": "Texto de exemplo de um edital fictício para teste.", "status": "ok"}}
      prompt = montar_prompt_final(pesquisa_dict, textos_pdfs, "2 toneladas", carregar_prompt_base())
      resultado = chamar_gemini(prompt)
      print(json.dumps(resultado, ensure_ascii=False, indent=2)[:3000])
      print("Chaves de topo:", list(resultado.keys()))
  ```
- [ ] Rodar `cd backend && .venv/bin/python -m tests.test_gemini_isolated`.
- [ ] Comparar as chaves de topo retornadas com o schema esperado em `prompt.md` (`metadados`, `documentos_auditados`, `documentos_ausentes`, `itens`, `classificacao_checklist`, `constatacoes`, `dicas_aprimoramento`, `recomendacoes_consolidadas`, `quadro_sintese`).
- [ ] **Checkpoint Fase 5**: chamada real bem-sucedida, JSON parseado sem exceção, chaves de topo presentes (mesmo que com valores vazios/genéricos dado o input de teste reduzido).

---

## Fase 6 — Endpoints de análise

- [ ] Criar `backend/app/services/analise_service.py` (ou adicionar direto em `gemini_service.py` — escolher um lugar, ex. novo arquivo `analise_service.py` para separar orquestração de chamada pura):
  - Função `executar_analise(analise_id: int, pesquisa_id: int)`:
    - Abre `Session` própria.
    - Busca `Pesquisa` pelo id, garante `status == "completo"`.
    - Marca `Analise.status = "em_andamento"`, commit.
    - `pesquisa_dict = json.loads(pesquisa.resultado_json)`.
    - `textos_pdfs = extrair_textos_da_pasta(pesquisa.pasta_downloads)`.
    - `prompt = montar_prompt_final(pesquisa_dict, textos_pdfs, pesquisa.quantidade_desejada, carregar_prompt_base())`.
    - `resultado = chamar_gemini(prompt)`.
    - Em sucesso: `Analise.status = "completo"`, `resultado_json = json.dumps(resultado, ensure_ascii=False)`, `modelo_gemini = settings.GEMINI_MODEL`.
    - Em exceção: `Analise.status = "erro"`, `erro_mensagem = str(exc)`.
    - Commit, fecha sessão em `finally`.
- [ ] Atualizar `backend/app/services/job_runner.py` adicionando:
  ```python
  def iniciar_job_analise(analise_id: int, pesquisa_id: int):
      thread = threading.Thread(target=executar_analise, args=(analise_id, pesquisa_id), daemon=True)
      thread.start()
  ```
- [ ] Preencher `backend/app/routers/analises.py`:
  - `POST /pesquisas/{id}/analise`:
    - Busca `Pesquisa`; 404 se não existir; 409 se `status != "completo"`.
    - Verifica se já existe `Analise` com `status in ("pendente", "em_andamento")` para essa pesquisa; se sim, 409.
    - Cria nova `Analise(pesquisa_id=id, status="pendente")`, commit, dispara `iniciar_job_analise(...)`, retorna 202 com `{analise_id, status}`.
  - `GET /pesquisas/{id}/analise`:
    - Busca a `Analise` mais recente daquela pesquisa (`order_by(Analise.criado_em.desc()).first()`); 404 se nenhuma existir ainda.
    - Retorna `AnaliseStatusOut` com `resultado = json.loads(resultado_json)` se completo.
- [ ] Testar via curl:
  ```bash
  curl -X POST http://localhost:8000/pesquisas/<id>/analise
  curl http://localhost:8000/pesquisas/<id>/analise   # repetir até status=completo
  ```
- [ ] **Checkpoint Fase 6**: ciclo completo scraping → análise funciona via curl puro, sem frontend.

---

## Fase 7 — Frontend: tipos, client de API e formulário

- [ ] Criar `frontend/lib/types.ts` espelhando os schemas Pydantic (`Pesquisa`, `Processo`, `Documento`, `Item`, `Andamento`, `Analise`, `AnaliseResultado` com os 9 campos de topo do schema de auditoria).
- [ ] Criar `frontend/lib/api-client.ts` com funções: `criarPesquisa(payload)`, `listarPesquisas()`, `getPesquisa(id)`, `getPesquisaStatus(id)`, `dispararAnalise(id)`, `getAnalise(id)` — todas usando `fetch(`${process.env.NEXT_PUBLIC_API_URL}/...`)`.
- [ ] Criar `frontend/components/pesquisa-form.tsx` (`"use client"`): formulário com `Input` (termo de busca, obrigatório) e `Textarea` ou `Input` (quantidade desejada, opcional), botão `Button` "Iniciar Pesquisa" com estado de loading; ao submeter, chama `criarPesquisa`, em sucesso `router.push(`/pesquisas/${id}`)`.
- [ ] Criar `frontend/app/nova-pesquisa/page.tsx` renderizando `<PesquisaForm />` dentro de um `Card`.
- [ ] Criar `frontend/components/pesquisa-lista.tsx`: tabela (`Table` do shadcn) com colunas Termo, Quantidade Desejada, Status (Badge colorido por status), Data, link "Ver".
- [ ] Criar `frontend/app/pesquisas/page.tsx`: server component que busca `listarPesquisas()` (ou client component se preferir simplicidade) e renderiza `<PesquisaLista />`.
- [ ] Ajustar `frontend/app/page.tsx` (home) para ter um botão/link de destaque para `/nova-pesquisa` e outro para `/pesquisas`.
- [ ] **Checkpoint Fase 7**: com backend rodando, preencher o formulário em `http://localhost:3000/nova-pesquisa` cria pesquisa real (confirmar via `curl GET /pesquisas` no backend) e a lista em `/pesquisas` reflete isso.

---

## Fase 8 — Frontend: tela de detalhe com polling

- [ ] Criar `frontend/lib/use-pesquisa-polling.ts` com o hook genérico de polling (conforme especificado no plano), parametrizável por `fetchFn`, `intervalMs`, `shouldStop`.
- [ ] Criar `frontend/components/pesquisa-status-card.tsx`: mostra spinner/Progress + texto do status atual enquanto `pendente`/`em_andamento`; `Alert variant="destructive"` se `erro`.
- [ ] Criar `frontend/components/processo-card.tsx`: `Card` por processo mostrando `numero_processo`, `Badge` de `situacao`, `comprador`, `modalidade`, `objeto`, tabela de `informacoes`, tabela de `datas`, tabela de `itens`.
- [ ] Criar `frontend/components/conteudo-bruto-viewer.tsx`: `Accordion` com um item por processo, dentro um `<pre>` scrollável com `conteudo_bruto.join("\n")`.
- [ ] Criar `frontend/components/documentos-lista.tsx`: lista/tabela de `documentos` (nome, tipo, data) cruzada com `arquivos_baixados` (tamanho), com link de download apontando para `${API_URL}/pesquisas/{id}/documentos/{arquivo}`.
- [ ] Criar `frontend/app/pesquisas/[id]/page.tsx` (`"use client"`):
  - Usa `usePolling` chamando `getPesquisaStatus(id)` a cada 3000ms, parando quando `status === "completo" || status === "erro"`.
  - Enquanto não parado: renderiza `<PesquisaStatusCard />`.
  - Quando `completo`: busca `getPesquisa(id)` uma vez, renderiza `Tabs` com `TabsTrigger` "Dados Organizados" / "Dados Brutos" / "Documentos", cada `TabsContent` usando os componentes acima; mais um botão fixo (`<AnaliseTriggerButton pesquisaId={id} />` — criado na Fase 9, pode deixar placeholder por enquanto).
  - Quando `erro`: renderiza `Alert` com `erro_mensagem`.
- [ ] **Checkpoint Fase 8**: criar pesquisa nova pelo formulário e, sem dar refresh manual na página, ver a transição automática de "em andamento" para as abas de dados completos.

---

## Fase 9 — Frontend: disparo e exibição da análise

- [ ] Criar `frontend/components/analise-trigger-button.tsx` (`"use client"`): botão "Condensar e enviar pra LLM" que chama `dispararAnalise(pesquisaId)`, mostra loading, em sucesso `router.push(`/pesquisas/${id}/analise`)`. Desabilitar o botão (ou mostrar mensagem) se já existir análise em andamento (checar isso opcionalmente via `getAnalise` antes de habilitar).
- [ ] Substituir o placeholder da Fase 8 em `pesquisas/[id]/page.tsx` pelo componente real.
- [ ] Criar `frontend/components/analise-resultado-view.tsx`: recebe o objeto `AnaliseResultado` e renderiza:
  - `metadados` em um `Card` de cabeçalho (órgão, município/UF, número do processo, modalidade, valor estimado etc).
  - `classificacao_checklist` em `Table` com `Badge` colorido por `classificacao` (C=verde, PC=amarelo/laranja, NC=vermelho, N/A=cinza).
  - `constatacoes` em `Accordion`, um item por constatação, mostrando `risco` como `Badge`, `descricao_sumaria`, `situacao_encontrada`, `recomendacao`.
  - `quadro_sintese` em uma linha de `Card`s pequenos (total_itens, conformes, parcialmente_conformes, nao_conformes, percentual_conformidade, grau_risco_geral).
  - `documentos_ausentes`, `dicas_aprimoramento`, `recomendacoes_consolidadas` em listas simples (`ul`/`li` estilizado ou `Alert` informativo).
- [ ] Criar `frontend/app/pesquisas/[id]/analise/page.tsx` (`"use client"`):
  - `usePolling` chamando `getAnalise(id)` a cada 5000ms, parando quando `status === "completo" || status === "erro"`.
  - Enquanto não parado: spinner/Progress com texto "Analisando com IA...".
  - Quando `completo`: renderiza `<AnaliseResultadoView resultado={analise.resultado} />`.
  - Quando `erro`: `Alert` com `erro_mensagem` e botão para tentar novamente (re-chama `dispararAnalise`).
- [ ] **Checkpoint Fase 9**: clicar no botão na tela de detalhe leva à tela de análise, que faz polling e ao final mostra relatório formatado e legível (zero JSON crú visível na UI).

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
