# PLANO — Geração de TR com o template oficial da PGE

Handoff para o Claude Code do VSCode **executar**. Este documento é só o plano; a
implementação é sua. Baseado no estado atual do `main` (backend já com geração ETP+TR).

## Contexto — o que já existe e o que falta

O encanamento do TR **já está pronto ponta a ponta**:
- `Geracao.tipo ∈ {etp, tr}` (`backend/app/models.py`), schemas com `tipo`, router
  `POST/GET/download /pesquisas/{id}/etp?tipo=tr` (`backend/app/routers/geracoes.py`),
  `executar_geracao` que carrega `prompt_tr.md` e chama o renderizador
  (`backend/app/services/gerador_etp_service.py`), e o front com seletor ETP/TR
  (`frontend/components/etp-geracao-card.tsx`, já passa `tipo`).
- **ETP** renderiza via docxtpl + `templates/template_etp.docx` (`gerar_etp`).
- **TR hoje** renderiza via `gerar_tr_provisorio` (python-docx, 17 seções genéricas,
  marcado "MINUTA PROVISÓRIA") — **não** segue a estrutura da PGE.

Novo insumo: o **template oficial da PGE** `20.02 TR E HABILITAÇÃO de COMPRAS.docx`
(TR = **Anexo I**; Requisitos de Habilitação = **Anexo II**). Características:
estilos próprios `PGE-*`/`Ttulo`/`Ttulo1`/`N11`; **numeração automática** (1.1, 1.1.1);
notas em estilo `PGE-NotaExplicativa` (suprimíveis, o modelo instrui Ctrl+Shift+1); sem
cabeçalho próprio (só `footnotes.xml`) — a identidade vem dos estilos/numeração/título.

**Objetivo:** o TR passar a sair no template da PGE, no mesmo motor docxtpl do ETP,
aposentando o `gerar_tr_provisorio`.

## Insight central: FILL vs KEEP (a habilitação é boilerplate)

Diferente do ETP (que tinha slots "..." vazios), a minuta da PGE **já traz o texto-modelo
das cláusulas** dentro dos parágrafos `N11`. Boa parte — sobretudo a **Habilitação**
(Anexo II) e as **Sanções** — é texto jurídico padrão que **NÃO deve ser reescrito pelo
LLM** (risco de alucinar cláusula legal e de descaracterizar a minuta da PGE).

Regra de ouro do template do TR:
- **KEEP** — cláusulas padrão ficam **verbatim** no template (sem tag Jinja). O LLM não toca.
- **FILL** — só os trechos específicos do objeto viram `{{ tag }}` preenchida pelo LLM.
- **HYBRID** — cláusula padrão + um único ponto variável tagueado.

Essa decisão reduz drasticamente alucinação/risco jurídico e é o ponto mais importante do
plano. **Não** é um "replace cego de placeholders" como foi no ETP.

## Mapa de seções (PGE → campo JSON → política)

**Anexo I — Termo de Referência**
| Seção PGE | Campo JSON | Política |
|---|---|---|
| DO OBJETO | `objeto` + tabela de itens (loop) | FILL |
| FUNDAMENTAÇÃO E DESCRIÇÃO DA NECESSIDADE | `fundamentacao_necessidade` | FILL |
| DESCRIÇÃO DA SOLUÇÃO (ciclo de vida) + especificação | `descricao_solucao` | FILL |
| REQUISITOS DA CONTRATAÇÃO | `requisitos` | FILL |
| MODELO DE EXECUÇÃO DO OBJETO | `modelo_execucao` | HYBRID |
| MODELO DE GESTÃO DO CONTRATO | (fiscal) | KEEP + `[A PREENCHER]` fiscal |
| CRITÉRIOS DE MEDIÇÃO E PAGAMENTO | `criterios_medicao` | HYBRID |
| FORMA E CRITÉRIOS DE SELEÇÃO DO FORNECEDOR | `criterio_julgamento` | KEEP + FILL do critério |
| ESTIMATIVAS DO VALOR | `estimativa_valor` | FILL (citar fonte de mercado) |
| ADEQUAÇÃO ORÇAMENTÁRIA | — | KEEP + `[A PREENCHER]` |
| SANÇÕES ADMINISTRATIVAS | — | KEEP |

**Anexo II — Requisitos de Habilitação**
| Seção PGE | Campo JSON | Política |
|---|---|---|
| HABILITAÇÃO JURÍDICA | — | KEEP |
| HABILITAÇÃO FISCAL, SOCIAL E TRABALHISTA | — | KEEP |
| HABILITAÇÃO TÉCNICA | `habilitacao_tecnica` | FILL (específico do objeto) |
| HABILITAÇÃO ECONÔMICO-FINANCEIRA | — | KEEP (toggle se exigir balanço) |

## Mudanças (delta)

1. **Novo `backend/scripts/preparar_template_tr.py`** (espelha `preparar_template_etp.py`):
   - Copiar a minuta PGE para `templates/template_tr.docx`.
   - Remover os parágrafos estilo `PGE-NotaExplicativa` (equivalem às notas do ETP).
   - Percorrer por `Ttulo1` (seções). Para seções **FILL**: substituir o parágrafo de
     conteúdo pelo `{{ campo }}` (reusar o helper `_set_para` que preserva a formatação do
     run). Para **KEEP**: não tocar. **HYBRID**: taguear só o ponto variável.
   - Tabela **DO OBJETO** (itens): converter em loop `{% for it in itens %}...{% endfor %}`
     (colunas: item, descrição/especificação, unidade, quantidade, valor de referência).
   - ⚠️ **Numeração automática** (`N11`: 1.1, 1.1.1): docxtpl preserva o campo de numeração
     porque só troca texto no run — **não** tentar regenerar numeração. O conteúdo do LLM
     entra como texto do parágrafo sob o título numerado; para múltiplos subitens, manter
     como um texto único (com quebras) em vez de brigar com a numeração do Word.
   - Imprimir contadores (seções FILL tagueadas, KEEP mantidas, notas removidas, loop de
     itens) para conferência, como faz o script do ETP.

2. **Reescrever `backend/prompts/prompt_tr.md`**:
   - Novo schema JSON com **exatamente** os campos FILL do mapa acima (não os 17 provisórios).
   - Manter regras anti-alucinação e placeholders `[A PREENCHER PELO AGENTE: ...]`; citar
     artigos (Lei 14.133 **art. 6º, XXIII** define os elementos do TR; Decreto 5352-R
     correlatos), usando o contexto cacheado das fontes de verdade.
   - **Remover** a "Nota sobre MINUTA PROVISÓRIA".
   - Instrução explícita: **NÃO** gerar as cláusulas KEEP (habilitação jurídica/fiscal,
     sanções, etc.) — elas já vêm prontas no template.

3. **`backend/app/services/gerador_documento.py`**:
   - Adicionar `gerar_tr(conteudo, destino)` = docxtpl sobre `templates/template_tr.docx`
     (espelho exato de `gerar_etp`).
   - Manter `gerar_tr_provisorio` como **fallback** caso `template_tr.docx` não exista.

4. **`backend/app/services/gerador_etp_service.py`** (`executar_geracao`, ramo `else` ~linhas
   66-69): trocar `gerar_tr_provisorio(...)` por `gerar_tr(...)`, com fallback ao provisório
   se o template estiver ausente.

5. **Plumbing back/front: sem mudança** — `tipo=tr` já é suportado em models, schemas,
   router, `api-client.ts` e no card. Ajuste apenas cosmético em
   `frontend/components/etp-geracao-card.tsx`: rótulo "TR — Termo de Referência (minuta)" →
   "(oficial PGE)". (Obs.: `frontend/AGENTS.md` avisa que este Next.js é modificado — aqui é
   só troca de string, sem risco.)

## Partes difíceis / riscos

- **Preparar `template_tr.docx` é o ponto sensível.** A minuta PGE não tem slots "..."
  limpos; exige a política por seção (FILL/KEEP), não um replace cego. Antes de escrever o
  script, **dumpe os parágrafos por estilo** (como já inspecionamos) e mapeie
  seção→parágrafo/run.
- **Numeração 1.1/1.1.1**: não regenerar; deixar o Word manter.
- **Habilitação e sanções**: manter verbatim; validar que o LLM não as reescreveu.
- **Itens**: garantir que vêm dos processos **curados** (não inventados).
- **Responsabilidade**: segue rascunho para revisão humana; nada de fato sem origem citável.

## Verificação (no VSCode)

1. `cd backend && python -m scripts.preparar_template_tr` → `template_tr.docx` criado;
   conferir os contadores impressos.
2. Gerar TR para um processo real (ex.: a busca "Ibuprofeno") e abrir no Word:
   - Estrutura PGE preservada: Anexo I + Anexo II, estilos e numeração intactos; notas
     explicativas ausentes.
   - Seções **FILL** preenchidas e fundamentadas; cláusulas **KEEP** (habilitação
     jurídica/fiscal, sanções) idênticas ao modelo.
   - Tabela de itens preenchida a partir dos itens do processo.
   - `[A PREENCHER PELO AGENTE: ...]` onde faltou dado (dotação, fiscal, endereço de entrega).
3. `GET /pesquisas/{id}/etp/download?tipo=tr` → `.docx` editável e íntegro.
4. Rodar `pytest` para garantir que nada existente quebrou.
