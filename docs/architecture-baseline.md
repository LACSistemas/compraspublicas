# Baseline arquitetural

Este documento registra as capacidades que já existem antes da migração para o domínio orientado a decisões. Ele é uma proteção contra regressões: a nova arquitetura pode reorganizar o domínio, mas não deve perder estas garantias sem uma decisão explícita e documentada.

## Fluxo atual

1. Um usuário autenticado cria uma `Pesquisa` com termo e quantidade desejada.
2. Um job em segundo plano consulta a fonte HTTP configurada, normaliza processos, seleciona documentos relevantes, valida downloads e persiste o resultado.
3. O usuário consulta estado e resultado da pesquisa e acessa os documentos coletados.
4. Uma `Analise` extrai texto dos PDFs, usa OCR quando necessário, monta o contexto e executa o modelo.
5. Uma `Geracao` produz ETP ou TR e persiste o JSON e o arquivo DOCX.
6. O consumo de tokens é associado ao usuário e à execução correspondente.

Fluxo predominante atual:

```text
Usuário -> Pesquisa -> Coleta HTTP/Documentos -> OCR -> Análise -> Geração ETP/TR
```

Fluxo-alvo, sem descartar os motores existentes:

```text
Contratação -> Plano de Investigação -> Cards de Decisão
                                        |
                              Informações/Evidências
                                        |
                                Base de Conhecimento
                                        |
                         DFD/ETP/TR/Riscos/Edital/Contrato
```

Pesquisa, coleta, documentos, OCR e auditoria passam a alimentar evidências; não precisam ser removidos.

## Matriz de capacidades protegidas

| Capacidade | Implementação atual | Garantia a preservar |
|---|---|---|
| Autenticação | JWT e senha com bcrypt | Rotas privadas exigem usuário autenticado |
| Ativação | `Usuario.is_active` | Usuário pendente não acessa funções operacionais |
| Administração | `Usuario.is_owner` | Ações administrativas permanecem restritas |
| Isolamento | Filtro por `usuario_id` | Um usuário não lê pesquisas, documentos ou gerações de outro |
| Fonte de dados | Interface `FonteDados` e implementação HTTP | Domínio não fica acoplado ao Portal de Compras Públicas |
| Resiliência da coleta | Retry/backoff e normalização | Falhas externas produzem estado diagnosticável |
| Downloads | Validação de arquivo e caminhos | HTML indevido e path traversal não são aceitos como documento |
| Seleção documental | Filtro de documentos relevantes | Volume e ruído são controlados antes da análise |
| Extração | pypdf, pdfplumber e Tesseract | PDF escaneado não fica invisível para a análise |
| Assincronismo | Jobs e estados persistidos | Operações lentas não bloqueiam a requisição HTTP |
| Recuperação | Estados `pendente`, `em_andamento`, `completo`, `erro` | Falhas ficam visíveis e não aparentam sucesso |
| IA estruturada | Resposta JSON e limites de tokens | Saída é validável e chamadas excessivas podem ser bloqueadas |
| Fontes legais | Lei, decreto e cache de contexto | Fundamentação usa acervo controlado e rastreável |
| Auditoria | `Analise` persistida | Resultado e modelo utilizado permanecem consultáveis |
| Redação | Geração ETP/TR e DOCX | Artefatos atuais continuam disponíveis durante a migração |
| Custos | `UsoTokens` | Consumo fica associado a usuário, finalidade e execução |

## Limites conhecidos do baseline

- O domínio atual é centrado em `Pesquisa`; ainda não há `Contratacao`, Plano, Cards, Evidências ou Base de Conhecimento.
- Os jobs usam threads simples e não têm fila durável, cancelamento ou checkpoints por etapa.
- Há scripts de teste manual que dependem de rede, arquivos reais e chave do modelo.
- A chamada de análise pode resumir documentos longos individualmente, multiplicando chamadas.
- `Base.metadata.create_all` ainda é executado no startup, embora o projeto já possua Alembic.
- Parte relevante dos dados estruturados é persistida como JSON em colunas `Text`.

## Métricas a capturar no piloto

Para o fluxo atual e o novo fluxo, registrar por contratação:

- duração de coleta, download, extração/OCR, análise e geração;
- quantidade e volume dos documentos coletados;
- quantidade de PDFs por método de extração e falhas de OCR;
- número de chamadas de IA por finalidade;
- tokens de entrada, saída e total;
- quantidade de tentativas, falhas e reprocessamentos;
- cobertura de critérios por evidências;
- quantidade de perguntas feitas ao usuário;
- tempo de revisão humana e número de decisões alteradas;
- completude e rastreabilidade dos artefatos gerados.

## Política de migração

- Alterações iniciais de banco devem ser aditivas.
- Rotas atuais permanecem enquanto o novo fluxo estiver sob feature flag.
- Dados históricos devem continuar legíveis e exportáveis.
- Remoções exigem substituto funcional, backfill quando aplicável e testes de regressão.
- Mudanças estruturais solicitadas pelo feedback são permitidas, mas devem reutilizar as capacidades desta matriz.

