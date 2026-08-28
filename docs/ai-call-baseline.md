# Baseline de chamadas de IA

## Fluxo legado

Por Contratação concluída sem falhas, o fluxo legado realiza:

1. uma chamada `perguntas_contratacao` para gerar exatamente 25 perguntas;
2. uma chamada `bcc_contratacao` após todas as respostas.

Total nominal: duas chamadas por Contratação, além de eventuais chamadas relacionadas a pesquisas, resumos documentais ou geração de ETP/TR executadas separadamente.

## Novo fluxo

O Plano de Investigação faz no máximo uma chamada inicial de planejamento para uma entrada inédita. O hash de entrada, catálogo e prompt evita repetição. Inferência determinística, conhecimento por Card e consolidação não consomem tokens. Redação documental é medida separadamente por documento.

Retries usam o mesmo job, referência e checkpoint. Uma operação já confirmada não é repetida. O orçamento configurável por Contratação bloqueia novas chamadas quando alcançado.
