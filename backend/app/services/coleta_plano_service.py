import json
import logging
import threading

from sqlalchemy import case

from app.config import settings
from app.database import SessionLocal
from app.models import (Contratacao, HistoricoContratacao, Pesquisa,
    PlanoCardDecisao, PlanoInformacao, PlanoInvestigacao)
from app.services.scraper_service import executar_e_persistir
from app.services.evidencia_plano_service import criar_evidencia
from app.services.job_checkpoint_service import criar_job, executar_com_retry_idempotente

logger = logging.getLogger("coleta_plano_service")

PRIORIDADE_ESTRATEGIAS = {
    "consulta": 1, "integracao": 2, "inferencia": 3, "pergunta": 4, "upload": 5,
}
STATUS_RESOLVIDOS = {
    "coletada", "coletada_inferida", "coletada_resposta", "coletada_upload",
    "coletada_upload_extraida", "dispensada",
}


def listar_lacunas(db, plano_id: int) -> dict:
    from app.models import CardDecisaoCatalogo, CardInformacao, InformacaoCatalogo

    linhas = (db.query(PlanoInformacao, PlanoCardDecisao, CardDecisaoCatalogo,
            InformacaoCatalogo, CardInformacao)
        .join(PlanoCardDecisao, PlanoInformacao.plano_card_id == PlanoCardDecisao.id)
        .join(CardDecisaoCatalogo, PlanoCardDecisao.card_id == CardDecisaoCatalogo.id)
        .join(InformacaoCatalogo, PlanoInformacao.informacao_id == InformacaoCatalogo.id)
        .join(CardInformacao, (CardInformacao.card_id == PlanoCardDecisao.card_id) &
            (CardInformacao.informacao_id == PlanoInformacao.informacao_id))
        .filter(PlanoCardDecisao.plano_id == plano_id, PlanoCardDecisao.aplicavel.is_(True))
        .all())
    lacunas = []
    for execucao, item, card, info, vinculo in linhas:
        if execucao.status in STATUS_RESOLVIDOS:
            continue
        lacunas.append({"plano_informacao_id": execucao.id, "plano_card_id": item.id,
            "codigo_card": card.codigo, "codigo_informacao": info.codigo,
            "nome_informacao": info.nome, "estrategia": execucao.estrategia,
            "prioridade": PRIORIDADE_ESTRATEGIAS[execucao.estrategia],
            "status": execucao.status, "obrigatoria": vinculo.obrigatoria,
            "bloqueia_conhecimento": vinculo.obrigatoria})
    lacunas.sort(key=lambda x: (not x["obrigatoria"], x["prioridade"], x["codigo_card"],
        x["codigo_informacao"]))
    bloqueantes = sum(l["bloqueia_conhecimento"] for l in lacunas)
    return {"plano_id": plano_id, "total": len(lacunas), "bloqueantes": bloqueantes,
        "opcionais": len(lacunas) - bloqueantes, "pronto_para_conhecimento": bloqueantes == 0,
        "proxima_estrategia": lacunas[0]["estrategia"] if lacunas else None,
        "lacunas": lacunas}


def _resumo_consulta(resultado: dict) -> dict:
    processos = resultado.get("processos", [])
    compradores = sorted({p.get("comprador") for p in processos if p.get("comprador")})
    return {"total_processos_similares": len(processos), "compradores_encontrados": compradores[:20],
        "fontes": [p.get("url") for p in processos if p.get("url")][:20]}


def _resumo_integracao(resultado: dict) -> dict:
    itens = []
    for processo in resultado.get("processos", []):
        for item in processo.get("itens", []) or []:
            itens.append({"descricao": item.get("descricao"), "quantidade": item.get("quantidade"),
                "unidade": item.get("unidade"), "processo": processo.get("numero_processo")})
    return {"total_itens_referencia": len(itens), "amostra_itens": itens[:50]}


def consolidar_resultado_coleta(db, plano_id: int, resultado: dict) -> int:
    atualizadas = 0
    execucoes = (db.query(PlanoInformacao).join(PlanoCardDecisao)
        .filter(PlanoCardDecisao.plano_id == plano_id,
            PlanoInformacao.estrategia.in_(["consulta", "integracao"]),
            PlanoInformacao.status == "pendente_coleta")
        .order_by(case(PRIORIDADE_ESTRATEGIAS, value=PlanoInformacao.estrategia, else_=99),
            PlanoInformacao.id).all())
    for execucao in execucoes:
        valor = _resumo_consulta(resultado) if execucao.estrategia == "consulta" else _resumo_integracao(resultado)
        tem_dados = valor.get("total_processos_similares", valor.get("total_itens_referencia", 0)) > 0
        execucao.valor_json = json.dumps(valor, ensure_ascii=False)
        execucao.status = "coletada" if tem_dados else "coleta_indisponivel"
        execucao.origem = "portal_compras_http"
        execucao.confianca = "media" if tem_dados else "baixa"
        execucao.estado_semantico = "informado" if tem_dados else "nao_informado"
        criar_evidencia(db, execucao.id, tipo="consulta_externa",
            descricao=f"Resultado de {execucao.estrategia} no Portal de Compras Públicas",
            conteudo=valor, origem="portal_compras_http", metodo_obtencao=execucao.estrategia,
            confianca=execucao.confianca)
        atualizadas += 1
    return atualizadas


def _job_coletar(contratacao_id: int, usuario_id: int):
    db = SessionLocal()
    try:
        c = db.query(Contratacao).filter_by(id=contratacao_id, usuario_id=usuario_id).first()
        plano = (db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao_id)
            .order_by(PlanoInvestigacao.versao.desc()).first())
        if c is None or plano is None:
            return
        pesquisa = Pesquisa(usuario_id=usuario_id, contratacao_id=c.id, termo_busca=c.objeto,
            quantidade_desejada=None, limite_processos=settings.MAX_PROCESSOS, status="pendente")
        db.add(pesquisa)
        db.commit()
        db.refresh(pesquisa)
        executar_e_persistir(pesquisa.id, c.objeto, settings.MAX_PROCESSOS)
        db.expire_all()
        pesquisa = db.query(Pesquisa).filter_by(id=pesquisa.id).one()
        resultado = json.loads(pesquisa.resultado_json) if pesquisa.resultado_json else {"processos": []}
        atualizadas = consolidar_resultado_coleta(db, plano.id, resultado)
        db.add(HistoricoContratacao(contratacao_id=c.id, usuario_id=usuario_id,
            acao="Coleta automática do Plano concluída",
            detalhe=f"Pesquisa #{pesquisa.id} | {atualizadas} informações atualizadas"))
        db.commit()
    except Exception as exc:
        logger.exception("Erro na coleta automática da contratação %s", contratacao_id)
        db.rollback()
        c = db.query(Contratacao).filter_by(id=contratacao_id, usuario_id=usuario_id).first()
        if c:
            c.erro_mensagem = f"Falha parcial na coleta automática: {exc}"
            db.commit()
    finally:
        db.close()


def iniciar_coleta_plano(contratacao_id: int, usuario_id: int):
    db = SessionLocal()
    try:
        job = criar_job(db, "coleta_plano", contratacao_id, referencia_id=contratacao_id)
        job_id = job.id
    finally:
        db.close()

    def executar():
        def pesquisa_estado():
            sessao = SessionLocal()
            try:
                p = (sessao.query(Pesquisa).filter_by(contratacao_id=contratacao_id)
                    .order_by(Pesquisa.id.desc()).first())
                return {"pesquisa_id": p.id if p else None,
                    "pesquisa_status": p.status if p else None}
            finally:
                sessao.close()
        executar_com_retry_idempotente(SessionLocal, job_id,
            lambda: _job_coletar(contratacao_id, usuario_id),
            lambda: pesquisa_estado()["pesquisa_status"] == "completo",
            etapa_execucao="pesquisa_http", etapa_sucesso="evidencias_consolidadas",
            checkpoint=pesquisa_estado)

    threading.Thread(target=executar, daemon=True).start()
