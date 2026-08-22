import json
import logging
import os
import threading
from datetime import datetime

from app.database import SessionLocal
from app.models import Contratacao, HistoricoContratacao, PerguntaContratacao
from app.services.gemini_service import chamar_gemini, salvar_uso_tokens

logger = logging.getLogger("investigacao_service")

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "prompt_perguntas.md")


def _job_gerar_perguntas(contratacao_id: int):
    db = SessionLocal()
    try:
        contratacao = db.query(Contratacao).filter(Contratacao.id == contratacao_id).first()
        if not contratacao:
            return

        with open(_PROMPT_PATH, encoding="utf-8") as f:
            template = f.read()

        prompt = template.format(
            objeto=contratacao.objeto,
            orgao=contratacao.orgao_unidade,
            tipo=contratacao.tipo_contratacao or "não especificado",
            contexto=contratacao.contexto_inicial or "não informado",
        )

        dados, token_info = chamar_gemini(prompt)
        perguntas_raw = dados.get("perguntas", [])

        for p in perguntas_raw:
            db.add(PerguntaContratacao(
                contratacao_id=contratacao_id,
                ordem=p["ordem"],
                texto=p["texto"],
                alternativas_json=json.dumps(p["alternativas"], ensure_ascii=False),
            ))

        salvar_uso_tokens(db, contratacao.usuario_id, "perguntas_contratacao", token_info, contratacao_id)

        db.add(HistoricoContratacao(
            contratacao_id=contratacao_id,
            usuario_id=contratacao.usuario_id,
            acao=f"IA gerou {len(perguntas_raw)} perguntas de investigação",
            detalhe=f"Modelo: {token_info.modelo} | Tokens: {token_info.total}",
        ))

        contratacao.status = "investigacao"
        db.commit()
        logger.info("Perguntas geradas com sucesso para contratacao_id=%s", contratacao_id)

    except Exception as exc:
        logger.exception("Erro ao gerar perguntas para contratacao_id=%s", contratacao_id)
        db.rollback()
        try:
            c = db.query(Contratacao).filter(Contratacao.id == contratacao_id).first()
            if c:
                c.status = "erro"
                c.erro_mensagem = str(exc)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def iniciar_geracao_perguntas(contratacao_id: int):
    threading.Thread(
        target=_job_gerar_perguntas, args=(contratacao_id,), daemon=True
    ).start()
