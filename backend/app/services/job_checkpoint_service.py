import json

from app.models import JobExecucao


def criar_job(db, tipo: str, contratacao_id: int | None, referencia_id: int | None = None,
    max_tentativas: int = 2) -> JobExecucao:
    job = JobExecucao(tipo=tipo, contratacao_id=contratacao_id, referencia_id=referencia_id,
        status="pendente", etapa="criado", tentativa=0, max_tentativas=max_tentativas,
        checkpoint_json="{}")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def atualizar_job(db, job_id: int, *, status: str | None = None, etapa: str | None = None,
    checkpoint: dict | None = None, erro: str | None = None, incrementar_tentativa: bool = False):
    job = db.query(JobExecucao).filter_by(id=job_id).one()
    if status is not None:
        job.status = status
    if etapa is not None:
        job.etapa = etapa
    if checkpoint is not None:
        job.checkpoint_json = json.dumps(checkpoint, ensure_ascii=False, sort_keys=True)
    if incrementar_tentativa:
        job.tentativa += 1
    job.erro_mensagem = erro
    db.commit()
    return job


def executar_com_retry_idempotente(session_factory, job_id: int, operacao, concluido,
    *, etapa_execucao: str, etapa_sucesso: str, checkpoint) -> bool:
    """Repete o mesmo job/ref; `concluido` impede duplicar trabalho já confirmado."""
    while True:
        db = session_factory()
        try:
            job = db.query(JobExecucao).filter_by(id=job_id).one()
            if concluido():
                atualizar_job(db, job_id, status="completo", etapa=etapa_sucesso,
                    checkpoint=checkpoint(), erro=None)
                return True
            if job.tentativa >= job.max_tentativas:
                atualizar_job(db, job_id, status="erro", etapa="tentativas_esgotadas",
                    checkpoint=checkpoint(), erro=job.erro_mensagem or "Tentativas esgotadas")
                return False
            atualizar_job(db, job_id, status="em_andamento", etapa=etapa_execucao,
                incrementar_tentativa=True, erro=None)
        finally:
            db.close()
        try:
            operacao()
        except Exception as exc:
            db = session_factory()
            try:
                atualizar_job(db, job_id, status="aguardando_retry", etapa="falha_transitoria",
                    checkpoint=checkpoint(), erro=str(exc))
            finally:
                db.close()
            continue
        if concluido():
            db = session_factory()
            try:
                atualizar_job(db, job_id, status="completo", etapa=etapa_sucesso,
                    checkpoint=checkpoint(), erro=None)
            finally:
                db.close()
            return True
        db = session_factory()
        try:
            atualizar_job(db, job_id, status="aguardando_retry", etapa="resultado_incompleto",
                checkpoint=checkpoint(), erro="Operação terminou sem atingir o estado esperado")
        finally:
            db.close()
