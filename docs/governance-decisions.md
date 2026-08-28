# Decisões de governança do Plano de Investigação

## Jurisdição

A jurisdição inicial é o Estado do Espírito Santo. A curadoria local usa o TCE-ES. Fontes federais continuam sendo usadas quando aplicáveis, especialmente a Lei nº 14.133/2021 e jurisprudência do TCU.

Somente fontes cadastradas, oficiais e marcadas como confirmadas podem aparecer como `fontes_confirmadas`. Texto ou citação propostos pela IA são material candidato e não recebem esse status automaticamente.

## Manifestação formal

Os Cards D001, D006, D007, D008, D009 e D014 são críticos e exigem manifestação humana explícita, representada pela aprovação da versão vigente do conhecimento. Sua robustez mínima é 75%.

Os demais Cards também exigem aprovação humana final, mas podem ser instruídos por informações coletadas ou inferidas posteriormente confirmadas. Sua robustez mínima é 60%.

## Alçada

Na versão inicial, a alçada de aprovação de conhecimento e de dispensa pertence ao usuário proprietário da Contratação. Todas as rotas verificam o `usuario_id` da Contratação. Uma matriz com aprovadores distintos deve ser introduzida antes de uso multiárea ou segregação formal de funções.

## Documentos e AI Studio

O termo DPD foi interpretado como DFD. A cadeia preparatória aceita DFD, ETP, Mapa de Riscos e TR. Edital e Contrato permanecem fora dos tipos aceitos.

A comparação visual com o protótipo do AI Studio foi dispensada para o aceite técnico atual, pois não há referência acessível. O comportamento é validado pelos contratos de API, testes automatizados, migrations reversíveis e build de produção.
