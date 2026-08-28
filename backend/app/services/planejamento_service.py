import json
import hashlib
import logging
import os
import threading

from app.database import SessionLocal
from app.models import (CardDecisaoCatalogo, CardInformacao, Contratacao, ExecucaoIA,
    HistoricoContratacao, InformacaoCatalogo, PerguntaContratacao,
    PlanoCardDecisao, PlanoInformacao)
from app.services.gemini_service import chamar_gemini, salvar_uso_tokens
from app.services.plano_investigacao_service import criar_plano_deterministico
from app.services.governanca_ia_service import exigir_orcamento_disponivel
from app.services.job_checkpoint_service import criar_job, executar_com_retry_idempotente
from app.schemas import PropostaPlanoInvestigacao

logger = logging.getLogger("planejamento_service")
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "prompt_plano_investigacao.md")
ESTRATEGIAS = {"consulta", "integracao", "inferencia", "pergunta", "upload"}
PROMPT_VERSAO = "plano-investigacao-v2"


def _serializar_canonico(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_planejamento(entrada: dict, catalogo: list[dict], prompt: str) -> str:
    conteudo = _serializar_canonico({"entrada": entrada, "catalogo": catalogo,
        "prompt": prompt, "prompt_versao": PROMPT_VERSAO})
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


PERGUNTAS_ROBUSTAS = {
    "I001": ("Qual problema concreto a contratação de {objeto} precisa resolver?", [
        "Interrupção ou insuficiência de serviço público já mensurada",
        "Demanda crescente comprovada por registros administrativos",
        "Risco à segurança, saúde ou continuidade operacional",
        "Modernização ou substituição preventiva de solução existente",
        "Outro problema — deverá ser detalhado na rodada complementar"]),
    "I003": ("Qual é o principal resultado mensurável esperado com {objeto}?", [
        "Ampliar capacidade ou cobertura de atendimento", "Reduzir tempo de resposta ou execução",
        "Reduzir falhas, indisponibilidade ou riscos", "Substituir estrutura obsoleta e manter continuidade",
        "Combinação ou outro resultado — deverá ser detalhado"]),
    "I004": ("Como o resultado de {objeto} deverá ser verificado após a contratação?", [
        "Quantidade de atendimentos, entregas ou cobertura", "Tempo médio, prazo ou nível de serviço",
        "Taxa de disponibilidade, falhas ou ocorrências", "Economia obtida ou custo por unidade de resultado",
        "Mais de um indicador ou indicador ainda a definir"]),
    "I005": ("Qual fundamento local sustenta o quantitativo previsto para {objeto}?", [
        "Demanda histórica e projeção de atendimentos", "População, território ou unidades a atender",
        "Capacidade operacional e frequência estimada de uso", "Substituição de bem indisponível ou fim de vida útil",
        "Ainda não há memória de cálculo local suficiente"]),
    "I007": ("A qual instrumento institucional a contratação de {objeto} está alinhada?", [
        "Plano de Contratações Anual", "Planejamento estratégico ou plano setorial",
        "Programa, ação orçamentária ou política pública específica", "Demanda emergencial devidamente motivada",
        "Alinhamento ainda precisa ser identificado e documentado"]),
    "I008": ("Quem será diretamente beneficiado por {objeto}?", [
        "População em geral", "Usuários de serviço público ou grupo territorial específico",
        "Servidores e unidades administrativas", "Equipes operacionais que atendem a população",
        "Mais de um público ou público ainda não delimitado"]),
    "I009": ("Qual grupo de requisitos deve prevalecer na especificação de {objeto}?", [
        "Desempenho e capacidade mínima", "Compatibilidade e integração com estrutura existente",
        "Segurança, qualidade e normas técnicas", "Prazo, garantia, manutenção e assistência técnica",
        "Todos os grupos, com detalhamento técnico posterior"]),
    "I011": ("Quais alternativas ao fornecimento pretendido devem ser comparadas para atender à necessidade?", [
        "Aquisição de bens novos versus aproveitamento ou recuperação dos existentes",
        "Aquisição versus locação ou contratação como serviço", "Execução própria versus contratação externa",
        "Soluções com diferentes tecnologias, capacidades ou configurações",
        "Não há alternativa evidente; o levantamento de mercado deverá identificá-la"]),
    "I013": ("Quais custos devem compor a análise de vantajosidade de {objeto}?", [
        "Aquisição, adaptação e entrega", "Operação, consumo e pessoal necessário",
        "Manutenção, garantia, peças e indisponibilidade", "Descarte, valor residual e ciclo de vida",
        "Todos os custos relevantes, ainda pendentes de memória de cálculo"]),
    "I014": ("Qual fator deverá justificar a escolha final da solução para {objeto}?", [
        "Melhor desempenho técnico para a necessidade", "Menor custo total durante o ciclo de vida",
        "Maior disponibilidade, confiabilidade ou rapidez de implantação",
        "Compatibilidade com infraestrutura e contratos existentes",
        "Combinação ponderada desses fatores"]),
    "I015": ("Qual referência deverá prevalecer na estimativa de preços de {objeto}?", [
        "Contratações públicas recentes e comparáveis", "Painéis ou bancos públicos de preços",
        "Cotações formais de fornecedores", "Tabela oficial ou preço regulado aplicável",
        "Combinação de fontes com tratamento de comparabilidade e outliers"]),
    "I017": ("O objeto {objeto} pode ser dividido em itens ou lotes sem prejudicar o resultado?", [
        "Sim, por itens independentes", "Sim, por lotes técnica ou geograficamente coerentes",
        "Não, pois a integração ou responsabilidade única é indispensável",
        "Não, pois a divisão perderia economia de escala ou inviabilizaria a execução",
        "Ainda depende de estudo técnico e de mercado"]),
    "I019": ("Qual benefício deve ser confrontado com o custo de {objeto}?", [
        "Aumento de capacidade ou cobertura", "Redução de custos operacionais ou manutenção",
        "Redução de riscos e interrupções", "Melhoria de qualidade, desempenho ou tempo de atendimento",
        "Conjunto de benefícios quantitativos e qualitativos"]),
    "I021": ("Que providência precisa estar pronta antes da implantação de {objeto}?", [
        "Adequação física, elétrica, lógica ou de infraestrutura", "Capacitação ou designação de equipe",
        "Licença, autorização, integração ou configuração técnica", "Não há providência prévia relevante",
        "Há múltiplas providências e será necessário detalhar responsáveis e prazos"]),
    "I022": ("Que contratação ou recurso relacionado precisa ser compatível com {objeto}?", [
        "Insumos, consumíveis ou acessórios", "Manutenção, garantia ou assistência técnica",
        "Infraestrutura física, elétrica, lógica ou operacional", "Outro contrato de fornecimento ou serviço",
        "Não há interdependência conhecida ou ainda precisa ser verificada"]),
    "I023": ("Qual impacto ambiental do ciclo de vida de {objeto} merece tratamento prioritário?", [
        "Consumo de energia, água ou combustível", "Emissões, ruído ou poluição durante o uso",
        "Embalagens, resíduos e descarte ao fim da vida útil", "Durabilidade, reparabilidade e logística reversa",
        "Mais de um impacto ou impacto ainda não identificado"]),
    "I025": ("Qual condição determina a conclusão de viabilidade de {objeto}?", [
        "Necessidade, solução e requisitos tecnicamente consistentes", "Preço estimado compatível e orçamento disponível",
        "Mercado competitivo e condições de execução adequadas", "Riscos e providências prévias controláveis",
        "Viabilidade condicionada ao fechamento de pendências críticas"]),
    "I026": ("Qual risco pode impedir ou comprometer a contratação de {objeto}?", [
        "Especificação ou quantitativo inadequado", "Orçamento, preço ou disponibilidade de fornecedores",
        "Atraso, infraestrutura ou dependência de outra contratação", "Falha de operação, manutenção ou fiscalização",
        "Mais de um risco ou risco crítico ainda não identificado"]),
}


def _pergunta_fallback(info: dict, objeto: str = "o objeto") -> dict:
    texto, opcoes = PERGUNTAS_ROBUSTAS.get(info["codigo"],
        (f"Qual definição objetiva deve constar nos documentos sobre {info['nome']} para {objeto}?", [
            f"Adotar a definição técnica descrita no contexto da contratação",
            f"Adotar referência de contratação anterior comparável", "Realizar estudo ou validação específica",
            "A informação não se aplica ao objeto", "A informação ainda precisa ser detalhada pelo gestor"]))
    return {"texto": texto.format(objeto=objeto), "alternativas": [
        {"letra": letra, "texto": opcao} for letra, opcao in zip("abcde", opcoes)]}


def _proposta_fallback(catalogo: list[dict], objeto: str = "o objeto") -> dict:
    cards = []
    for card in catalogo:
        infos = []
        for info in card["informacoes"]:
            estrategia = info["estrategia_preferencial"]
            infos.append({"codigo": info["codigo"], "estrategia": estrategia,
                "justificativa": "Estratégia preferencial definida no catálogo versionado",
                "pergunta": _pergunta_fallback(info, objeto) if estrategia == "pergunta" else None})
        cards.append({"codigo": card["codigo"], "aplicavel": True,
            "justificativa": "Aplicabilidade padrão do catálogo piloto", "informacoes": infos})
    return {"cards": cards}


def _validar_qualidade_perguntas(dados: dict) -> None:
    assinaturas: dict[tuple[str, ...], int] = {}
    problemas = []
    for card in dados.get("cards", []):
        for info in card.get("informacoes", []):
            if info.get("estrategia") != "pergunta":
                continue
            pergunta = info.get("pergunta") or {}
            texto = str(pergunta.get("texto") or "").strip()
            alternativas = pergunta.get("alternativas") or []
            opcoes = tuple(_normalizar_pergunta(a.get("texto", "")) for a in alternativas)
            assinatura = tuple(opcoes)
            assinaturas[assinatura] = assinaturas.get(assinatura, 0) + 1
            generica = (len(texto) < 25
                or "qual e a situacao" in _normalizar_pergunta(texto)
                or "informacao formalizada" in " ".join(opcoes)
                or any(len(opcao) < 10 for opcao in opcoes))
            if generica:
                problemas.append(info.get("codigo", "sem-codigo"))
    repetidas = [quantidade for assinatura, quantidade in assinaturas.items()
        if assinatura and quantidade > 1]
    if problemas or repetidas:
        raise ValueError("Perguntas sem especificidade documental: " +
            ", ".join(problemas or ["alternativas repetidas entre informações distintas"]))


def _normalizar_pergunta(texto: str) -> str:
    return " ".join(str(texto).lower().replace(":", " ").split())


def _reparar_planejamento(prompt: str, dados_ruins: dict, erro: Exception) -> tuple[dict, object]:
    prompt_reparo = prompt + "\n\nA PRIMEIRA PROPOSTA FOI REJEITADA.\n" + str(erro) + (
        "\nReescreva integralmente as perguntas. Cada pergunta deve produzir conteúdo diretamente "
        "utilizável em DFD, ETP, TR e mapa de riscos. As alternativas devem representar decisões "
        "materiais sobre o objeto, nunca o grau de formalização da informação. Não repita o mesmo "
        "conjunto de alternativas em informações diferentes. Preserve todos os códigos e o schema.\n"
        "PROPOSTA REJEITADA:\n" + json.dumps(dados_ruins, ensure_ascii=False))
    return chamar_gemini(prompt_reparo)


def _catalogo(db, plano):
    saida = []
    itens = db.query(PlanoCardDecisao).filter_by(plano_id=plano.id).order_by(PlanoCardDecisao.ordem).all()
    for item in itens:
        card = db.query(CardDecisaoCatalogo).filter_by(id=item.card_id).one()
        infos = []
        for vinculo in db.query(CardInformacao).filter_by(card_id=card.id).order_by(CardInformacao.ordem):
            info = db.query(InformacaoCatalogo).filter_by(id=vinculo.informacao_id).one()
            infos.append({"codigo": info.codigo, "nome": info.nome, "objetivo": info.objetivo,
                "tipo": info.tipo, "obrigatoriedade": info.obrigatoriedade,
                "estrategia_preferencial": info.estrategia_preferencial})
        saida.append({"codigo": card.codigo, "nome": card.nome,
            "pergunta_controle": card.pergunta_controle, "informacoes": infos})
    return saida


def _validar_e_persistir(db, contratacao, plano, dados):
    dados = PropostaPlanoInvestigacao.model_validate(dados).model_dump()
    cards_entrada = {c["codigo"]: c for c in dados.get("cards", [])}
    ordem_pergunta = 1
    for item in db.query(PlanoCardDecisao).filter_by(plano_id=plano.id).order_by(PlanoCardDecisao.ordem):
        card = db.query(CardDecisaoCatalogo).filter_by(id=item.card_id).one()
        proposta_card = cards_entrada.get(card.codigo, {})
        item.aplicavel = proposta_card.get("aplicavel") is not False
        if not item.aplicavel:
            item.status = "dispensa_proposta"
            item.dispensa_status = "proposta"
            item.justificativa_dispensa = proposta_card.get("justificativa") or "Dispensa proposta no planejamento"
        propostas_info = {i.get("codigo"): i for i in proposta_card.get("informacoes", [])}
        for vinculo in db.query(CardInformacao).filter_by(card_id=card.id).order_by(CardInformacao.ordem):
            info = db.query(InformacaoCatalogo).filter_by(id=vinculo.informacao_id).one()
            proposta = propostas_info.get(info.codigo, {})
            estrategia = proposta.get("estrategia", info.estrategia_preferencial)
            if estrategia not in ESTRATEGIAS:
                estrategia = info.estrategia_preferencial
            status_info = "dispensada" if not item.aplicavel else (
                "aguardando_resposta" if estrategia == "pergunta" else
                "aguardando_upload" if estrategia == "upload" else "pendente_coleta"
            )
            pi = PlanoInformacao(plano_card_id=item.id, informacao_id=info.id, estrategia=estrategia,
                status=status_info,
                estado_semantico="nao_aplicavel" if not item.aplicavel else "nao_informado",
                justificativa_estrategia=proposta.get("justificativa"))
            db.add(pi)
            db.flush()
            if item.aplicavel and estrategia == "pergunta":
                pergunta = proposta.get("pergunta") or {}
                alternativas = pergunta.get("alternativas") or []
                textos_alternativas = " ".join(str(a.get("texto", "")) for a in alternativas).lower()
                if ("qual é a situação atual de" in str(pergunta.get("texto", "")).lower()
                        or "informação formalizada e documentada" in textos_alternativas):
                    pergunta = _pergunta_fallback({"codigo": info.codigo, "nome": info.nome},
                        contratacao.objeto)
                    alternativas = pergunta["alternativas"]
                letras = [a.get("letra") for a in alternativas]
                if len(alternativas) != 5 or letras != ["a", "b", "c", "d", "e"]:
                    raise ValueError(f"Alternativas inválidas para {info.codigo}")
                texto = pergunta.get("texto")
                if not texto:
                    raise ValueError(f"Pergunta ausente para {info.codigo}")
                db.add(PerguntaContratacao(contratacao_id=contratacao.id, plano_informacao_id=pi.id,
                    ordem=ordem_pergunta, texto=texto,
                    alternativas_json=json.dumps(alternativas, ensure_ascii=False)))
                ordem_pergunta += 1


def _executar_coleta_deterministica(db, contratacao, plano):
    for execucao in (db.query(PlanoInformacao).join(PlanoCardDecisao)
            .filter(PlanoCardDecisao.plano_id == plano.id).all()):
        if execucao.estrategia != "inferencia" or execucao.status != "pendente_coleta":
            continue
        info = db.query(InformacaoCatalogo).filter_by(id=execucao.informacao_id).one()
        contexto = contratacao.contexto_inicial or ""
        if not contexto.strip():
            execucao.status = "inferencia_indisponivel"
            execucao.origem = "sistema"
            execucao.confianca = "baixa"
            continue
        execucao.valor_json = json.dumps({"valor_candidato": contexto,
            "aviso": f"Inferência candidata para {info.nome}; exige confirmação"}, ensure_ascii=False)
        execucao.status = "coletada_inferida"
        execucao.estado_semantico = "inferido"
        execucao.origem = "inferencia_contexto_inicial"
        execucao.confianca = "baixa"


def _job_planejar(contratacao_id: int):
    db = SessionLocal()
    try:
        c = db.query(Contratacao).filter_by(id=contratacao_id).first()
        if c is None:
            return
        plano = criar_plano_deterministico(db, c)
        catalogo = _catalogo(db, plano)
        template = open(_PROMPT_PATH, encoding="utf-8").read()
        entrada = {"objeto": c.objeto,
            "orgao_unidade": c.orgao_unidade, "tipo": c.tipo_contratacao,
            "contexto": c.contexto_inicial}
        prompt = template.format(contratacao_json=json.dumps(entrada, ensure_ascii=False),
            catalogo_json=json.dumps(catalogo, ensure_ascii=False))
        hash_entrada = _hash_planejamento(entrada, catalogo, prompt)
        cache = db.query(ExecucaoIA).filter(ExecucaoIA.fase == "plano_investigacao",
            ExecucaoIA.hash_entrada == hash_entrada,
            ExecucaoIA.status.in_(["sucesso", "fallback"])).order_by(ExecucaoIA.id.desc()).first()
        if cache is not None and db.query(PlanoInformacao).join(PlanoCardDecisao).filter(
                PlanoCardDecisao.plano_id == plano.id).count() > 0:
            c.status = "investigacao"
            db.add(HistoricoContratacao(contratacao_id=c.id, usuario_id=c.usuario_id,
                acao="Plano de Investigação reutilizado",
                detalhe=f"Execução IA #{cache.id} | hash {hash_entrada[:12]}"))
            db.commit()
            return
        execucao_ia = ExecucaoIA(contratacao_id=c.id, plano_id=plano.id,
            fase="plano_investigacao", hash_entrada=hash_entrada,
            modelo=None, prompt_versao=PROMPT_VERSAO, prompt_texto=prompt,
            entrada_json=_serializar_canonico(entrada), catalogo_json=_serializar_canonico(catalogo),
            status="pendente")
        db.add(execucao_ia)
        db.flush()
        usou_fallback = False
        try:
            exigir_orcamento_disponivel(db, c.id)
            dados, tokens = chamar_gemini(prompt)
            dados = PropostaPlanoInvestigacao.model_validate(dados).model_dump()
            try:
                _validar_qualidade_perguntas(dados)
            except ValueError as erro_qualidade:
                logger.warning("Saída inicial sem qualidade; solicitando reparação: %s", erro_qualidade)
                dados, tokens = _reparar_planejamento(prompt, dados, erro_qualidade)
                dados = PropostaPlanoInvestigacao.model_validate(dados).model_dump()
                _validar_qualidade_perguntas(dados)
            execucao_ia.modelo = tokens.modelo
            execucao_ia.tokens_input, execucao_ia.tokens_output = tokens.input, tokens.output
            execucao_ia.tokens_total, execucao_ia.status = tokens.total, "sucesso"
        except Exception as exc:
            logger.warning("Planejamento por IA inválido/indisponível; usando fallback: %s", exc)
            dados, tokens, usou_fallback = _proposta_fallback(catalogo, c.objeto), None, True
            execucao_ia.status, execucao_ia.erro_mensagem = "fallback", str(exc)
        execucao_ia.saida_json = _serializar_canonico(dados)
        _validar_e_persistir(db, c, plano, dados)
        _executar_coleta_deterministica(db, c, plano)
        if tokens is not None:
            salvar_uso_tokens(db, c.usuario_id, "plano_investigacao", tokens, c.id)
        c.status = "investigacao"
        db.add(HistoricoContratacao(contratacao_id=c.id, usuario_id=c.usuario_id,
            acao="Plano de Investigação proposto pela IA",
            detalhe=(f"{len(catalogo)} Cards | " +
                ("Fallback determinístico" if usou_fallback else f"Tokens: {tokens.total}"))))
        db.commit()
    except Exception as exc:
        logger.exception("Erro ao planejar contratacao_id=%s", contratacao_id)
        db.rollback()
        c = db.query(Contratacao).filter_by(id=contratacao_id).first()
        if c:
            c.status, c.erro_mensagem = "erro", str(exc)
            db.commit()
    finally:
        db.close()


def retomar_planejamento(job_id: int, contratacao_id: int):
    def executar():
        def estado():
            sessao = SessionLocal()
            try:
                c = sessao.query(Contratacao).filter_by(id=contratacao_id).first()
                return c.status if c else None
            finally:
                sessao.close()
        executar_com_retry_idempotente(SessionLocal, job_id,
            lambda: _job_planejar(contratacao_id), lambda: estado() == "investigacao",
            etapa_execucao="planejando", etapa_sucesso="plano_persistido",
            checkpoint=lambda: {"contratacao_status": estado()})

    threading.Thread(target=executar, daemon=True).start()


def iniciar_planejamento(contratacao_id: int):
    db = SessionLocal()
    try:
        job = criar_job(db, "planejamento", contratacao_id, referencia_id=contratacao_id)
        job_id = job.id
    finally:
        db.close()
    retomar_planejamento(job_id, contratacao_id)
