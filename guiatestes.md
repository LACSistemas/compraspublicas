# Guia de testes do novo fluxo

Este guia valida o fluxo introduzido pelo Plano de Investigação sem remover o comportamento legado. Os comandos partem da raiz do repositório `compraspublicas`.

## 1. O que será testado

O roteiro cobre:

- Plano de Investigação com Cards D001–D014;
- perguntas dinâmicas somente para lacunas;
- coleta automática, inferência, respostas e uploads;
- lacunas obrigatórias e opcionais;
- estados semânticos das informações;
- evidências, conflitos, critérios e validação humana;
- robustez multidimensional;
- reprocessamento seletivo;
- aprovação, dispensa e snapshot da BCC;
- geração de DFD, ETP, Mapa de Riscos e TR;
- orçamento de tokens, jobs, retry e checkpoints;
- isolamento entre usuários;
- fontes jurídicas confirmadas da Lei nº 14.133/2021, TCU e TCE-ES.

## 2. Preparação segura

Não use uma base de produção. Para um teste descartável, configure no `backend/.env`:

```env
DATABASE_URL=sqlite:///./data/teste_manual.db
INVESTIGACAO_HABILITADA=true
GEMINI_API_KEY=SUA_CHAVE
SECRET_KEY=UMA_CHAVE_LOCAL_LONGA
OWNER_EMAIL=owner@example.com
OWNER_PASSWORD=uma-senha-local
TOKEN_BUDGET_CONTRATACAO=500000
```

Não registre a chave do Gemini no Git. O arquivo `backend/.env` já deve permanecer ignorado.

No frontend, crie `frontend/.env.local` se ainda não existir:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 3. Instalação e banco

Backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r ../requirements-dev.txt
.venv/bin/alembic upgrade head
```

Frontend:

```bash
cd frontend
npm install
```

## 4. Testes automatizados

### Backend

```bash
cd backend
.venv/bin/python -m pytest -q
```

Resultado esperado nesta versão:

```text
65 passed
```

Pode aparecer um aviso conhecido de depreciação do `Starlette TestClient`. Ele não representa falha.

### Reversibilidade das migrations

Execute somente contra uma base descartável:

```bash
cd backend
DATABASE_URL=sqlite:////tmp/compraspublicas-migration-test.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite:////tmp/compraspublicas-migration-test.db .venv/bin/alembic downgrade base
DATABASE_URL=sqlite:////tmp/compraspublicas-migration-test.db .venv/bin/alembic upgrade head
```

As três operações devem terminar sem erro.

### Frontend

```bash
cd frontend
npm run build
```

Resultado esperado: compilação e TypeScript concluídos com sucesso.

## 5. Iniciar a aplicação

Terminal 1:

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Acesse:

- frontend: <http://localhost:3000>
- documentação da API: <http://localhost:8000/docs>

Entre com `OWNER_EMAIL` e `OWNER_PASSWORD`. O owner é criado na primeira inicialização caso ainda não exista.

## 6. Roteiro manual principal

### 6.1 Criar a Contratação

1. Acesse **Contratações > Nova contratação**.
2. Informe um objeto suficientemente específico, por exemplo “Aquisição de café torrado e moído para 12 unidades administrativas”.
3. Preencha órgão/unidade, tipo e contexto inicial.
4. Salve e abra a contratação.
5. Clique para iniciar a investigação.

Resultado esperado:

- o status passa por `gerando_plano` e chega a `investigacao`;
- aparece o Plano de Investigação;
- existem 14 Cards, de D001 a D014;
- a quantidade de perguntas é variável e inferior à entrevista fixa legada;
- a repetição da mesma entrada reutiliza o hash registrado e não duplica perguntas.

### 6.2 Conferir lacunas e prioridades

No topo do Plano, confira **Lacunas priorizadas**.

Resultado esperado:

- lacunas obrigatórias aparecem antes das opcionais;
- a prioridade segue `consulta → integração → inferência → pergunta → upload`;
- a tela separa bloqueantes de opcionais;
- somente lacunas obrigatórias impedem a prontidão para gerar conhecimento.

### 6.3 Executar coleta automática

Clique em **Executar coleta**.

Resultado esperado:

- é criada uma Pesquisa vinculada à Contratação;
- consultas e integrações recebem dados ou `coleta_indisponivel`;
- evidências normalizadas são criadas sem duplicar o mesmo conteúdo;
- um job `coleta_plano` registra etapa, tentativa e checkpoint.

Se o portal externo estiver indisponível, o erro deve ficar registrado sem apagar o Plano.

### 6.4 Responder perguntas dinâmicas

Responda as perguntas exibidas no fluxo de investigação.

Resultado esperado para cada resposta:

- a pergunta é persistida individualmente;
- a informação relacionada recebe `coletada_resposta`;
- o estado semântico passa de `nao_informado` para `informado`;
- é criada uma evidência do tipo `declaracao_gestor`;
- apenas o conhecimento do Card relacionado é invalidado, caso já exista.

### 6.5 Enviar documentos obrigatórios

Enquanto a tela de upload dedicada não estiver presente em todos os pontos do fluxo, use a documentação da API.

1. Faça login em `POST /auth/login` no Swagger.
2. Copie o `access_token` e use **Authorize** com o token Bearer.
3. Consulte `GET /contratacoes/{id}/plano`.
4. Localize uma informação cuja estratégia seja `upload` e copie seu campo `id`.
5. Use `POST /contratacoes/{id}/plano/informacoes/{informacao_id}/upload`.

Formatos permitidos: PDF, DOCX e XLSX. Limite padrão: 20 MB.

Resultado esperado:

- nomes como `../documento.pdf` são sanitizados;
- PDF com conteúdo que não começa por `%PDF` é rejeitado;
- o arquivo recebe nome interno aleatório;
- PDF gera evidência primária e, quando possível, texto derivado por extração/OCR;
- o estado semântico passa para `informado`.

## 7. Revisão de evidências e critérios

Na seção **Evidências normalizadas**:

1. confirme ou rejeite uma evidência;
2. marque os critérios efetivamente sustentados;
3. clique em **Salvar critérios**.

Resultado esperado:

- evidência confirmada e vigente leva a informação para `confirmado`;
- evidência rejeitada retorna a informação para `nao_informado`;
- critérios aparecem vinculados por código estável;
- a alteração invalida somente o Card afetado.

Não marque critérios que o documento não sustenta. A robustez depende dessa associação.

## 8. Conflito e substituição explícita

Para testar conflito, envie ou registre uma segunda evidência diferente para a mesma informação.

Resultado esperado:

- a nova evidência fica `conflitante`;
- a informação fica `contraditorio`;
- a evidência anterior não é apagada;
- a substituição exige chamada explícita a `POST /contratacoes/{id}/plano/evidencias/{nova_id}/substituir`, informando `evidencia_anterior_id`;
- após a substituição, a anterior fica `substituida` e a nova fica `vigente`.

## 9. Conhecimento e robustez

Clique em **Avaliar Cards**.

Cada conhecimento deve mostrar:

- conclusão e versão;
- cobertura critério a critério;
- completude;
- confiança;
- atualidade;
- consistência;
- robustez final;
- fontes jurídicas confirmadas.

Regras de aprovação:

- D001, D006, D007, D008, D009 e D014 exigem pelo menos 75%;
- os demais exigem pelo menos 60%;
- conhecimento com evidência obrigatória pendente não pode ser aprovado;
- somente a versão mais recente pode ser revisada;
- todos os Cards exigem aprovação humana final.

Confirme que aparecem links oficiais para a Lei nº 14.133/2021 e, nos Cards pertinentes, TCU e TCE-ES.

## 10. Reprocessamento seletivo

1. Aprove conhecimentos de pelo menos dois Cards.
2. Adicione ou altere evidência de somente um deles.
3. Clique novamente em **Avaliar Cards**.

Resultado esperado:

- somente o conhecimento afetado fica `superado`;
- somente esse Card recebe nova versão;
- os demais conhecimentos permanecem vigentes e não são recalculados.

## 11. Dispensa

Quando o planejador propuser dispensa:

- o Card fica `dispensa_proposta`;
- a justificativa aparece na tela;
- o proprietário pode **Manter Card** ou **Aprovar dispensa**;
- a IA nunca conclui a dispensa sozinha;
- aprovação da dispensa leva as informações a `nao_aplicavel`;
- rejeição reativa o Card e retorna as informações a `nao_informado`.

## 12. Consolidar a BCC

Depois de revisar os conhecimentos, clique em **Consolidar BCC**.

Resultado esperado:

- é criado um snapshot versionado com hash SHA-256;
- decisões, evidências, riscos, recomendações e lacunas preservam o contrato JSON da BCC;
- uma mudança posterior não altera snapshots antigos;
- ETP/TR vinculados à Contratação só usam snapshot contendo todos os Cards aplicáveis aprovados.

## 13. Gerar documentos

A coleta automática cria uma Pesquisa vinculada. Abra essa Pesquisa pela lista de pesquisas e, na geração documental, selecione:

- DFD — Documento de Formalização da Demanda;
- ETP — Estudo Técnico Preliminar;
- Mapa de Riscos;
- TR — Termo de Referência.

Resultado esperado:

- pesquisa independente continua usando o fluxo legado;
- pesquisa vinculada usa `snapshot_bcc_aprovado` como fonte canônica;
- geração é bloqueada se algum Card aplicável não estiver aprovado;
- o JSON gerado contém `rastreabilidade_secoes` com códigos D001–D014;
- lacunas são listadas em `pendencias`, sem preenchimento inventado;
- Edital e Contrato são rejeitados como tipos inválidos.

## 14. Tokens e orçamento

Consulte:

```text
GET /contratacoes/{id}/plano/metricas-ia
```

Resultado esperado:

- consumo separado por planejamento, inferência, Cards, consolidação, redação e legado;
- fases determinísticas apresentam zero tokens;
- `total`, `limite`, `disponivel` e `excedido` são informados.

Para testar o bloqueio, use uma base descartável e defina um limite muito baixo:

```env
TOKEN_BUDGET_CONTRATACAO=1
```

Reinicie o backend e tente uma nova chamada de IA. Ela deve ser bloqueada ou cair no fallback determinístico quando aplicável, sem ultrapassar silenciosamente o orçamento.

## 15. Jobs, retry e checkpoint

Consulte:

```text
GET /contratacoes/{id}/jobs
```

Confira:

- `status`;
- `etapa`;
- `tentativa`;
- `max_tentativas`;
- `checkpoint`;
- `erro_mensagem`.

Para testar retry, provoque temporariamente uma falha recuperável — por exemplo, chave Gemini inválida numa base descartável. O job tentará novamente imediatamente até o limite. Depois, restaure a configuração, reinicie o backend e crie uma nova geração controlada. O comportamento unitário de “falha na primeira tentativa e sucesso na segunda” também está coberto pela suíte automatizada.

Resultado esperado:

- o mesmo job e a mesma referência são mantidos;
- a tentativa é incrementada;
- trabalho já confirmado não é repetido;
- após o limite, o job termina em `tentativas_esgotadas`;
- planejamento idêntico reaproveita seu hash;
- evidências permanecem deduplicadas.

## 16. Isolamento entre usuários

1. Crie um segundo usuário em `/register`.
2. Ative-o pelo owner na administração.
3. Crie uma Contratação com cada usuário.
4. Tente acessar com o segundo usuário os IDs do primeiro via interface ou Swagger.

Resultado esperado: Plano, lacunas, evidências, conhecimentos, métricas, jobs e BCC do outro usuário retornam 404 e não vazam existência ou conteúdo.

## 17. Pesquisa de mercado e preços

1. Abra uma Contratação na etapa **Investigação** ou **Base Pronta**.
2. No card **Pesquisa de mercado e preços**, clique em **Iniciar pesquisa de mercado**.
3. Aguarde as cinco buscas terminarem. Confira os termos usados, processos únicos, preços comparáveis, mediana e confiança.
4. Abra alguns links da **Amostra rastreável** e confronte descrição, órgão, unidade e valor com a fonte.
5. Use **Excluir da amostra** em um item incompatível e confirme que as estatísticas são recalculadas.
6. Se a amostra for insuficiente, clique em **Ampliar pesquisa**. O sistema pode chegar a dez consultas sem repetir termos já usados.
7. Com pelo menos três preços comparáveis, clique em **Aprovar amostra de preços**.
8. Consolide novamente a BCC e gere o ETP/TR.

Resultado esperado:

- cada observação conserva processo, comprador, item, valor e documento de origem quando disponível;
- baixa aderência não entra automaticamente na amostra;
- outliers são separados por intervalo interquartil;
- aprovação é bloqueada abaixo de três preços comparáveis;
- somente a aprovação humana confirma as observações e alimenta I015/I016, BCC e snapshots futuros;
- documentos usam o pacote aprovado; valores pendentes ou rejeitados não viram fundamento.

## 18. Checklist de aceite

- [ ] 71 testes automatizados passam.
- [ ] Migrations sobem, descem e sobem novamente numa base descartável.
- [ ] Build do frontend passa.
- [ ] Plano apresenta D001–D014.
- [ ] Perguntas são variáveis e vinculadas a informações.
- [ ] Lacunas opcionais não bloqueiam conhecimento.
- [ ] Estados semânticos mudam conforme coleta e validação.
- [ ] Conflitos não apagam histórico.
- [ ] Robustez exibe cinco dimensões.
- [ ] Somente o Card afetado é reprocessado.
- [ ] Dispensa e conhecimento exigem decisão humana.
- [ ] Fontes confirmadas apontam para órgãos oficiais.
- [ ] Snapshot aprovado alimenta os documentos.
- [ ] DFD, ETP, Mapa de Riscos e TR são gerados com rastreabilidade.
- [ ] Orçamento bloqueia excesso.
- [ ] Jobs registram tentativa e checkpoint.
- [ ] Usuários não acessam dados alheios.
- [ ] Pesquisa de preços executa 5–10 buscas, deduplica processos e preserva fontes.
- [ ] Amostra aprovada alimenta BCC, I015/I016, ETP e TR.

## 19. Problemas comuns

### Plano não aparece

Confirme `INVESTIGACAO_HABILITADA=true` e reinicie o backend.

### Login do owner falha

Confirme `OWNER_EMAIL`, `OWNER_PASSWORD` e se a base usada é a esperada. O seed não troca a senha de um owner já existente.

### Frontend não encontra a API

Confirme `NEXT_PUBLIC_API_URL=http://localhost:8000` e reinicie `npm run dev`.

### Coleta externa falha

Verifique conectividade e logs do backend. O Plano deve continuar íntegro e o job deve registrar a falha.

### Não consigo aprovar um Card

Confira informações obrigatórias, evidências vigentes, validação, critérios atendidos, conflitos e robustez mínima.

### Não consigo gerar documento

Em pesquisa vinculada, aprove a versão mais recente de todos os Cards aplicáveis e consolide um novo snapshot da BCC.

### Quero repetir tudo do zero

Pare os servidores e remova apenas a base descartável indicada em `DATABASE_URL`. Nunca apague uma base cujo caminho não tenha sido previamente conferido.
