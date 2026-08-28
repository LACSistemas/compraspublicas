# ADR 0001 — Evolução incremental para investigação orientada a Cards

- Status: aceito para piloto
- Data: 2026-08-22
- Origem: `feedback.md` e `tasks.md`

## Contexto

A versão `dea3e76` já implementa Contratação, entrevista fixa de 25 perguntas e BCC em JSON. O feedback posterior determina que o Plano de Investigação deve anteceder perguntas e que informações devem ser obtidas prioritariamente por consulta, integração, inferência, pergunta ou upload.

## Decisão

Manter o fluxo existente disponível e introduzir o novo domínio de forma aditiva, protegido por `INVESTIGACAO_HABILITADA`.

- Catálogos são separados das execuções de Cards.
- O Plano é versionado por Contratação.
- A chamada inicial propõe Cards, informações e estratégias dentro de um catálogo fechado.
- Perguntas são geradas somente para lacunas conversacionais.
- Evidências e conhecimento passam a entidades normalizadas, mas adaptadores mantêm o contrato JSON da BCC durante a migração.
- Inferência nunca equivale a declaração do gestor.
- Nenhum artefato antigo é removido antes de equivalência e regressão comprovadas.

## Consequências

- Há duplicidade transitória entre dados normalizados e o JSON da BCC.
- Migrations são exclusivamente aditivas no piloto.
- O frontend pode operar nos dois fluxos durante a feature flag.
- A robustez aumenta por rastreabilidade, mas exige versionamento, deduplicação e invalidação explícitos.

## Critérios para ampliar além de D001, D003 e D007

- Planejamento determinístico e por IA produzem contratos válidos.
- Consultas, integrações, perguntas, uploads e inferências preservam origem e confiança.
- Evidência pode ser rastreada até informação, Card, Plano e Contratação.
- Fluxo legado continua coberto por testes.
- Custo e número de chamadas não superam o baseline de duas chamadas por contratação sem justificativa.
