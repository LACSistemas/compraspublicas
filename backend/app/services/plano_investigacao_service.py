import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    CardDecisaoCatalogo,
    CardInformacao,
    CardDependencia,
    CriterioCardCatalogo,
    Contratacao,
    HistoricoContratacao,
    InformacaoCatalogo,
    PlanoCardDecisao,
    PlanoInvestigacao,
    FonteJuridica,
    CardFonteJuridica,
)


INFORMACOES = [
    ("I001", "Problema público", "Caracterizar o problema que exige atuação administrativa", "texto", "obrigatoria", "pergunta"),
    ("I002", "Público afetado", "Identificar quem é afetado e a dimensão da necessidade", "texto", "recomendada", "consulta"),
    ("I003", "Resultados pretendidos", "Definir resultados mensuráveis da contratação", "texto", "obrigatoria", "pergunta"),
    ("I004", "Indicadores de resultado", "Definir como os resultados serão verificados", "texto", "recomendada", "pergunta"),
    ("I005", "Memória de cálculo do quantitativo", "Demonstrar premissas e cálculo da quantidade", "upload", "obrigatoria", "upload"),
    ("I006", "Histórico de consumo", "Obter série histórica ou referência equivalente", "numero", "recomendada", "integracao"),
    ("I007", "Alinhamento institucional", "Demonstrar o alinhamento da demanda com objetivos e planos institucionais", "texto", "obrigatoria", "consulta"),
    ("I008", "Interesse coletivo", "Identificar beneficiários e o interesse público atendido", "texto", "obrigatoria", "pergunta"),
    ("I009", "Requisitos da contratação", "Definir requisitos funcionais, técnicos e de desempenho", "texto", "obrigatoria", "pergunta"),
    ("I010", "Normas e padrões aplicáveis", "Identificar normas, padrões e restrições aplicáveis", "texto", "recomendada", "consulta"),
    ("I011", "Alternativas disponíveis", "Levantar alternativas capazes de atender à necessidade", "texto", "obrigatoria", "pergunta"),
    ("I012", "Análise comparativa", "Comparar alternativas por critérios técnicos e econômicos", "upload", "recomendada", "upload"),
    ("I013", "Custo total e vantajosidade", "Demonstrar custos do ciclo de vida e vantajosidade", "upload", "obrigatoria", "upload"),
    ("I014", "Justificativa da solução", "Justificar a solução escolhida diante das alternativas", "texto", "obrigatoria", "pergunta"),
    ("I015", "Pesquisa de preços", "Fundamentar o valor estimado da contratação", "upload", "obrigatoria", "upload"),
    ("I016", "Fontes e cotações", "Registrar fontes, datas e condições das referências de preço", "texto", "recomendada", "integracao"),
    ("I017", "Divisibilidade do objeto", "Avaliar a possibilidade técnica e econômica de parcelamento", "texto", "obrigatoria", "pergunta"),
    ("I018", "Competição e economia de escala", "Avaliar impactos do parcelamento sobre competição e escala", "texto", "recomendada", "consulta"),
    ("I019", "Benefícios e custos esperados", "Relacionar benefícios esperados aos custos da solução", "texto", "obrigatoria", "pergunta"),
    ("I020", "Metas associadas", "Associar resultados a metas e indicadores verificáveis", "texto", "recomendada", "inferencia"),
    ("I021", "Providências prévias", "Identificar adequações, capacitações e recursos prévios necessários", "texto", "obrigatoria", "pergunta"),
    ("I022", "Contratações correlatas", "Identificar contratações correlatas ou interdependentes", "texto", "obrigatoria", "integracao"),
    ("I023", "Impactos ambientais", "Identificar impactos ambientais da solução e de seu ciclo de vida", "texto", "obrigatoria", "pergunta"),
    ("I024", "Medidas de sustentabilidade", "Definir medidas de prevenção, mitigação e sustentabilidade", "texto", "recomendada", "consulta"),
    ("I025", "Conclusão de viabilidade", "Consolidar a conclusão sobre a viabilidade da contratação", "texto", "obrigatoria", "inferencia"),
    ("I026", "Impedimentos e riscos críticos", "Identificar impedimentos e riscos que afetem a viabilidade", "texto", "obrigatoria", "pergunta"),
]

CARDS = [
    ("D001", "Necessidade pública", "Existe necessidade pública suficientemente caracterizada?", ["art. 18, I, da Lei 14.133/2021"], ["problema público caracterizado", "público afetado identificado"], ["declaracao", "documento de demanda"], ["DFD", "ETP"], ["I001", "I002"]),
    ("D003", "Resultados pretendidos", "Os resultados pretendidos estão definidos e são verificáveis?", ["art. 18, §1º, IX, da Lei 14.133/2021"], ["resultado definido", "indicador verificável"], ["declaracao", "plano institucional"], ["ETP", "TR"], ["I003", "I004"]),
    ("D007", "Fundamentação do quantitativo", "O quantitativo está fundamentado por memória de cálculo?", ["art. 18, §1º, IV, da Lei 14.133/2021"], ["memória de cálculo", "premissas rastreáveis"], ["memoria de calculo", "historico de consumo"], ["ETP", "TR"], ["I005", "I006"]),
    ("D002", "Interesse público", "A contratação atende a interesse público demonstrável?", ["art. 18, caput, da Lei 14.133/2021"], ["alinhamento institucional demonstrado", "beneficiários identificados"], ["plano institucional", "declaracao"], ["DFD", "ETP"], ["I007", "I008"]),
    ("D004", "Requisitos", "Os requisitos da contratação foram definidos de forma suficiente?", ["art. 18, §1º, III, da Lei 14.133/2021"], ["requisitos funcionais e técnicos definidos", "normas aplicáveis identificadas"], ["especificacao tecnica", "norma tecnica"], ["ETP", "TR"], ["I009", "I010"]),
    ("D005", "Alternativas", "As alternativas para atendimento da necessidade foram avaliadas?", ["art. 18, §1º, V, da Lei 14.133/2021"], ["alternativas relevantes levantadas", "comparação técnica e econômica realizada"], ["estudo comparativo", "levantamento de mercado"], ["ETP"], ["I011", "I012"]),
    ("D006", "Vantajosidade da solução", "A solução escolhida é a alternativa mais vantajosa?", ["art. 18, §1º, V e IX, da Lei 14.133/2021"], ["custo total considerado", "escolha justificada diante das alternativas"], ["analise de custo", "justificativa tecnica"], ["ETP", "TR"], ["I013", "I014"]),
    ("D008", "Valor estimado", "O valor estimado está adequadamente fundamentado?", ["art. 18, §1º, VI, da Lei 14.133/2021"], ["pesquisa de preços válida", "fontes e condições rastreáveis"], ["pesquisa de precos", "cotacao"], ["ETP", "TR"], ["I015", "I016"]),
    ("D009", "Parcelamento", "O parcelamento adotado é técnica e economicamente adequado?", ["art. 18, §1º, VIII, da Lei 14.133/2021"], ["divisibilidade avaliada", "competição e economia de escala consideradas"], ["analise de parcelamento", "estudo de mercado"], ["ETP", "TR"], ["I017", "I018"]),
    ("D010", "Justificativa por resultados", "Os resultados esperados justificam os custos da contratação?", ["art. 18, §1º, IX, da Lei 14.133/2021"], ["benefícios relacionados aos custos", "metas verificáveis associadas"], ["memoria de beneficios", "plano de resultados"], ["ETP", "TR"], ["I019", "I020"]),
    ("D011", "Providências prévias", "As providências prévias necessárias foram identificadas?", ["art. 18, §1º, X, da Lei 14.133/2021"], ["adequações necessárias identificadas", "responsáveis ou prazos definidos"], ["plano de providencias", "plano de capacitacao"], ["ETP", "TR"], ["I021"]),
    ("D012", "Contratações correlatas", "As contratações correlatas ou interdependentes foram consideradas?", ["art. 18, §1º, XI, da Lei 14.133/2021"], ["contratações correlatas identificadas", "interdependências avaliadas"], ["contrato", "plano de contratacoes"], ["ETP"], ["I022"]),
    ("D013", "Impactos ambientais", "Os impactos ambientais e as medidas de sustentabilidade foram avaliados?", ["art. 18, §1º, XII, da Lei 14.133/2021"], ["impactos do ciclo de vida identificados", "medidas de mitigação definidas"], ["estudo ambiental", "plano de sustentabilidade"], ["ETP", "TR"], ["I023", "I024"]),
    ("D014", "Viabilidade", "A contratação é viável diante do conjunto das análises?", ["art. 18, §1º, XIII, da Lei 14.133/2021"], ["conclusão coerente com as evidências", "riscos críticos e impedimentos tratados"], ["parecer de viabilidade", "matriz de riscos"], ["ETP"], ["I025", "I026"]),
]

ORDEM_CARDS = tuple(f"D{numero:03d}" for numero in range(1, 15))

DEPENDENCIAS = {
    "D002": ("D001",), "D003": ("D001",), "D004": ("D003",),
    "D005": ("D004",), "D006": ("D005",), "D007": ("D004",),
    "D008": ("D004",), "D009": ("D007",), "D010": ("D003", "D006"),
    "D011": ("D004",), "D012": ("D004",), "D013": ("D004",),
    "D014": ("D006", "D007", "D008", "D009", "D010", "D011", "D012", "D013"),
}

TIPOS_INFORMACAO = {"texto", "numero", "upload"}
ESTRATEGIAS_COLETA = {"consulta", "integracao", "inferencia", "pergunta", "upload"}
OBRIGATORIEDADES = {"obrigatoria", "recomendada"}


def validar_catalogo() -> None:
    codigos_info = [item[0] for item in INFORMACOES]
    codigos_cards = [item[0] for item in CARDS]
    if len(codigos_info) != len(set(codigos_info)):
        raise ValueError("Catálogo contém códigos de informação duplicados")
    if len(codigos_cards) != len(set(codigos_cards)) or set(codigos_cards) != set(ORDEM_CARDS):
        raise ValueError("Catálogo deve conter exatamente os Cards D001–D014, sem duplicidade")
    for codigo, _, _, tipo, obrigatoriedade, estrategia in INFORMACOES:
        if tipo not in TIPOS_INFORMACAO:
            raise ValueError(f"Tipo inválido para {codigo}: {tipo}")
        if obrigatoriedade not in OBRIGATORIEDADES:
            raise ValueError(f"Obrigatoriedade inválida para {codigo}: {obrigatoriedade}")
        if estrategia not in ESTRATEGIAS_COLETA:
            raise ValueError(f"Estratégia inválida para {codigo}: {estrategia}")
    for codigo, _, _, base, criterios, _, _, infos in CARDS:
        if not base or not criterios:
            raise ValueError(f"Card {codigo} exige base legal e critérios")
        desconhecidas = set(infos) - set(codigos_info)
        if desconhecidas:
            raise ValueError(f"Card {codigo} referencia informações inexistentes: {sorted(desconhecidas)}")
    if set(DEPENDENCIAS) - set(codigos_cards):
        raise ValueError("Dependência definida para Card inexistente")
    grafo = {codigo: tuple(DEPENDENCIAS.get(codigo, ())) for codigo in codigos_cards}
    if any(set(deps) - set(codigos_cards) for deps in grafo.values()):
        raise ValueError("Dependência referencia Card inexistente")
    visitando, visitados = set(), set()

    def visitar(codigo: str) -> None:
        if codigo in visitando:
            raise ValueError(f"Ciclo detectado nas dependências do Card {codigo}")
        if codigo in visitados:
            return
        visitando.add(codigo)
        for dependencia in grafo[codigo]:
            visitar(dependencia)
        visitando.remove(codigo)
        visitados.add(codigo)

    for codigo in codigos_cards:
        visitar(codigo)


def garantir_catalogo_piloto(db: Session) -> None:
    validar_catalogo()
    fonte_lei = db.query(FonteJuridica).filter_by(codigo="LEI-14133-2021").first()
    if fonte_lei is None:
        fonte_lei = FonteJuridica(codigo="LEI-14133-2021", tipo="lei",
            titulo="Lei nº 14.133, de 1º de abril de 2021",
            referencia="Lei 14.133/2021", orgao_emissor="Presidência da República",
            url_oficial="https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm",
            confirmada=True, metadados_json=json.dumps({"fonte": "Planalto",
                "escopo": "normas gerais de licitação e contratação"}),
            verificada_em=datetime.now(timezone.utc).replace(tzinfo=None))
        db.add(fonte_lei)
        db.flush()
    repositorio_tcu = db.query(FonteJuridica).filter_by(codigo="TCU-JURIS-REPOSITORIO").first()
    if repositorio_tcu is None:
        db.add(FonteJuridica(codigo="TCU-JURIS-REPOSITORIO", tipo="repositorio_jurisprudencia",
            titulo="Pesquisa de jurisprudência do Tribunal de Contas da União",
            referencia="Repositório oficial de pesquisa TCU", orgao_emissor="TCU",
            url_oficial="https://pesquisa.apps.tcu.gov.br/",
            confirmada=True, metadados_json=json.dumps({"vinculacao_cards": False,
                "aviso": "Repositório confirmado; precedentes exigem curadoria individual"}),
            verificada_em=datetime.now(timezone.utc).replace(tzinfo=None)))
    precedente_tcu = db.query(FonteJuridica).filter_by(codigo="TCU-AC-764-2025-P").first()
    if precedente_tcu is None:
        precedente_tcu = FonteJuridica(codigo="TCU-AC-764-2025-P", tipo="jurisprudencia",
            titulo="Acórdão 764/2025-TCU-Plenário", referencia="Levantamento de mercado e requisitos no ETP",
            orgao_emissor="TCU",
            url_oficial="https://pesquisa.apps.tcu.gov.br/documento/acordao-completo/%2A/NUMACORDAO%253A764%2520ANOACORDAO%253A2025%2520COLEGIADO%253A%2522Plen%25C3%25A1rio%2522/DTRELEVANCIA%2520desc/0/sinonimos%253Dfalse",
            confirmada=True, metadados_json=json.dumps({"colegiado": "Plenário", "ano": 2025,
                "tese": "ETP deve identificar alternativas de mercado e justificar requisitos restritivos"}),
            verificada_em=datetime.now(timezone.utc).replace(tzinfo=None))
        db.add(precedente_tcu)
        db.flush()
    portal_tcees = db.query(FonteJuridica).filter_by(codigo="TCEES-NLLC-PORTAL").first()
    if portal_tcees is None:
        db.add(FonteJuridica(codigo="TCEES-NLLC-PORTAL", tipo="repositorio_jurisprudencia",
            titulo="Portal de orientação da Nova Lei de Licitações e Contratos",
            referencia="Portal oficial TCE-ES", orgao_emissor="TCE-ES",
            url_oficial="https://www.tcees.tc.br/carta-de-servicos/servico/328797/",
            confirmada=True, metadados_json=json.dumps({"jurisdicao": "Espírito Santo",
                "vinculacao_cards": False}),
            verificada_em=datetime.now(timezone.utc).replace(tzinfo=None)))
    precedente_tcees = db.query(FonteJuridica).filter_by(codigo="TCEES-INF-136-ITEM-30").first()
    if precedente_tcees is None:
        precedente_tcees = FonteJuridica(codigo="TCEES-INF-136-ITEM-30",
            tipo="jurisprudencia", titulo="Informativo de Jurisprudência TCE-ES nº 136, item 30",
            referencia="Planejamento e comparação efetiva de soluções no ETP",
            orgao_emissor="TCE-ES",
            url_oficial="https://www.tcees.tc.br/wp-content/uploads/formidable/44/Informativo-de-Jurisprudencia-136.pdf",
            confirmada=True, metadados_json=json.dumps({"jurisdicao": "Espírito Santo",
                "tese": "ETP não pode validar escolha pré-concebida sem comparação técnica e econômica"}),
            verificada_em=datetime.now(timezone.utc).replace(tzinfo=None))
        db.add(precedente_tcees)
        db.flush()
    info_map = {}
    for codigo, nome, objetivo, tipo, obrigatoriedade, estrategia in INFORMACOES:
        item = db.query(InformacaoCatalogo).filter_by(codigo=codigo).first()
        if item is None:
            item = InformacaoCatalogo(codigo=codigo, nome=nome, objetivo=objetivo, tipo=tipo,
                obrigatoriedade=obrigatoriedade, estrategia_preferencial=estrategia,
                dominio_json="[]", ativo=True)
            db.add(item)
            db.flush()
        else:
            item.nome, item.objetivo, item.tipo = nome, objetivo, tipo
            item.obrigatoriedade, item.estrategia_preferencial = obrigatoriedade, estrategia
            item.ativo = True
        info_map[codigo] = item

    for codigo, nome, pergunta, base, criterios, evidencias, artefatos, infos in CARDS:
        card = db.query(CardDecisaoCatalogo).filter_by(codigo=codigo).first()
        if card is None:
            card = CardDecisaoCatalogo(codigo=codigo, versao=1, nome=nome,
                pergunta_controle=pergunta, base_legal_json=json.dumps(base),
                criterios_json=json.dumps(criterios), evidencias_aceitas_json=json.dumps(evidencias),
                artefatos_impactados_json=json.dumps(artefatos), ativo=True)
            db.add(card)
            db.flush()
        else:
            card.nome, card.pergunta_controle = nome, pergunta
            card.base_legal_json, card.criterios_json = json.dumps(base), json.dumps(criterios)
            card.evidencias_aceitas_json = json.dumps(evidencias)
            card.artefatos_impactados_json, card.ativo = json.dumps(artefatos), True
        for indice, descricao in enumerate(criterios, 1):
            codigo_criterio = f"{codigo}-C{indice:02d}"
            if db.query(CriterioCardCatalogo).filter_by(codigo=codigo_criterio).first() is None:
                db.add(CriterioCardCatalogo(card_id=card.id, codigo=codigo_criterio,
                    descricao=descricao, peso=1))
        for ordem, info_codigo in enumerate(infos, 1):
            info = info_map[info_codigo]
            existe = db.query(CardInformacao).filter_by(card_id=card.id, informacao_id=info.id).first()
            if existe is None:
                db.add(CardInformacao(card_id=card.id, informacao_id=info.id, ordem=ordem,
                    obrigatoria=info.obrigatoriedade == "obrigatoria"))
        dispositivo = "; ".join(base)
        if db.query(CardFonteJuridica).filter_by(card_id=card.id,
                fonte_id=fonte_lei.id, dispositivo=dispositivo).first() is None:
            db.add(CardFonteJuridica(card_id=card.id, fonte_id=fonte_lei.id,
                dispositivo=dispositivo))
        if codigo in {"D005", "D006", "D014"} and db.query(CardFonteJuridica).filter_by(
                card_id=card.id, fonte_id=precedente_tcees.id,
                dispositivo="Informativo 136, item 30").first() is None:
            db.add(CardFonteJuridica(card_id=card.id, fonte_id=precedente_tcees.id,
                dispositivo="Informativo 136, item 30"))
        if codigo in {"D004", "D005", "D006"} and db.query(CardFonteJuridica).filter_by(
                card_id=card.id, fonte_id=precedente_tcu.id,
                dispositivo="Acórdão 764/2025-TCU-Plenário").first() is None:
            db.add(CardFonteJuridica(card_id=card.id, fonte_id=precedente_tcu.id,
                dispositivo="Acórdão 764/2025-TCU-Plenário"))
    db.flush()
    cards_map = {c.codigo: c for c in db.query(CardDecisaoCatalogo).filter(
        CardDecisaoCatalogo.codigo.in_(ORDEM_CARDS)).all()}
    for codigo, dependencias in DEPENDENCIAS.items():
        for depende_de in dependencias:
            existe = db.query(CardDependencia).filter_by(
                card_id=cards_map[codigo].id, depende_de_card_id=cards_map[depende_de].id).first()
            if existe is None:
                db.add(CardDependencia(card_id=cards_map[codigo].id,
                    depende_de_card_id=cards_map[depende_de].id))
    db.commit()


def criar_plano_deterministico(db: Session, contratacao: Contratacao) -> PlanoInvestigacao:
    existente = db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao.id, versao=1).first()
    if existente:
        return existente
    garantir_catalogo_piloto(db)
    plano = PlanoInvestigacao(contratacao_id=contratacao.id, versao=1, status="ativo")
    db.add(plano)
    db.flush()
    cards = db.query(CardDecisaoCatalogo).filter(CardDecisaoCatalogo.codigo.in_(ORDEM_CARDS)).all()
    por_codigo = {card.codigo: card for card in cards}
    for ordem, codigo in enumerate(ORDEM_CARDS, 1):
        db.add(PlanoCardDecisao(plano_id=plano.id, card_id=por_codigo[codigo].id,
            ordem=ordem, status="pendente", aplicavel=True, robustez_pct=0))
    db.add(HistoricoContratacao(contratacao_id=contratacao.id, usuario_id=contratacao.usuario_id,
        acao="Plano de Investigação criado", detalhe="Planejador determinístico: catálogo D001–D014"))
    db.commit()
    db.refresh(plano)
    return plano
