from sqlalchemy import func

from app.config import settings
from app.models import ExecucaoIA, Geracao, Pesquisa, UsoTokens


def consumo_tokens_contratacao(db, contratacao_id: int) -> dict:
    planejamento = (db.query(func.coalesce(func.sum(ExecucaoIA.tokens_total), 0))
        .filter(ExecucaoIA.contratacao_id == contratacao_id).scalar() or 0)
    legado = (db.query(func.coalesce(func.sum(UsoTokens.tokens_total), 0))
        .filter(UsoTokens.referencia_id == contratacao_id,
            UsoTokens.tipo.in_(["perguntas_contratacao", "bcc_contratacao"])).scalar() or 0)
    documentos = (db.query(func.coalesce(func.sum(UsoTokens.tokens_total), 0))
        .join(Geracao, UsoTokens.referencia_id == Geracao.id)
        .join(Pesquisa, Geracao.pesquisa_id == Pesquisa.id)
        .filter(Pesquisa.contratacao_id == contratacao_id,
            UsoTokens.tipo.in_(["dfd", "etp", "mapa_riscos", "tr"])).scalar() or 0)
    por_fase = {"planejamento": int(planejamento), "legado": int(legado),
        "redacao_documental": int(documentos), "inferencia": 0,
        "conhecimento_cards": 0, "consolidacao": 0}
    total = sum(por_fase.values())
    limite = settings.TOKEN_BUDGET_CONTRATACAO
    return {"contratacao_id": contratacao_id, "por_fase": por_fase, "total": total,
        "limite": limite, "disponivel": max(0, limite - total), "excedido": total >= limite}


def exigir_orcamento_disponivel(db, contratacao_id: int) -> dict:
    consumo = consumo_tokens_contratacao(db, contratacao_id)
    if consumo["excedido"]:
        raise ValueError(f"Orçamento de tokens da contratação esgotado ({consumo['total']}/{consumo['limite']})")
    return consumo
