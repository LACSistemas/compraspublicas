import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_active_user
from app.database import get_db
from app.models import (CampanhaPesquisaPrecos, ConsultaPesquisaPrecos, Contratacao,
    ObservacaoPreco, Usuario)
from app.schemas import ExpandirPesquisaPrecosIn, RevisarObservacaoPrecoIn
from app.services.pesquisa_precos_service import (aprovar_campanha, criar_campanha,
    expandir_campanha, iniciar_campanha, _calcular_resultado)

router = APIRouter(tags=["pesquisa-precos"])


def _contratacao(db, contratacao_id: int, usuario_id: int) -> Contratacao:
    row = db.query(Contratacao).filter_by(id=contratacao_id, usuario_id=usuario_id).first()
    if row is None: raise HTTPException(status_code=404, detail="Contratação não encontrada")
    return row


def _campanha(db, contratacao_id: int, usuario_id: int) -> CampanhaPesquisaPrecos:
    _contratacao(db, contratacao_id, usuario_id)
    row = db.query(CampanhaPesquisaPrecos).filter_by(contratacao_id=contratacao_id).order_by(
        CampanhaPesquisaPrecos.id.desc()).first()
    if row is None: raise HTTPException(status_code=404, detail="Pesquisa de preços não iniciada")
    return row


def _saida(db, campanha: CampanhaPesquisaPrecos) -> dict:
    consultas = db.query(ConsultaPesquisaPrecos).filter_by(campanha_id=campanha.id).order_by(
        ConsultaPesquisaPrecos.ordem).all()
    observacoes = db.query(ObservacaoPreco).filter_by(campanha_id=campanha.id).order_by(
        ObservacaoPreco.aderencia_pct.desc(), ObservacaoPreco.id).all()
    return {"id": campanha.id, "contratacao_id": campanha.contratacao_id,
        "status": campanha.status, "objeto_canonico": json.loads(campanha.objeto_canonico_json),
        "max_consultas": campanha.max_consultas, "resultado": json.loads(campanha.resultado_json),
        "erro_mensagem": campanha.erro_mensagem, "aprovado_em": campanha.aprovado_em,
        "consultas": [{"id": c.id, "ordem": c.ordem, "termo": c.termo, "status": c.status,
            "processos_encontrados": c.processos_encontrados, "processos_novos": c.processos_novos}
            for c in consultas],
        "observacoes": [{"id": o.id, "processo_url": o.processo_url,
            "numero_processo": o.numero_processo, "comprador": o.comprador,
            "descricao_item": o.descricao_item, "quantidade": o.quantidade, "unidade": o.unidade,
            "valor_unitario": o.valor_unitario, "tipo_valor": o.tipo_valor,
            "aderencia_pct": o.aderencia_pct, "comparavel": o.comparavel,
            "motivo_exclusao": o.motivo_exclusao, "documento_origem": o.documento_origem,
            "status_validacao": o.status_validacao} for o in observacoes]}


@router.post("/contratacoes/{contratacao_id}/pesquisa-precos", status_code=202)
def iniciar_pesquisa(contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user)):
    contratacao = _contratacao(db, contratacao_id, current_user.id)
    ativa = db.query(CampanhaPesquisaPrecos).filter(
        CampanhaPesquisaPrecos.contratacao_id == contratacao_id,
        CampanhaPesquisaPrecos.status.in_(["planejada", "executando"])).first()
    if ativa: raise HTTPException(status_code=409, detail="Já existe uma pesquisa de preços em andamento")
    campanha = criar_campanha(db, contratacao)
    iniciar_campanha(campanha.id)
    return {"campanha_id": campanha.id, "status": "executando"}


@router.get("/contratacoes/{contratacao_id}/pesquisa-precos")
def obter_pesquisa(contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user)):
    return _saida(db, _campanha(db, contratacao_id, current_user.id))


@router.post("/contratacoes/{contratacao_id}/pesquisa-precos/expandir", status_code=202)
def expandir(contratacao_id: int, payload: ExpandirPesquisaPrecosIn,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_active_user)):
    campanha = _campanha(db, contratacao_id, current_user.id)
    if campanha.status not in ("pronta_revisao", "erro"):
        raise HTTPException(status_code=409, detail="Aguarde a rodada atual terminar")
    adicionadas = expandir_campanha(db, campanha, payload.quantidade)
    if not adicionadas: raise HTTPException(status_code=409, detail="Limite de consultas atingido")
    iniciar_campanha(campanha.id)
    return {"campanha_id": campanha.id, "consultas_adicionadas": adicionadas}


@router.patch("/contratacoes/{contratacao_id}/pesquisa-precos/observacoes/{observacao_id}")
def revisar_observacao(contratacao_id: int, observacao_id: int,
    payload: RevisarObservacaoPrecoIn, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user)):
    campanha = _campanha(db, contratacao_id, current_user.id)
    observacao = db.query(ObservacaoPreco).filter_by(id=observacao_id,
        campanha_id=campanha.id).first()
    if observacao is None: raise HTTPException(status_code=404, detail="Observação não encontrada")
    observacao.comparavel, observacao.motivo_exclusao = payload.comparavel, payload.motivo_exclusao
    observacao.status_validacao = payload.status_validacao
    consultas = db.query(ConsultaPesquisaPrecos).filter_by(campanha_id=campanha.id).all()
    observacoes = db.query(ObservacaoPreco).filter_by(campanha_id=campanha.id).all()
    campanha.resultado_json = json.dumps(_calcular_resultado(observacoes, consultas), ensure_ascii=False)
    db.commit()
    return _saida(db, campanha)


@router.post("/contratacoes/{contratacao_id}/pesquisa-precos/aprovar")
def aprovar(contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user)):
    campanha = _campanha(db, contratacao_id, current_user.id)
    if campanha.status != "pronta_revisao":
        raise HTTPException(status_code=409, detail="A pesquisa ainda não está pronta para aprovação")
    try: aprovar_campanha(db, campanha, current_user.id)
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _saida(db, campanha)
