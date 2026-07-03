import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Analise, Pesquisa
from app.schemas import AnaliseStatusOut
from app.services.job_runner import iniciar_job_analise

router = APIRouter(tags=["analises"])


@router.post("/pesquisas/{pesquisa_id}/analise", status_code=202)
def criar_analise(pesquisa_id: int, db: Session = Depends(get_db)):
    pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
    if pesquisa is None:
        raise HTTPException(status_code=404, detail="Pesquisa não encontrada")
    if pesquisa.status != "completo":
        raise HTTPException(
            status_code=409, detail=f"Pesquisa ainda não está completa (status={pesquisa.status})"
        )

    analise_em_andamento = (
        db.query(Analise)
        .filter(Analise.pesquisa_id == pesquisa_id, Analise.status.in_(["pendente", "em_andamento"]))
        .first()
    )
    if analise_em_andamento is not None:
        raise HTTPException(status_code=409, detail="Já existe uma análise em andamento para essa pesquisa")

    analise = Analise(pesquisa_id=pesquisa_id, status="pendente")
    db.add(analise)
    db.commit()
    db.refresh(analise)

    iniciar_job_analise(analise.id, pesquisa_id)

    return {"analise_id": analise.id, "status": analise.status}


@router.get("/pesquisas/{pesquisa_id}/analise", response_model=AnaliseStatusOut)
def obter_analise(pesquisa_id: int, db: Session = Depends(get_db)):
    analise = (
        db.query(Analise)
        .filter(Analise.pesquisa_id == pesquisa_id)
        .order_by(Analise.criado_em.desc())
        .first()
    )
    if analise is None:
        raise HTTPException(status_code=404, detail="Nenhuma análise encontrada para essa pesquisa")

    resultado = json.loads(analise.resultado_json) if analise.resultado_json else None
    return AnaliseStatusOut(
        id=analise.id,
        status=analise.status,
        erro_mensagem=analise.erro_mensagem,
        resultado=resultado,
        modelo_gemini=analise.modelo_gemini,
    )
