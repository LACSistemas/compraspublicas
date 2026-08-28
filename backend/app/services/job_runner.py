import threading

from app.database import SessionLocal
from app.models import Geracao, Pesquisa
from app.services.job_checkpoint_service import criar_job, executar_com_retry_idempotente
from app.services.analise_service import executar_analise
from app.services.gerador_etp_service import executar_geracao
from app.services.scraper_service import executar_e_persistir


def iniciar_job_scraping(pesquisa_id: int, termo: str, limite: int, usuario_id: int):
    thread = threading.Thread(
        target=executar_e_persistir, args=(pesquisa_id, termo, limite), daemon=True
    )
    thread.start()


def iniciar_job_analise(analise_id: int, pesquisa_id: int, usuario_id: int):
    thread = threading.Thread(
        target=executar_analise, args=(analise_id, pesquisa_id, usuario_id), daemon=True
    )
    thread.start()


def iniciar_job_geracao(geracao_id: int, pesquisa_id: int, params: dict, usuario_id: int):
    db = SessionLocal()
    try:
        pesquisa = db.query(Pesquisa).filter_by(id=pesquisa_id).first()
        job = criar_job(db, "redacao_documental", pesquisa.contratacao_id if pesquisa else None,
            referencia_id=geracao_id)
        job_id = job.id
    finally:
        db.close()

    def executar():
        def estado():
            sessao = SessionLocal()
            try:
                g = sessao.query(Geracao).filter_by(id=geracao_id).first()
                return {"geracao_id": geracao_id, "status": g.status if g else None,
                    "arquivo": g.arquivo_gerado if g else None}
            finally:
                sessao.close()
        executar_com_retry_idempotente(SessionLocal, job_id,
            lambda: executar_geracao(geracao_id, pesquisa_id, params, usuario_id),
            lambda: estado()["status"] == "completo",
            etapa_execucao="redacao_ia", etapa_sucesso="documento_salvo", checkpoint=estado)

    thread = threading.Thread(
        target=executar, daemon=True
    )
    thread.start()
