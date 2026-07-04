# GERACAO_ETP_TR.md — Geração assistida de ETP e TR no template oficial do ES

Especificação de handoff para o Claude Code do VSCode. O backend vive local; os nomes de
módulo seguem a convenção do `REFACTOR.md`. Adapte aos nomes reais onde divergir.

## Context

Nova capacidade: **gerar rascunhos de ETP e TR** já no template oficial do Governo do ES
(Lei 14.133), fundamentados em fontes legais de verdade, para o **servidor público revisar,
baixar, editar o que for necessário e então entregar** ao responsável. É geração assistida
com humano no loop — não um documento final automático.

Três insumos foram fornecidos:
- **Template ETP** (`.docx` do ES): cabeçalho "Governo do Estado do Espírito Santo" + logo,
  fonte `Ecofont_Spranq_eco_Sans` + Arial, 15 seções (estilo `Nivel01`), notas explicativas
  (estilo `Nivel2`, a suprimir no final), Anexo I (Mapeamento de Riscos) e Anexo II (Matriz
  de Alocação), riscos em tabelas repetíveis.
- **Lei 14.133/2021** (`.docx`, ~69k tokens) — fonte de verdade federal.
- **Decreto 5352-R/2023** (`.pdf`, ~17,6k tokens) — fonte de verdade estadual **confirmada**
  (arts. 15-26 regem o ETP). O arquivo foi rotulado "5766" por engano; a norma vigente e a
  fonte de verdade é o **5352-R/2023**.

## Arquitetura — 3 camadas (separação forma × conteúdo × verdade)

```
Camada 1: FONTES DE VERDADE (Lei 14.133 + Decreto 5352-R)   → cacheadas, sempre presentes
Camada 2: LLM gera só o CONTEÚDO (JSON por seção)           → prompt novo, fundamentado
Camada 3: docxtpl injeta o JSON no template .docx           → forma idêntica ao modelo do ES
```

O princípio central: **o LLM nunca produz .docx**. Ele produz texto por seção. O template
carrega toda a forma (cabeçalho/rodapé/logo/Ecofont/estilos/tabelas), então o resultado sai
sempre no padrão do ES sem esforço.

## Camada 1 — Fontes de Absoluta Verdade (grounding)

- Extrair e versionar no repo os textos canônicos:
  `backend/fontes_verdade/lei_14133.md` e `backend/fontes_verdade/decreto_5352R.md`
  (texto limpo, com um cabeçalho de metadados: norma, data, hash do arquivo-fonte).
- **Injeção via context caching do Gemini**: criar um objeto de conteúdo cacheado contendo
  {Lei 14.133 + Decreto 5352-R + spec estrutural do ETP + instruções-base do prompt}. Reusar
  esse cache em toda geração. Paga o custo uma vez; grounding garantido; ~90% de desconto nas
  chamadas seguintes. Guardar o `cache_id` e invalidá-lo quando as fontes mudarem (ver abaixo).
- **Regra dura no prompt** (reforça a verdade absoluta): toda exigência estrutural ou
  requisito do ETP deve **citar o artigo** da Lei/Decreto que o embasa; é proibido inventar
  norma; se a lei exige algo que os dados do processo não fornecem, **marcar como pendência**
  para o humano em vez de preencher com suposição.
- **Versionamento**: se a norma for atualizada, trocar o `.md`, recomputar o hash e recriar o
  cache. Um teste de fumaça compara o hash atual com o registrado e avisa se divergiu.

## Camada 2 — Prompt novo de GERAÇÃO (separado do de auditoria)

Criar `backend/prompts/prompt_etp.md` (não reaproveitar `prompt.md`, que é auditoria — este
é geração). Estrutura:

- **Papel**: elaborar rascunho de ETP conforme arts. 15-26 do Decreto 5352-R e a Lei 14.133.
- **Entradas**:
  1. Fontes de verdade (via cache — Camada 1).
  2. Processo(s) raspado(s) + textos dos documentos **curados** (edital/TR/ETP de processos
     similares já filtrados pela curadoria) — insumo para "Levantamento de Mercado" e
     "Estimativa do Valor".
  3. Parâmetros do servidor: objeto, quantidade desejada, unidade gestora, responsáveis, etc.
- **Saída**: JSON estrito com um campo por seção do template + bloco de identificação +
  `riscos[]` (para o Anexo I) + `matriz_riscos[]` (Anexo II). Ver schema na Camada 3.
- **Regras anti-alucinação** (críticas, dado que o documento entra em processo real):
  - Fatos (preço, quantidade, fornecedor, referência de mercado) **só** se vierem dos
    documentos de entrada; sempre citar a origem.
  - Onde faltar dado, emitir placeholder explícito `[A PREENCHER PELO AGENTE: <o que falta>]`
    — nunca inventar número ou justificativa.
  - Responder às "perguntas-guia" de cada seção do modelo (elas viram o roteiro do conteúdo).
  - Tom técnico, impessoal, fundamentado; sem floreio.

## Camada 3 — Motor de template (docxtpl)

- **Preparar `backend/templates/template_etp.docx` (uma vez)** a partir do modelo do ES:
  - Remover os parágrafos `Nivel2` de nota explicativa ("O que deve ser informado...",
    "Pergunta:...") — o próprio modelo manda suprimi-los na versão final.
  - Substituir cada slot "..." pela tag Jinja da seção (ex.: `{{ descricao_necessidade }}`).
  - Nas células das tabelas (IDENTIFICAÇÃO): tags `{{ un_gestora }}`, `{{ responsaveis }}`,
    `{{ data_elab }}`, `{{ versao }}`, etc.
  - Nos blocos de risco (Anexo I/II): converter em loop `{% for r in riscos %}...{% endfor %}`
    sobre as linhas da tabela, com `{{ r.descricao }}`, `{{ r.probabilidade }}`,
    `{{ r.impacto }}`, `{{ r.dano }}`, `{{ r.acao_preventiva }}`, etc.
  - **Não tocar** em cabeçalho, rodapé, logo, fontes, estilos.
- **Serviço `backend/app/services/gerador_documento.py`**:
  ```python
  from docxtpl import DocxTemplate
  def gerar_etp(conteudo: dict, destino: str) -> str:
      doc = DocxTemplate("templates/template_etp.docx")
      doc.render(conteudo)     # conteudo = JSON da Camada 2
      doc.save(destino)        # .docx EDITÁVEL
      return destino
  ```
- **Saída primária = `.docx` editável** (requisito: o servidor edita antes de entregar).
- **PDF é opcional** e só para pré-visualização — exige LibreOffice headless **+ a
  `Ecofont_Spranq_eco_Sans` instalada no servidor** (senão o PDF troca a fonte). Para
  fidelidade total, embutir as fontes no template (Word: "Incorporar fontes no arquivo").
- Adicionar `docxtpl` ao `requirements.txt`.

## Fluxo e endpoints

- `POST /pesquisas/{id}/etp` — dispara job de geração (background), retorna `etp_id`/status.
- `GET /pesquisas/{id}/etp` — status; quando `completo`, expõe metadados + pendências.
- `GET /pesquisas/{id}/etp/download` — devolve o `.docx` (`FileResponse`).
- Frontend: botão **"Gerar ETP (rascunho)"**, aviso visível "Rascunho para revisão humana —
  confira e complete os campos [A PREENCHER] antes de entregar", e botão de download.

## TR (Termo de Referência) — sem template oficial por enquanto

Decisão: **gerar o TR já agora, sem o template `.docx` do ES** (que será fornecido depois).
As camadas 1 (fontes de verdade) e 2 (prompt/schema) são construídas normalmente; só a
camada 3 usa, provisoriamente, um documento **genérico** em vez do template oficial.

- **Camada 2**: criar `prompt_tr.md` + schema do TR com base nos requisitos do TR do
  **Decreto 5352-R** (a partir do art. ~27) e da Lei 14.133. Mesmas regras anti-alucinação.
- **Camada 3 (provisória)**: renderizar o conteúdo num `.docx` simples via `python-docx`
  (títulos de seção + texto), sem cabeçalho/rodapé/Ecofont do ES. Marcar visivelmente
  "MINUTA PROVISÓRIA — sem formatação oficial".
- **Quando o template oficial chegar**: adicionar `template_tr.docx` e trocar o renderizador
  genérico pelo `docxtpl` — o `prompt_tr.md` e o schema já prontos não mudam. A troca fica
  isolada na camada 3.

Assim o TR não fica bloqueado pela falta do modelo, e a forma oficial entra depois sem
retrabalho de prompt/schema.

## Riscos e decisões em aberto

1. **Identidade do decreto**: resolvido — a fonte de verdade é o **Decreto 5352-R/2023**
   (o rótulo "5766" do arquivo é engano). Sem pendência.
2. **LLM/caching**: manter Gemini (já em uso) e usar seu context caching; alternativa é Claude
   com prompt caching. A escolha muda o `gemini_service.py`, não a arquitetura.
3. **Fontes que mudam**: versionar + recriar o cache; teste de hash alerta divergência.
4. **Ecofont no PDF**: instalar/embutir a fonte se for gerar PDF fiel.
5. **Responsabilidade**: sempre rascunho, humano revisa e entrega; placeholders em vez de
   invenção; fatos citáveis à fonte. Não apresentar como documento final.
6. **Auditoria vs geração**: este é um fluxo NOVO e separado (prompt/endpoint próprios),
   convivendo com a auditoria existente — não a substitui.

## Verificação end-to-end (no VSCode)

1. Gerar ETP para um processo real (ex.: a busca de "Ibuprofeno").
2. Abrir o `.docx` no Word e confirmar: cabeçalho "Governo do ES", logo, rodapé, Ecofont e
   estilos **idênticos** ao modelo; as 15 seções preenchidas; as notas explicativas ausentes.
3. Conferir que requisitos citam artigos da Lei/Decreto corretos.
4. Conferir que onde faltou dado aparece `[A PREENCHER PELO AGENTE: ...]`, sem número inventado.
5. Conferir Anexo I/II com os riscos renderizados nas tabelas.
6. Editar um campo e salvar — confirmar que o arquivo é editável e íntegro.
