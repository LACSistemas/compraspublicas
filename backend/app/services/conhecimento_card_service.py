import hashlib
import json
from datetime import datetime, timezone

from app.models import (BaseConhecimento, CardDecisaoCatalogo, CardInformacao,
    CardFonteJuridica, ConhecimentoCard, CriterioCardCatalogo, EvidenciaCriterio,
    EvidenciaPlano, FonteJuridica, PlanoCardDecisao, PlanoInformacao,
    PlanoInvestigacao, SnapshotBCC)
from app.services.pesquisa_precos_service import obter_pacote_disponivel


def gerar_conhecimentos(db, plano: PlanoInvestigacao) -> list[ConhecimentoCard]:
    gerados = []
    itens = db.query(PlanoCardDecisao).filter_by(plano_id=plano.id).order_by(PlanoCardDecisao.ordem).all()
    for item in itens:
        if not item.aplicavel:
            continue
        ultimo = (db.query(ConhecimentoCard).filter_by(plano_card_id=item.id)
            .order_by(ConhecimentoCard.versao.desc()).first())
        if ultimo is not None and ultimo.status != "superado":
            continue
        card = db.query(CardDecisaoCatalogo).filter_by(id=item.card_id).one()
        vinculos = db.query(CardInformacao).filter_by(card_id=card.id).all()
        obrigatorias = [v for v in vinculos if v.obrigatoria]
        todas_evidencias = (db.query(EvidenciaPlano).join(PlanoInformacao)
            .filter(PlanoInformacao.plano_card_id == item.id).all())
        evidencias = [e for e in todas_evidencias if e.estado == "vigente"]
        infos_cobertas = {e.plano_informacao_id for e in evidencias}
        exec_obrigatorias = (db.query(PlanoInformacao).filter(
            PlanoInformacao.plano_card_id == item.id,
            PlanoInformacao.informacao_id.in_([v.informacao_id for v in obrigatorias])).all()) if obrigatorias else []
        cobertura = sum(1 for e in exec_obrigatorias if e.id in infos_cobertas)
        cobertura_info_pct = round(100 * cobertura / max(1, len(exec_obrigatorias)))
        criterios = db.query(CriterioCardCatalogo).filter_by(card_id=card.id).all()
        evidencias_confirmadas = [e for e in evidencias if e.status_validacao == "confirmada"]
        vinculos_criterios = (db.query(EvidenciaCriterio).filter(
            EvidenciaCriterio.evidencia_id.in_([e.id for e in evidencias_confirmadas])).all()
            if evidencias_confirmadas else [])
        criterio_ids_cobertos = {v.criterio_id for v in vinculos_criterios}
        peso_total = sum(c.peso for c in criterios) or 1
        peso_coberto = sum(c.peso for c in criterios if c.id in criterio_ids_cobertos)
        cobertura_criterio_pct = round(100 * peso_coberto / peso_total)
        confiancas = {"alta": 100, "media": 70, "baixa": 35}
        confianca_pct = round(sum(confiancas.get(e.confianca, 0) for e in evidencias) /
            max(1, len(evidencias)))
        agora = datetime.now(timezone.utc).replace(tzinfo=None)
        atualidades = []
        for evidencia in evidencias:
            dias = (agora - evidencia.criado_em).days if evidencia.criado_em else 0
            atualidades.append(100 if dias <= 365 else 50 if dias <= 730 else 0)
        atualidade_pct = round(sum(atualidades) / max(1, len(atualidades)))
        conflitantes = sum(e.estado == "conflitante" for e in todas_evidencias)
        rejeitadas = sum(e.status_validacao == "rejeitada" for e in todas_evidencias)
        consistencia_pct = 0 if conflitantes else 50 if rejeitadas else 100
        dimensoes = {"completude": cobertura_info_pct, "cobertura_criterios": cobertura_criterio_pct,
            "confianca": confianca_pct, "atualidade": atualidade_pct,
            "consistencia": consistencia_pct}
        robustez = round(cobertura_info_pct * 0.30 + cobertura_criterio_pct * 0.25 +
            confianca_pct * 0.20 + atualidade_pct * 0.10 + consistencia_pct * 0.15)
        cobertura_criterios = [{"codigo": c.codigo, "descricao": c.descricao,
            "atendido": c.id in criterio_ids_cobertos} for c in criterios]
        fontes = (db.query(FonteJuridica, CardFonteJuridica)
            .join(CardFonteJuridica, CardFonteJuridica.fonte_id == FonteJuridica.id)
            .filter(CardFonteJuridica.card_id == card.id, FonteJuridica.confirmada.is_(True)).all())
        fontes_confirmadas = [{"codigo": fonte.codigo, "titulo": fonte.titulo,
            "referencia": fonte.referencia, "dispositivo": vinculo.dispositivo,
            "url_oficial": fonte.url_oficial, "orgao_emissor": fonte.orgao_emissor}
            for fonte, vinculo in fontes]
        ausentes = len(exec_obrigatorias) - cobertura
        status = "aguardando_revisao" if ausentes == 0 and cobertura_criterio_pct == 100 else "aguardando_evidencia"
        versao = (db.query(ConhecimentoCard).filter_by(plano_card_id=item.id).count() + 1)
        conhecimento = ConhecimentoCard(plano_card_id=item.id, versao=versao,
            conclusao=("Fundamentação disponível para revisão" if ausentes == 0 else
                f"Fundamentação parcial; {ausentes} informação(ões) obrigatória(s) sem evidência vigente"),
            motivacao=f"Avaliação determinística dos critérios do Card {card.codigo}: {card.pergunta_controle}",
            fundamentacao_json=card.base_legal_json, riscos_json=json.dumps(
                [] if ausentes == 0 else [{"descricao": "Decisão com evidências obrigatórias incompletas",
                    "nivel": "alto"}], ensure_ascii=False),
            recomendacoes_json=json.dumps([] if ausentes == 0 else [
                {"descricao": "Coletar e validar as informações obrigatórias pendentes"}], ensure_ascii=False),
            evidencias_json=json.dumps([e.id for e in evidencias]),
            cobertura_criterios_json=json.dumps(cobertura_criterios, ensure_ascii=False),
            dimensoes_robustez_json=json.dumps(dimensoes, ensure_ascii=False),
            fontes_confirmadas_json=json.dumps(fontes_confirmadas, ensure_ascii=False),
            robustez_pct=robustez, status=status)
        item.robustez_pct = robustez
        item.status = status
        db.add(conhecimento)
        gerados.append(conhecimento)
    db.flush()
    return gerados


def consolidar_bcc(db, contratacao_id: int, conhecimentos: list[ConhecimentoCard]):
    decisoes, evidencias, riscos, recomendacoes, lacunas = [], [], [], [], []
    ids_evidencias = set()
    for conhecimento in conhecimentos:
        item = db.query(PlanoCardDecisao).filter_by(id=conhecimento.plano_card_id).one()
        card = db.query(CardDecisaoCatalogo).filter_by(id=item.card_id).one()
        ids = json.loads(conhecimento.evidencias_json)
        ids_evidencias.update(ids)
        decisoes.append({"id": f"card-{card.codigo}", "pergunta_decisoria": card.pergunta_controle,
            "conclusao": conhecimento.conclusao, "motivacao_administrativa": conhecimento.motivacao,
            "base_legal": "; ".join(json.loads(conhecimento.fundamentacao_json)),
            "evidencias_utilizadas": [f"ev-{i}" for i in ids],
            "nivel_robustez_pct": conhecimento.robustez_pct,
            "nivel_robustez_label": "Alta" if conhecimento.robustez_pct >= 75 else "Parcial",
            "documentos_impactados": json.loads(card.artefatos_impactados_json), "status": conhecimento.status})
        riscos.extend(json.loads(conhecimento.riscos_json))
        recomendacoes.extend(json.loads(conhecimento.recomendacoes_json))
        if conhecimento.status == "aguardando_evidencia":
            lacunas.append({"id": f"lac-{card.codigo}", "descricao": conhecimento.conclusao,
                "criticidade": "alta", "decisao_bloqueada": card.codigo})
    for evidencia in db.query(EvidenciaPlano).filter(EvidenciaPlano.id.in_(ids_evidencias)).all() if ids_evidencias else []:
        evidencias.append({"id": f"ev-{evidencia.id}", "descricao": evidencia.descricao,
            "origem": evidencia.origem, "confiabilidade": evidencia.confianca,
            "status_validacao": evidencia.status_validacao, "fonte": evidencia.metodo_obtencao})
    progresso = round(sum(c.robustez_pct for c in conhecimentos) / max(1, len(conhecimentos)))
    dados = {"metricas": {"progresso_pct": progresso,
        "nivel_maturidade": "Maduro" if progresso >= 75 else "Parcial" if progresso >= 40 else "Insuficiente",
        "evidencias_coletadas": len(evidencias), "evidencias_total": len(evidencias),
        "decisoes_fundamentadas": sum(c.status == "aprovado" for c in conhecimentos),
        "decisoes_total": len(conhecimentos), "pendencias_criticas": len(lacunas)},
        "resumo_executivo": {"necessidade": "Consolidação dos Cards do Plano de Investigação",
            "solucao_escolhida": "Aguardando consolidação de todos os Cards", "riscos_principais": []},
        "evidencias": evidencias, "decisoes": decisoes, "lacunas": lacunas, "riscos": riscos,
        "recomendacoes": recomendacoes, "documentos_status": {}, "fundamentacoes": [], "historico": []}
    pesquisa_precos = obter_pacote_disponivel(db, contratacao_id)
    if pesquisa_precos:
        dados["pesquisa_precos"] = pesquisa_precos
    serializado = json.dumps(dados, ensure_ascii=False, sort_keys=True)
    versao = db.query(SnapshotBCC).filter_by(contratacao_id=contratacao_id).count() + 1
    snapshot = SnapshotBCC(contratacao_id=contratacao_id, versao=versao, dados_json=serializado,
        hash_conteudo=hashlib.sha256(serializado.encode()).hexdigest())
    db.add(snapshot)
    bcc = db.query(BaseConhecimento).filter_by(contratacao_id=contratacao_id).first()
    if bcc is None:
        bcc = BaseConhecimento(contratacao_id=contratacao_id, dados_json=serializado)
        db.add(bcc)
    bcc.dados_json, bcc.progresso_pct = serializado, progresso
    bcc.nivel_maturidade = dados["metricas"]["nivel_maturidade"]
    db.flush()
    return bcc, snapshot
