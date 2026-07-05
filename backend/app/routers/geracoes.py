import json
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Geracao, Pesquisa
from app.schemas import GeracaoCreate, GeracaoDetailOut, GeracaoStatusOut
from app.services.job_runner import iniciar_job_geracao

router = APIRouter(tags=["geracoes"])


@router.post("/pesquisas/{pesquisa_id}/etp", status_code=202)
def criar_geracao(
    pesquisa_id: int,
    payload: GeracaoCreate,
    db: Session = Depends(get_db),
):
    pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
    if pesquisa is None:
        raise HTTPException(status_code=404, detail="Pesquisa não encontrada")
    if pesquisa.status != "completo":
        raise HTTPException(
            status_code=409,
            detail=f"Pesquisa ainda não está completa (status={pesquisa.status})",
        )

    em_andamento = (
        db.query(Geracao)
        .filter(
            Geracao.pesquisa_id == pesquisa_id,
            Geracao.tipo == payload.tipo,
            Geracao.status.in_(["pendente", "em_andamento"]),
        )
        .first()
    )
    if em_andamento is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Já existe uma geração de {payload.tipo.upper()} em andamento para essa pesquisa",
        )

    geracao = Geracao(pesquisa_id=pesquisa_id, tipo=payload.tipo, status="pendente")
    db.add(geracao)
    db.commit()
    db.refresh(geracao)

    params = {
        "tipo": payload.tipo,
        "un_gestora": payload.un_gestora,
        "responsaveis": payload.responsaveis,
        "objeto_resumido": payload.objeto_resumido,
    }
    iniciar_job_geracao(geracao.id, pesquisa_id, params)

    return {"geracao_id": geracao.id, "status": geracao.status}


@router.get("/pesquisas/{pesquisa_id}/etp", response_model=GeracaoDetailOut)
def obter_geracao(
    pesquisa_id: int,
    tipo: str = "etp",
    db: Session = Depends(get_db),
):
    geracao = (
        db.query(Geracao)
        .filter(Geracao.pesquisa_id == pesquisa_id, Geracao.tipo == tipo)
        .order_by(Geracao.criado_em.desc())
        .first()
    )
    if geracao is None:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma geração de {tipo.upper()} encontrada para essa pesquisa",
        )

    resultado = json.loads(geracao.resultado_json) if geracao.resultado_json else None
    pendencias = resultado.get("pendencias") if resultado else None
    arquivo_disponivel = bool(
        geracao.arquivo_gerado and os.path.isfile(geracao.arquivo_gerado)
    )

    return GeracaoDetailOut(
        id=geracao.id,
        tipo=geracao.tipo,
        status=geracao.status,
        erro_mensagem=geracao.erro_mensagem,
        pendencias=pendencias,
        arquivo_disponivel=arquivo_disponivel,
        resultado=resultado,
        modelo_gemini=geracao.modelo_gemini,
        criado_em=geracao.criado_em,
        atualizado_em=geracao.atualizado_em,
    )


@router.get("/pesquisas/{pesquisa_id}/etp/download")
def download_geracao(
    pesquisa_id: int,
    tipo: str = "etp",
    db: Session = Depends(get_db),
):
    geracao = (
        db.query(Geracao)
        .filter(Geracao.pesquisa_id == pesquisa_id, Geracao.tipo == tipo)
        .order_by(Geracao.criado_em.desc())
        .first()
    )
    if geracao is None or not geracao.arquivo_gerado:
        raise HTTPException(status_code=404, detail="Documento não disponível")
    if not os.path.isfile(geracao.arquivo_gerado):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no disco")

    nome_arquivo = os.path.basename(geracao.arquivo_gerado)
    return FileResponse(
        path=geracao.arquivo_gerado,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=nome_arquivo,
    )
