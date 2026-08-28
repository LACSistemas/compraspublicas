import hashlib
import json

from app.models import ConhecimentoCard, EvidenciaPlano, PlanoCardDecisao, PlanoInformacao
from app.services.pdf_extractor import extrair_texto_pdf


def invalidar_conhecimento_por_informacao(db, plano_informacao_id: int) -> int:
    info = db.query(PlanoInformacao).filter_by(id=plano_informacao_id).first()
    if info is None:
        return 0
    conhecimentos = db.query(ConhecimentoCard).filter(
        ConhecimentoCard.plano_card_id == info.plano_card_id,
        ConhecimentoCard.status.notin_(["superado", "rejeitado"])).all()
    for conhecimento in conhecimentos:
        conhecimento.status = "superado"
    item = db.query(PlanoCardDecisao).filter_by(id=info.plano_card_id).one()
    item.status = "pendente"
    item.robustez_pct = 0
    return len(conhecimentos)


def criar_evidencia(db, plano_informacao_id: int, *, tipo: str, descricao: str,
        conteudo, origem: str, metodo_obtencao: str, confianca: str) -> EvidenciaPlano:
    conteudo_json = json.dumps(conteudo, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(conteudo_json.encode("utf-8")).hexdigest()
    existente = db.query(EvidenciaPlano).filter_by(
        plano_informacao_id=plano_informacao_id, hash_conteudo=digest).first()
    if existente:
        return existente
    anterior = (db.query(EvidenciaPlano).filter_by(plano_informacao_id=plano_informacao_id,
        estado="vigente").order_by(EvidenciaPlano.criado_em.desc()).first())
    evidencia = EvidenciaPlano(plano_informacao_id=plano_informacao_id, tipo=tipo,
        descricao=descricao, conteudo_json=conteudo_json, origem=origem,
        metodo_obtencao=metodo_obtencao, confianca=confianca,
        hash_conteudo=digest, status_validacao="pendente",
        estado="conflitante" if anterior else "vigente")
    db.add(evidencia)
    db.flush()
    info = db.query(PlanoInformacao).filter_by(id=plano_informacao_id).one()
    info.estado_semantico = "contraditorio" if anterior else (
        "inferido" if metodo_obtencao == "inferencia" else "informado")
    invalidar_conhecimento_por_informacao(db, plano_informacao_id)
    return evidencia


def substituir_evidencia(db, nova: EvidenciaPlano, anterior: EvidenciaPlano) -> None:
    if nova.plano_informacao_id != anterior.plano_informacao_id:
        raise ValueError("Evidências pertencem a informações diferentes")
    anterior.estado = "substituida"
    nova.estado = "vigente"
    nova.substitui_evidencia_id = anterior.id
    info = db.query(PlanoInformacao).filter_by(id=nova.plano_informacao_id).one()
    info.estado_semantico = "confirmado" if nova.status_validacao == "confirmada" else "informado"
    invalidar_conhecimento_por_informacao(db, nova.plano_informacao_id)


def extrair_e_registrar_pdf(db, plano_informacao_id: int, caminho: str, nome_original: str):
    resultado = extrair_texto_pdf(caminho)
    status = resultado.get("status", "erro")
    texto = resultado.get("texto", "")
    confianca = "media" if status in {"ok", "ok_ocr"} else "baixa"
    return criar_evidencia(db, plano_informacao_id, tipo="texto_documental",
        descricao=f"Texto extraído de {nome_original}",
        conteudo={"texto": texto, "status_extracao": status,
            "metodo_extracao": resultado.get("metodo"), "erro": resultado.get("erro")},
        origem="documento_upload", metodo_obtencao=resultado.get("metodo") or "extracao_falhou",
        confianca=confianca)
