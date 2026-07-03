import json
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Pesquisa
from app.schemas import (
    PesquisaCreate,
    PesquisaDetailOut,
    PesquisaListItemOut,
    PesquisaStatusOut,
)
from app.services.job_runner import iniciar_job_scraping

router = APIRouter(tags=["pesquisas"])


def _buscar_pesquisa_ou_404(pesquisa_id: int, db: Session) -> Pesquisa:
    pesquisa = db.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).first()
    if pesquisa is None:
        raise HTTPException(status_code=404, detail="Pesquisa não encontrada")
    return pesquisa


@router.post("/pesquisas", status_code=201, response_model=PesquisaStatusOut)
def criar_pesquisa(payload: PesquisaCreate, db: Session = Depends(get_db)):
    pesquisa = Pesquisa(
        termo_busca=payload.termo_busca,
        quantidade_desejada=payload.quantidade_desejada,
        limite_processos=settings.MAX_PROCESSOS,
        status="pendente",
    )
    db.add(pesquisa)
    db.commit()
    db.refresh(pesquisa)

    iniciar_job_scraping(pesquisa.id, payload.termo_busca, settings.MAX_PROCESSOS)

    return pesquisa


@router.get("/pesquisas", response_model=list[PesquisaListItemOut])
def listar_pesquisas(db: Session = Depends(get_db)):
    return db.query(Pesquisa).order_by(Pesquisa.criado_em.desc()).all()


@router.get("/pesquisas/{pesquisa_id}", response_model=PesquisaDetailOut)
def obter_pesquisa(pesquisa_id: int, db: Session = Depends(get_db)):
    pesquisa = _buscar_pesquisa_ou_404(pesquisa_id, db)
    resultado = json.loads(pesquisa.resultado_json) if pesquisa.resultado_json else None
    return PesquisaDetailOut(
        id=pesquisa.id,
        termo_busca=pesquisa.termo_busca,
        quantidade_desejada=pesquisa.quantidade_desejada,
        limite_processos=pesquisa.limite_processos,
        status=pesquisa.status,
        erro_mensagem=pesquisa.erro_mensagem,
        resultado=resultado,
        pasta_downloads=pesquisa.pasta_downloads,
        criado_em=pesquisa.criado_em,
        atualizado_em=pesquisa.atualizado_em,
    )


@router.get("/pesquisas/{pesquisa_id}/status", response_model=PesquisaStatusOut)
def obter_status_pesquisa(pesquisa_id: int, db: Session = Depends(get_db)):
    return _buscar_pesquisa_ou_404(pesquisa_id, db)


@router.get("/pesquisas/{pesquisa_id}/documentos/{nome_arquivo:path}")
def obter_documento(pesquisa_id: int, nome_arquivo: str, db: Session = Depends(get_db)):
    pesquisa = _buscar_pesquisa_ou_404(pesquisa_id, db)
    if not pesquisa.pasta_downloads:
        raise HTTPException(status_code=404, detail="Pesquisa sem documentos")

    pasta_base = os.path.realpath(pesquisa.pasta_downloads)
    caminho = os.path.realpath(os.path.join(pesquisa.pasta_downloads, nome_arquivo))

    # Proteção contra path traversal (ex: nome_arquivo="../../app/config.py")
    if caminho != pasta_base and not caminho.startswith(pasta_base + os.sep):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not os.path.isfile(caminho):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(caminho)
