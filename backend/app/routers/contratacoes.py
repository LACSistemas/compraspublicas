import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_active_user
from app.database import get_db
from app.models import (
    BaseConhecimento,
    Contratacao,
    HistoricoContratacao,
    PerguntaContratacao,
    Usuario,
)
from app.models import UsoTokens
from app.schemas import (
    BaseConhecimentoOut,
    ContratacaoCreate,
    ContratacaoListItemOut,
    ContratacaoOut,
    EstatsFase,
    EstatisticasTokensOut,
    PerguntaOut,
    ResponderPerguntaIn,
    TokensPorContratacao,
    ValidarEvidenciaIn,
)
from app.services.bcc_service import iniciar_processamento_bcc
from app.services.investigacao_service import iniciar_geracao_perguntas

router = APIRouter(tags=["contratacoes"])


def _calcular_stats(values: list[int]) -> EstatsFase:
    n = len(values)
    if n == 0:
        return EstatsFase(total_chamadas=0, media=0.0, mediana=0.0, variancia=0.0, minimo=0, maximo=0)
    media = sum(values) / n
    mid = n // 2
    mediana = float(values[mid]) if n % 2 == 1 else (values[mid - 1] + values[mid]) / 2.0
    variancia = sum((v - media) ** 2 for v in values) / n
    return EstatsFase(
        total_chamadas=n,
        media=round(media, 2),
        mediana=round(mediana, 2),
        variancia=round(variancia, 2),
        minimo=values[0],
        maximo=values[-1],
    )


def _buscar_contratacao_ou_404(contratacao_id: int, db: Session, usuario_id: int) -> Contratacao:
    c = (
        db.query(Contratacao)
        .filter(Contratacao.id == contratacao_id, Contratacao.usuario_id == usuario_id)
        .first()
    )
    if c is None:
        raise HTTPException(status_code=404, detail="Contratação não encontrada")
    return c


def _pergunta_to_out(p: PerguntaContratacao) -> PerguntaOut:
    return PerguntaOut(
        id=p.id,
        ordem=p.ordem,
        texto=p.texto,
        alternativas=p.alternativas,
        resposta_escolhida=p.resposta_escolhida,
        respondida_em=p.respondida_em,
    )


def _bcc_to_out(bcc: BaseConhecimento) -> BaseConhecimentoOut:
    return BaseConhecimentoOut(
        progresso_pct=bcc.progresso_pct,
        nivel_maturidade=bcc.nivel_maturidade,
        dados=bcc.dados,
        atualizado_em=bcc.atualizado_em,
    )


def _contratacao_to_out(c: Contratacao) -> ContratacaoOut:
    return ContratacaoOut(
        id=c.id,
        objeto=c.objeto,
        orgao_unidade=c.orgao_unidade,
        numero_processo=c.numero_processo,
        equipe_responsavel=c.equipe_responsavel,
        tipo_contratacao=c.tipo_contratacao,
        contexto_inicial=c.contexto_inicial,
        status=c.status,
        erro_mensagem=c.erro_mensagem,
        criado_em=c.criado_em,
        atualizado_em=c.atualizado_em,
        perguntas=[_pergunta_to_out(p) for p in c.perguntas],
        base_conhecimento=_bcc_to_out(c.base_conhecimento) if c.base_conhecimento else None,
    )


@router.post("/contratacoes", status_code=201, response_model=ContratacaoOut)
def criar_contratacao(
    payload: ContratacaoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    c = Contratacao(
        usuario_id=current_user.id,
        objeto=payload.objeto,
        orgao_unidade=payload.orgao_unidade,
        numero_processo=payload.numero_processo,
        equipe_responsavel=payload.equipe_responsavel,
        tipo_contratacao=payload.tipo_contratacao,
        contexto_inicial=payload.contexto_inicial,
        status="cadastro",
    )
    db.add(c)
    db.flush()

    db.add(HistoricoContratacao(
        contratacao_id=c.id,
        usuario_id=current_user.id,
        acao="Contratação criada",
        detalhe=f"Objeto: {c.objeto} | Órgão: {c.orgao_unidade}",
    ))
    db.commit()
    db.refresh(c)
    return _contratacao_to_out(c)


@router.get("/contratacoes", response_model=list[ContratacaoListItemOut])
def listar_contratacoes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    return (
        db.query(Contratacao)
        .filter(Contratacao.usuario_id == current_user.id)
        .order_by(Contratacao.criado_em.desc())
        .all()
    )


@router.get("/contratacoes/estatisticas/tokens", response_model=EstatisticasTokensOut)
def estatisticas_tokens(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    def _valores_fase(tipo: str) -> list[int]:
        rows = (
            db.query(UsoTokens.tokens_total)
            .filter(UsoTokens.usuario_id == current_user.id, UsoTokens.tipo == tipo)
            .order_by(UsoTokens.tokens_total)
            .all()
        )
        return [r.tokens_total or 0 for r in rows]

    stats_perguntas = _calcular_stats(_valores_fase("perguntas_contratacao"))
    stats_bcc = _calcular_stats(_valores_fase("bcc_contratacao"))

    # Tokens por contratação — duas queries pivot manuais
    perguntas_rows = (
        db.query(
            UsoTokens.referencia_id,
            UsoTokens.tokens_input,
            UsoTokens.tokens_output,
            UsoTokens.tokens_total,
        )
        .filter(UsoTokens.usuario_id == current_user.id, UsoTokens.tipo == "perguntas_contratacao")
        .all()
    )
    bcc_rows = (
        db.query(
            UsoTokens.referencia_id,
            UsoTokens.tokens_input,
            UsoTokens.tokens_output,
            UsoTokens.tokens_total,
        )
        .filter(UsoTokens.usuario_id == current_user.id, UsoTokens.tipo == "bcc_contratacao")
        .all()
    )

    perguntas_map = {r.referencia_id: r for r in perguntas_rows}
    bcc_map = {r.referencia_id: r for r in bcc_rows}

    contratacoes = (
        db.query(Contratacao)
        .filter(Contratacao.usuario_id == current_user.id)
        .order_by(Contratacao.criado_em.desc())
        .all()
    )

    por_contratacao = []
    for c in contratacoes:
        p = perguntas_map.get(c.id)
        b = bcc_map.get(c.id)
        tp_in = p.tokens_input or 0 if p else 0
        tp_out = p.tokens_output or 0 if p else 0
        tp_tot = p.tokens_total or 0 if p else 0
        tb_in = b.tokens_input or 0 if b else 0
        tb_out = b.tokens_output or 0 if b else 0
        tb_tot = b.tokens_total or 0 if b else 0
        por_contratacao.append(TokensPorContratacao(
            contratacao_id=c.id,
            objeto=c.objeto,
            tokens_perguntas_input=tp_in,
            tokens_perguntas_output=tp_out,
            tokens_perguntas_total=tp_tot,
            tokens_bcc_input=tb_in,
            tokens_bcc_output=tb_out,
            tokens_bcc_total=tb_tot,
            total=tp_tot + tb_tot,
        ))

    return EstatisticasTokensOut(perguntas=stats_perguntas, bcc=stats_bcc, por_contratacao=por_contratacao)


@router.get("/contratacoes/{contratacao_id}", response_model=ContratacaoOut)
def obter_contratacao(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    c = (
        db.query(Contratacao)
        .options(
            joinedload(Contratacao.perguntas),
            joinedload(Contratacao.base_conhecimento),
            joinedload(Contratacao.historico),
        )
        .filter(Contratacao.id == contratacao_id, Contratacao.usuario_id == current_user.id)
        .first()
    )
    if c is None:
        raise HTTPException(status_code=404, detail="Contratação não encontrada")
    return _contratacao_to_out(c)


@router.post("/contratacoes/{contratacao_id}/iniciar-investigacao", status_code=202)
def iniciar_investigacao(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    c = _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    if c.status not in ("cadastro", "erro"):
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível iniciar investigação com status '{c.status}'",
        )

    c.status = "gerando_perguntas"
    c.erro_mensagem = None
    db.commit()

    iniciar_geracao_perguntas(contratacao_id)
    return {"detail": "Geração de perguntas iniciada"}


@router.get("/contratacoes/{contratacao_id}/perguntas", response_model=list[PerguntaOut])
def listar_perguntas(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    perguntas = (
        db.query(PerguntaContratacao)
        .filter(PerguntaContratacao.contratacao_id == contratacao_id)
        .order_by(PerguntaContratacao.ordem)
        .all()
    )
    return [_pergunta_to_out(p) for p in perguntas]


@router.post(
    "/contratacoes/{contratacao_id}/perguntas/{pergunta_id}/responder",
    response_model=PerguntaOut,
)
def responder_pergunta(
    contratacao_id: int,
    pergunta_id: int,
    payload: ResponderPerguntaIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)

    if payload.resposta not in ("a", "b", "c", "d", "e"):
        raise HTTPException(status_code=400, detail="Resposta deve ser a, b, c, d ou e")

    p = (
        db.query(PerguntaContratacao)
        .filter(
            PerguntaContratacao.id == pergunta_id,
            PerguntaContratacao.contratacao_id == contratacao_id,
        )
        .first()
    )
    if p is None:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")

    p.resposta_escolhida = payload.resposta
    p.respondida_em = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return _pergunta_to_out(p)


@router.post("/contratacoes/{contratacao_id}/processar-base", status_code=202)
def processar_base(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    c = _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)

    if c.status != "investigacao":
        raise HTTPException(
            status_code=400,
            detail=f"A contratação deve estar em investigação para processar a base (status atual: '{c.status}')",
        )

    perguntas = (
        db.query(PerguntaContratacao)
        .filter(PerguntaContratacao.contratacao_id == contratacao_id)
        .all()
    )
    nao_respondidas = [p for p in perguntas if p.resposta_escolhida is None]
    if nao_respondidas:
        raise HTTPException(
            status_code=400,
            detail=f"{len(nao_respondidas)} pergunta(s) ainda não respondida(s). Responda todas antes de processar.",
        )

    c.status = "processando_bcc"
    c.erro_mensagem = None
    db.commit()

    iniciar_processamento_bcc(contratacao_id)
    return {"detail": "Processamento da Base de Conhecimento iniciado"}


@router.patch("/contratacoes/{contratacao_id}/bcc/evidencias", response_model=BaseConhecimentoOut)
def validar_evidencia(
    contratacao_id: int,
    payload: ValidarEvidenciaIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)

    bcc = db.query(BaseConhecimento).filter(
        BaseConhecimento.contratacao_id == contratacao_id
    ).first()
    if bcc is None:
        raise HTTPException(status_code=404, detail="Base de Conhecimento não encontrada")

    dados = json.loads(bcc.dados_json)
    evidencias = dados.get("evidencias", [])

    if payload.idx < 0 or payload.idx >= len(evidencias):
        raise HTTPException(status_code=400, detail="Índice de evidência inválido")

    evidencias[payload.idx]["status_validacao"] = payload.status_validacao
    if payload.responsavel:
        evidencias[payload.idx]["responsavel"] = payload.responsavel

    dados["evidencias"] = evidencias
    bcc.dados_json = json.dumps(dados, ensure_ascii=False)
    db.add(HistoricoContratacao(
        contratacao_id=contratacao_id,
        usuario_id=current_user.id,
        acao=f"Evidência #{payload.idx + 1} marcada como '{payload.status_validacao}'",
        detalhe=evidencias[payload.idx].get("descricao", ""),
    ))
    db.commit()
    db.refresh(bcc)
    return _bcc_to_out(bcc)
