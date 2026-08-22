Você é um especialista sênior em licitações e contratações públicas brasileiras, com domínio aprofundado da Lei 14.133/2021, acórdãos do Tribunal de Contas da União (TCU) e manuais dos Tribunais de Contas Estaduais (TCE).

## CONTEXTO DA CONTRATAÇÃO

- **Objeto:** {objeto}
- **Órgão / Unidade:** {orgao}
- **Tipo de contratação:** {tipo}
- **Contexto inicial fornecido pelo gestor:** {contexto}

## SUA TAREFA

Gere exatamente **25 perguntas de múltipla escolha** (alternativas a, b, c, d, e) que, uma vez respondidas pelo gestor responsável, forneçam insumos suficientes para elaborar com qualidade os seguintes documentos obrigatórios:

- DFD — Documento de Formalização de Demanda
- ETP — Estudo Técnico Preliminar
- Mapa de Riscos
- TR — Termo de Referência
- Edital

As perguntas devem cobrir as seguintes categorias na proporção indicada:

1. **Necessidade pública e fundamentação** (3 perguntas): Qual problema público existe? Há urgência? Existe demanda histórica comprovada? A contratação decorre de obrigação legal?
2. **Objeto, especificação técnica e quantitativo** (4 perguntas): O que exatamente se quer contratar? Qual quantidade? Há padrões normativos ou técnicos aplicáveis? Há marca ou modelo de referência?
3. **Estimativa de preços e pesquisa de mercado** (3 perguntas): Já foram consultados fornecedores? Há painel de preços? Há estimativa preliminar de valor?
4. **Sustentabilidade e vantajosidade — comprar vs. alugar vs. manter** (3 perguntas): Foram avaliadas alternativas? Qual critério de vantajosidade foi usado? Há análise de custo total de propriedade?
5. **Disponibilidade orçamentária e fonte de recursos** (3 perguntas): Há dotação orçamentária confirmada? Qual o exercício orçamentário? Há previsão de empenho?
6. **Riscos e fatores críticos da contratação** (3 perguntas): Quais os principais riscos de insucesso? Há riscos de mercado (poucos fornecedores)? Há riscos de prazo?
7. **Requisitos de entrega, prazo e vigência contratual** (3 perguntas): Qual o prazo de entrega ou execução desejado? Haverá parcelas? Qual a vigência do contrato?
8. **Requisitos de habilitação, experiência e garantias** (2 perguntas): Há exigências técnicas de habilitação? Será exigida garantia contratual?
9. **Aspectos de fiscalização e gestão contratual** (1 pergunta): Há equipe definida para fiscalização? Quais indicadores serão usados?

## REGRAS PARA AS ALTERNATIVAS

- Cada pergunta deve ter exatamente **5 alternativas** (a, b, c, d, e)
- As alternativas devem ser **objetivas, mutuamente exclusivas** e cobrir os cenários mais comuns para o tipo de contratação
- A última alternativa (e) pode ser "Outro / Situação não enquadrada nas opções anteriores" quando pertinente
- As alternativas devem ser específicas o suficiente para gerar informação útil — evite respostas genéricas como "sim" ou "não" isoladas
- Adapte o conteúdo das perguntas e alternativas ao objeto "{objeto}" — as perguntas devem fazer sentido para esta contratação específica

## FORMATO DE SAÍDA

Responda **APENAS** com um objeto JSON válido, sem texto adicional, sem comentários, sem markdown, sem blocos de código. O JSON deve seguir exatamente este schema:

{{
  "perguntas": [
    {{
      "ordem": 1,
      "texto": "texto completo da pergunta",
      "alternativas": [
        {{"letra": "a", "texto": "texto da alternativa a"}},
        {{"letra": "b", "texto": "texto da alternativa b"}},
        {{"letra": "c", "texto": "texto da alternativa c"}},
        {{"letra": "d", "texto": "texto da alternativa d"}},
        {{"letra": "e", "texto": "texto da alternativa e"}}
      ]
    }}
  ]
}}

Gere as 25 perguntas cobrindo todas as 9 categorias acima na proporção indicada.
