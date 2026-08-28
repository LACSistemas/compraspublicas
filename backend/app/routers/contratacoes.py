import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.auth import get_active_user, get_active_user_download
from app.database import get_db
from app.models import (
    BaseConhecimento,
    Contratacao,
    HistoricoContratacao,
    PerguntaContratacao,
    Usuario,
    CardDecisaoCatalogo,
    CardInformacao,
    CardDependencia,
    InformacaoCatalogo,
    PlanoCardDecisao,
    PlanoInvestigacao,
    PlanoInformacao,
    Pesquisa,
    EvidenciaPlano,
    ConhecimentoCard,
    SnapshotBCC,
    CriterioCardCatalogo,
    EvidenciaCriterio,
    JobExecucao,
    Geracao,
)
from app.config import settings
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
    PlanoCardOut,
    PlanoInvestigacaoOut,
    EvidenciaPlanoOut,
    ValidarEvidenciaPlanoIn,
    SubstituirEvidenciaIn,
    ConhecimentoCardOut,
    RevisarConhecimentoIn,
    VincularCriteriosIn,
    RevisarDispensaIn,
    ResumoLacunasPlanoOut,
    RevisarRecomendacaoIn,
    GeracaoCreate,
    GeracaoDetailOut,
)
from app.services.bcc_service import iniciar_processamento_bcc
from app.services.investigacao_service import iniciar_geracao_perguntas
from app.services.plano_investigacao_service import criar_plano_deterministico
from app.services.planejamento_service import iniciar_planejamento, _pergunta_fallback
from app.services.pesquisa_precos_service import (iniciar_pesquisa_automatica,
    consolidar_campanha_no_plano, extrair_documentos_comparaveis)
from app.models import CampanhaPesquisaPrecos
from app.services.coleta_plano_service import iniciar_coleta_plano
from app.services.coleta_plano_service import listar_lacunas
from app.services.evidencia_plano_service import (
    criar_evidencia, extrair_e_registrar_pdf, invalidar_conhecimento_por_informacao,
    substituir_evidencia,
)
from app.services.conhecimento_card_service import consolidar_bcc, gerar_conhecimentos
from app.services.governanca_ia_service import consumo_tokens_contratacao
from app.services.politica_governanca_service import robustez_minima_aprovacao
from app.services.job_runner import iniciar_job_geracao
import os

router = APIRouter(tags=["contratacoes"])


def _exigir_novo_fluxo() -> None:
    if not settings.INVESTIGACAO_HABILITADA:
        raise HTTPException(status_code=404, detail="Plano de Investigação não habilitado")


def _plano_to_out(plano: PlanoInvestigacao, db: Session) -> PlanoInvestigacaoOut:
    itens = db.query(PlanoCardDecisao).filter_by(plano_id=plano.id).order_by(PlanoCardDecisao.ordem).all()
    cards_out = []
    for item in itens:
        card = db.query(CardDecisaoCatalogo).filter_by(id=item.card_id).one()
        vinculos = db.query(CardInformacao).filter_by(card_id=card.id).order_by(CardInformacao.ordem).all()
        informacoes = []
        for vinculo in vinculos:
            info = db.query(InformacaoCatalogo).filter_by(id=vinculo.informacao_id).one()
            execucao = db.query(PlanoInformacao).filter_by(
                plano_card_id=item.id, informacao_id=info.id).first()
            informacoes.append({"id": execucao.id if execucao else None,
                "codigo": info.codigo, "nome": info.nome, "tipo": info.tipo,
                "obrigatoriedade": info.obrigatoriedade,
                "estrategia_preferencial": info.estrategia_preferencial,
                "estrategia": execucao.estrategia if execucao else info.estrategia_preferencial,
                "status": execucao.status if execucao else "nao_planejada",
                "justificativa_estrategia": execucao.justificativa_estrategia if execucao else None,
                "valor": json.loads(execucao.valor_json) if execucao and execucao.valor_json else None,
                "origem": execucao.origem if execucao else None,
                "confianca": execucao.confianca if execucao else None,
                "estado_semantico": execucao.estado_semantico if execucao else "nao_informado"})
        deps = db.query(CardDependencia).filter_by(card_id=card.id).all()
        dependencias = [db.query(CardDecisaoCatalogo).filter_by(id=d.depende_de_card_id).one().codigo for d in deps]
        cards_out.append(PlanoCardOut(id=item.id, codigo=card.codigo, nome=card.nome,
            pergunta_controle=card.pergunta_controle, ordem=item.ordem, status=item.status,
            aplicavel=item.aplicavel, justificativa_dispensa=item.justificativa_dispensa,
            robustez_pct=item.robustez_pct, informacoes=informacoes, dependencias=dependencias,
            dispensa_status=item.dispensa_status, dispensa_revisada_em=item.dispensa_revisada_em))
    return PlanoInvestigacaoOut(id=plano.id, contratacao_id=plano.contratacao_id,
        versao=plano.versao, status=plano.status, cards=cards_out,
        criado_em=plano.criado_em, atualizado_em=plano.atualizado_em)


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


def _pesquisa_documental(db: Session, contratacao: Contratacao) -> Pesquisa:
    pesquisa = (db.query(Pesquisa).filter_by(contratacao_id=contratacao.id)
        .order_by(Pesquisa.id.desc()).first())
    if pesquisa is None:
        pesquisa = Pesquisa(
            usuario_id=contratacao.usuario_id,
            contratacao_id=contratacao.id,
            termo_busca=contratacao.objeto,
            quantidade_desejada=None,
            limite_processos=0,
            status="completo",
            resultado_json=json.dumps({
                "origem": "contratacao",
                "objeto": contratacao.objeto,
                "orgao_unidade": contratacao.orgao_unidade,
                "numero_processo": contratacao.numero_processo,
                "contexto_inicial": contratacao.contexto_inicial,
            }, ensure_ascii=False),
        )
        db.add(pesquisa)
        db.commit()
        db.refresh(pesquisa)
    return pesquisa


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

    c.status = "gerando_plano" if settings.INVESTIGACAO_HABILITADA else "gerando_perguntas"
    c.erro_mensagem = None
    db.commit()

    iniciar_pesquisa_automatica(contratacao_id)

    if settings.INVESTIGACAO_HABILITADA:
        iniciar_planejamento(contratacao_id)
        return {"detail": "Geração do Plano de Investigação iniciada"}
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
    p.respondida_em = datetime.now(timezone.utc).replace(tzinfo=None)
    if p.plano_informacao_id:
        alternativa = next((a for a in p.alternativas if a.get("letra") == payload.resposta), None)
        execucao = db.query(PlanoInformacao).filter_by(id=p.plano_informacao_id).one()
        valor = {"pergunta": p.texto, "resposta": payload.resposta,
            "alternativa": alternativa.get("texto") if alternativa else None}
        execucao.valor_json = json.dumps(valor, ensure_ascii=False)
        execucao.status = "coletada_resposta"
        execucao.estado_semantico = "informado"
        execucao.origem = "resposta_gestor"
        execucao.confianca = "alta"
        criar_evidencia(db, execucao.id, tipo="declaracao_gestor",
            descricao=f"Resposta do gestor à informação do Plano #{execucao.id}",
            conteudo=valor, origem="resposta_gestor", metodo_obtencao="pergunta",
            confianca="alta")
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

    # Antes de consolidar, converte lacunas obrigatórias ainda sem cobertura em
    # uma rodada curta de perguntas complementares. Os Cards continuam sendo o
    # mecanismo de controle, mas o gestor vê apenas a ação necessária.
    plano = (db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao_id)
        .order_by(PlanoInvestigacao.versao.desc()).first())
    if plano is not None:
        ja_perguntadas = {p.plano_informacao_id for p in perguntas if p.plano_informacao_id}
        pendencias = (db.query(PlanoInformacao, InformacaoCatalogo)
            .join(PlanoCardDecisao, PlanoInformacao.plano_card_id == PlanoCardDecisao.id)
            .join(InformacaoCatalogo, PlanoInformacao.informacao_id == InformacaoCatalogo.id)
            .filter(
                PlanoCardDecisao.plano_id == plano.id,
                PlanoCardDecisao.aplicavel.is_(True),
                InformacaoCatalogo.obrigatoriedade == "obrigatoria",
                PlanoInformacao.estado_semantico.in_(["nao_informado", "inferido", "contraditorio"]),
            )
            .order_by(PlanoCardDecisao.ordem, InformacaoCatalogo.codigo)
            .all())
        novas = [(execucao, info) for execucao, info in pendencias
            if execucao.id not in ja_perguntadas][:8]
        if novas:
            proxima_ordem = max((p.ordem for p in perguntas), default=0) + 1
            for deslocamento, (execucao, info) in enumerate(novas):
                pergunta = _pergunta_fallback({"codigo": info.codigo, "nome": info.nome}, c.objeto)
                execucao.estrategia = "pergunta"
                execucao.status = "aguardando_resposta"
                db.add(PerguntaContratacao(
                    contratacao_id=contratacao_id,
                    plano_informacao_id=execucao.id,
                    ordem=proxima_ordem + deslocamento,
                    texto=pergunta["texto"],
                    alternativas_json=json.dumps(pergunta["alternativas"], ensure_ascii=False),
                ))
            db.add(HistoricoContratacao(
                contratacao_id=contratacao_id,
                usuario_id=current_user.id,
                acao="Rodada complementar de investigação criada",
                detalhe=f"{len(novas)} lacuna(s) obrigatória(s) convertida(s) em perguntas",
            ))
            db.commit()
            return {"detail": "Há pendências que exigem confirmação do gestor",
                "perguntas_adicionais": len(novas)}

    c.status = "processando_bcc"
    c.erro_mensagem = None
    db.commit()

    iniciar_processamento_bcc(contratacao_id)
    return {"detail": "Processamento da Base de Conhecimento iniciado"}


@router.post("/contratacoes/{contratacao_id}/aprofundar-investigacao", status_code=202)
def aprofundar_investigacao(contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user)):
    c = _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    if c.status != "bcc_ativa":
        raise HTTPException(status_code=409, detail="A Base precisa estar pronta para aprofundamento")
    campanha = (db.query(CampanhaPesquisaPrecos).filter_by(contratacao_id=contratacao_id)
        .order_by(CampanhaPesquisaPrecos.id.desc()).first())
    referencias = consolidar_campanha_no_plano(db, campanha) if campanha else 0
    documentos = extrair_documentos_comparaveis(db, campanha) if campanha else 0
    plano = (db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao_id)
        .order_by(PlanoInvestigacao.versao.desc()).first())
    if plano is None:
        raise HTTPException(status_code=409, detail="Plano de Investigação não encontrado")
    existentes = db.query(PerguntaContratacao).filter_by(contratacao_id=contratacao_id).all()
    pendentes_por_info = {p.plano_informacao_id for p in existentes
        if p.plano_informacao_id and p.resposta_escolhida is None}
    candidatos = (db.query(PlanoInformacao, InformacaoCatalogo)
        .join(PlanoCardDecisao, PlanoCardDecisao.id == PlanoInformacao.plano_card_id)
        .join(InformacaoCatalogo, InformacaoCatalogo.id == PlanoInformacao.informacao_id)
        .filter(PlanoCardDecisao.plano_id == plano.id).order_by(InformacaoCatalogo.codigo).all())
    codigos_genericos = {p.plano_informacao_id for p in existentes if p.plano_informacao_id and
        (p.texto.startswith("Qual definição objetiva deve constar") or
         "qual é a situação" in p.texto.lower())}
    novas = []
    proxima_ordem = max((p.ordem for p in existentes), default=0) + 1
    for info_plano, catalogo in candidatos:
        precisa_confirmar = (info_plano.id in codigos_genericos or
            (catalogo.obrigatoriedade == "obrigatoria" and
             info_plano.estado_semantico in {"nao_informado", "inferido", "contraditorio"}))
        if not precisa_confirmar or info_plano.id in pendentes_por_info:
            continue
        pergunta = _pergunta_fallback({"codigo": catalogo.codigo, "nome": catalogo.nome}, c.objeto)
        db.add(PerguntaContratacao(contratacao_id=c.id, plano_informacao_id=info_plano.id,
            ordem=proxima_ordem + len(novas), texto=pergunta["texto"],
            alternativas_json=json.dumps(pergunta["alternativas"], ensure_ascii=False)))
        info_plano.estrategia = "pergunta"
        info_plano.status = "aguardando_resposta"
        novas.append(catalogo.codigo)
        if len(novas) >= 8:
            break
    if novas:
        c.status = "investigacao"
        db.add(HistoricoContratacao(contratacao_id=c.id, usuario_id=current_user.id,
            acao="Aprofundamento da Base iniciado",
            detalhe=(f"{referencias} referências integradas | {documentos} documentos extraídos | "
                f"perguntas: {', '.join(novas)}")))
        db.commit()
        return {"detail": "Rodada de aprofundamento criada", "perguntas_adicionais": len(novas)}
    c.status = "processando_bcc"
    db.commit()
    iniciar_processamento_bcc(c.id)
    return {"detail": "Referências integradas; Base em reprocessamento", "perguntas_adicionais": 0}


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


@router.patch("/contratacoes/{contratacao_id}/bcc/recomendacoes", response_model=BaseConhecimentoOut)
def revisar_recomendacao(
    contratacao_id: int,
    payload: RevisarRecomendacaoIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    bcc = db.query(BaseConhecimento).filter_by(contratacao_id=contratacao_id).first()
    if bcc is None:
        raise HTTPException(status_code=404, detail="Base de Conhecimento não encontrada")
    dados = json.loads(bcc.dados_json)
    recomendacoes = dados.get("recomendacoes", [])
    if payload.idx >= len(recomendacoes):
        raise HTTPException(status_code=400, detail="Índice de recomendação inválido")
    novo_status = "executada" if payload.decisao == "executar" else "dispensada"
    recomendacoes[payload.idx]["status"] = novo_status
    recomendacoes[payload.idx]["decidido_em"] = datetime.now(timezone.utc).isoformat()
    recomendacoes[payload.idx]["decidido_por_usuario_id"] = current_user.id
    dados["recomendacoes"] = recomendacoes
    bcc.dados_json = json.dumps(dados, ensure_ascii=False)
    db.add(HistoricoContratacao(
        contratacao_id=contratacao_id,
        usuario_id=current_user.id,
        acao=f"Recomendação #{payload.idx + 1} {novo_status}",
        detalhe=recomendacoes[payload.idx].get("descricao", ""),
    ))
    db.commit()
    db.refresh(bcc)
    return _bcc_to_out(bcc)


@router.post("/contratacoes/{contratacao_id}/documentos", status_code=202)
def criar_documento_contratacao(
    contratacao_id: int,
    payload: GeracaoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    contratacao = _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    if contratacao.base_conhecimento is None:
        raise HTTPException(status_code=409, detail="Consolide a BCC antes de gerar documentos")
    pesquisa = _pesquisa_documental(db, contratacao)
    em_andamento = db.query(Geracao).filter(
        Geracao.pesquisa_id == pesquisa.id,
        Geracao.tipo == payload.tipo,
        Geracao.status.in_(["pendente", "em_andamento"]),
    ).first()
    if em_andamento:
        raise HTTPException(status_code=409,
            detail=f"Já existe uma geração de {payload.tipo.upper()} em andamento")
    geracao = Geracao(pesquisa_id=pesquisa.id, tipo=payload.tipo, status="pendente")
    db.add(geracao)
    db.commit()
    db.refresh(geracao)
    params = payload.model_dump()
    iniciar_job_geracao(geracao.id, pesquisa.id, params, current_user.id)
    return {"geracao_id": geracao.id, "status": geracao.status}


@router.get("/contratacoes/{contratacao_id}/documentos", response_model=GeracaoDetailOut)
def obter_documento_contratacao(
    contratacao_id: int,
    tipo: str = "etp",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    pesquisa = (db.query(Pesquisa).filter_by(contratacao_id=contratacao_id)
        .order_by(Pesquisa.id.desc()).first())
    if pesquisa is None:
        raise HTTPException(status_code=404, detail="Nenhuma geração encontrada")
    geracao = (db.query(Geracao).filter_by(pesquisa_id=pesquisa.id, tipo=tipo)
        .order_by(Geracao.id.desc()).first())
    if geracao is None:
        raise HTTPException(status_code=404, detail=f"Nenhuma geração de {tipo.upper()} encontrada")
    resultado = json.loads(geracao.resultado_json) if geracao.resultado_json else None
    return GeracaoDetailOut(
        id=geracao.id, tipo=geracao.tipo, status=geracao.status,
        erro_mensagem=geracao.erro_mensagem,
        pendencias=resultado.get("pendencias") if resultado else None,
        arquivo_disponivel=bool(geracao.arquivo_gerado and os.path.isfile(geracao.arquivo_gerado)),
        resultado=resultado, modelo_gemini=geracao.modelo_gemini,
        criado_em=geracao.criado_em, atualizado_em=geracao.atualizado_em,
    )


@router.get("/contratacoes/{contratacao_id}/documentos/download")
def download_documento_contratacao(
    contratacao_id: int,
    tipo: str = "etp",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user_download),
):
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    pesquisa = (db.query(Pesquisa).filter_by(contratacao_id=contratacao_id)
        .order_by(Pesquisa.id.desc()).first())
    geracao = ((db.query(Geracao).filter_by(pesquisa_id=pesquisa.id, tipo=tipo)
        .order_by(Geracao.id.desc()).first()) if pesquisa else None)
    if geracao is None or not geracao.arquivo_gerado or not os.path.isfile(geracao.arquivo_gerado):
        raise HTTPException(status_code=404, detail="Documento não disponível")
    return FileResponse(
        geracao.arquivo_gerado,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(geracao.arquivo_gerado),
    )


@router.post("/contratacoes/{contratacao_id}/plano", response_model=PlanoInvestigacaoOut, status_code=201)
def criar_plano_investigacao(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    contratacao = _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    plano = criar_plano_deterministico(db, contratacao)
    return _plano_to_out(plano, db)


@router.get("/contratacoes/{contratacao_id}/plano", response_model=PlanoInvestigacaoOut)
def obter_plano_investigacao(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    plano = (db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao_id)
        .order_by(PlanoInvestigacao.versao.desc()).first())
    if plano is None:
        raise HTTPException(status_code=404, detail="Plano de Investigação não encontrado")
    return _plano_to_out(plano, db)


@router.get("/contratacoes/{contratacao_id}/plano/metricas-ia")
def obter_metricas_ia_contratacao(
    contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    return consumo_tokens_contratacao(db, contratacao_id)


@router.get("/contratacoes/{contratacao_id}/jobs")
def listar_jobs_contratacao(
    contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    jobs = (db.query(JobExecucao).filter_by(contratacao_id=contratacao_id)
        .order_by(JobExecucao.id.desc()).all())
    return [{"id": job.id, "tipo": job.tipo, "referencia_id": job.referencia_id,
        "status": job.status, "etapa": job.etapa, "tentativa": job.tentativa,
        "max_tentativas": job.max_tentativas, "checkpoint": json.loads(job.checkpoint_json),
        "erro_mensagem": job.erro_mensagem, "criado_em": job.criado_em,
        "atualizado_em": job.atualizado_em} for job in jobs]


@router.patch("/contratacoes/{contratacao_id}/plano/cards/{plano_card_id}/dispensa",
    response_model=PlanoInvestigacaoOut)
def revisar_dispensa_card(
    contratacao_id: int, plano_card_id: int, payload: RevisarDispensaIn,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    item = (db.query(PlanoCardDecisao).join(PlanoInvestigacao)
        .filter(PlanoCardDecisao.id == plano_card_id,
            PlanoInvestigacao.contratacao_id == contratacao_id).first())
    if item is None:
        raise HTTPException(status_code=404, detail="Card do Plano não encontrado")
    if item.dispensa_status != "proposta":
        raise HTTPException(status_code=409, detail="O Card não possui dispensa aguardando revisão")
    item.dispensa_revisada_por_usuario_id = current_user.id
    item.dispensa_revisada_em = datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.decisao == "aprovar":
        item.dispensa_status, item.status, item.aplicavel = "aprovada", "dispensado", False
        for info in db.query(PlanoInformacao).filter_by(plano_card_id=item.id).all():
            info.estado_semantico = "nao_aplicavel"
    else:
        item.dispensa_status, item.status, item.aplicavel = "rejeitada", "pendente", True
        for info in db.query(PlanoInformacao).filter_by(plano_card_id=item.id).all():
            info.estado_semantico = "nao_informado"
            info.status = ("aguardando_resposta" if info.estrategia == "pergunta" else
                "aguardando_upload" if info.estrategia == "upload" else "pendente_coleta")
    card = db.query(CardDecisaoCatalogo).filter_by(id=item.card_id).one()
    db.add(HistoricoContratacao(contratacao_id=contratacao_id, usuario_id=current_user.id,
        acao=f"Dispensa do Card {card.codigo} {item.dispensa_status}",
        detalhe=item.justificativa_dispensa))
    db.commit()
    plano = db.query(PlanoInvestigacao).filter_by(id=item.plano_id).one()
    return _plano_to_out(plano, db)


@router.post("/contratacoes/{contratacao_id}/plano/coletar", status_code=202)
def coletar_informacoes_plano(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    plano = db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao_id).first()
    if plano is None:
        raise HTTPException(status_code=409, detail="Crie o Plano de Investigação antes da coleta")
    pendentes = (db.query(PlanoInformacao).join(PlanoCardDecisao)
        .filter(PlanoCardDecisao.plano_id == plano.id,
            PlanoInformacao.estrategia.in_(["consulta", "integracao"]),
            PlanoInformacao.status == "pendente_coleta").count())
    if pendentes == 0:
        raise HTTPException(status_code=409, detail="Não há consultas ou integrações pendentes")
    em_andamento = db.query(Pesquisa).filter(
        Pesquisa.contratacao_id == contratacao_id,
        Pesquisa.status.in_(["pendente", "em_andamento"])).first()
    if em_andamento:
        raise HTTPException(status_code=409, detail="Já existe coleta automática em andamento")
    iniciar_coleta_plano(contratacao_id, current_user.id)
    return {"detail": "Coleta automática iniciada", "informacoes_pendentes": pendentes}


@router.get("/contratacoes/{contratacao_id}/plano/lacunas", response_model=ResumoLacunasPlanoOut)
def listar_lacunas_plano(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    plano = (db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao_id)
        .order_by(PlanoInvestigacao.versao.desc()).first())
    if plano is None:
        raise HTTPException(status_code=409, detail="Crie o Plano de Investigação antes de consultar lacunas")
    return listar_lacunas(db, plano.id)


@router.post("/contratacoes/{contratacao_id}/plano/informacoes/{plano_informacao_id}/upload")
async def upload_informacao_plano(
    contratacao_id: int,
    plano_informacao_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    execucao = (db.query(PlanoInformacao).join(PlanoCardDecisao).join(PlanoInvestigacao)
        .filter(PlanoInformacao.id == plano_informacao_id,
            PlanoInvestigacao.contratacao_id == contratacao_id).first())
    if execucao is None:
        raise HTTPException(status_code=404, detail="Informação do Plano não encontrada")
    if execucao.estrategia != "upload":
        raise HTTPException(status_code=409, detail="Esta informação não está configurada para upload")
    conteudo = await arquivo.read(settings.MAX_UPLOAD_BYTES + 1)
    if not conteudo or len(conteudo) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo vazio ou acima do limite permitido")
    nome_original = Path(arquivo.filename or "documento").name
    extensao = Path(nome_original).suffix.lower()
    if extensao not in {".pdf", ".docx", ".xlsx"}:
        raise HTTPException(status_code=415, detail="Formato não permitido")
    if extensao == ".pdf" and not conteudo.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="Conteúdo não corresponde a um PDF válido")
    pasta = Path(settings.UPLOADS_DIR) / "contratacoes" / str(contratacao_id)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{uuid4().hex}{extensao}"
    destino.write_bytes(conteudo)
    execucao.valor_json = json.dumps({"arquivo": destino.name, "nome_original": nome_original,
        "tamanho_bytes": len(conteudo)}, ensure_ascii=False)
    execucao.status = "coletada_upload"
    execucao.estado_semantico = "informado"
    execucao.origem = "upload_usuario"
    execucao.confianca = "alta"
    criar_evidencia(db, execucao.id, tipo="documento_upload",
        descricao=f"Documento enviado pelo usuário: {nome_original}",
        conteudo={"arquivo": destino.name, "nome_original": nome_original,
            "tamanho_bytes": len(conteudo)}, origem="upload_usuario",
        metodo_obtencao="upload", confianca="alta")
    if extensao == ".pdf":
        evidencia_texto = extrair_e_registrar_pdf(db, execucao.id, str(destino), nome_original)
        if evidencia_texto.metodo_obtencao != "extracao_falhou":
            execucao.status = "coletada_upload_extraida"
    db.add(HistoricoContratacao(contratacao_id=contratacao_id, usuario_id=current_user.id,
        acao="Documento anexado a informação do Plano", detalhe=f"{nome_original} | {len(conteudo)} bytes"))
    db.commit()
    return {"detail": "Upload recebido", "informacao_id": execucao.id, "status": execucao.status}


def _evidencia_plano_to_out(e: EvidenciaPlano, db: Session) -> EvidenciaPlanoOut:
    vinculos = db.query(EvidenciaCriterio).filter_by(evidencia_id=e.id).all()
    criterios = [db.query(CriterioCardCatalogo).filter_by(id=v.criterio_id).one().codigo
        for v in vinculos]
    return EvidenciaPlanoOut(id=e.id, plano_informacao_id=e.plano_informacao_id,
        tipo=e.tipo, descricao=e.descricao, conteudo=json.loads(e.conteudo_json),
        origem=e.origem, metodo_obtencao=e.metodo_obtencao, confianca=e.confianca,
        hash_conteudo=e.hash_conteudo, status_validacao=e.status_validacao,
        estado=e.estado, substitui_evidencia_id=e.substitui_evidencia_id,
        criterios_atendidos=criterios,
        criado_em=e.criado_em)


@router.get("/contratacoes/{contratacao_id}/plano/evidencias", response_model=list[EvidenciaPlanoOut])
def listar_evidencias_plano(
    contratacao_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    evidencias = (db.query(EvidenciaPlano).join(PlanoInformacao).join(PlanoCardDecisao)
        .join(PlanoInvestigacao).filter(PlanoInvestigacao.contratacao_id == contratacao_id)
        .order_by(EvidenciaPlano.criado_em).all())
    return [_evidencia_plano_to_out(e, db) for e in evidencias]


@router.patch("/contratacoes/{contratacao_id}/plano/evidencias/{evidencia_id}", response_model=EvidenciaPlanoOut)
def validar_evidencia_plano(
    contratacao_id: int,
    evidencia_id: int,
    payload: ValidarEvidenciaPlanoIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    evidencia = (db.query(EvidenciaPlano).join(PlanoInformacao).join(PlanoCardDecisao)
        .join(PlanoInvestigacao).filter(EvidenciaPlano.id == evidencia_id,
            PlanoInvestigacao.contratacao_id == contratacao_id).first())
    if evidencia is None:
        raise HTTPException(status_code=404, detail="Evidência não encontrada")
    evidencia.status_validacao = payload.status_validacao
    plano_info = db.query(PlanoInformacao).filter_by(id=evidencia.plano_informacao_id).one()
    if payload.status_validacao == "confirmada" and evidencia.estado == "vigente":
        plano_info.estado_semantico = "confirmado"
    elif payload.status_validacao == "rejeitada":
        plano_info.estado_semantico = "nao_informado"
    invalidar_conhecimento_por_informacao(db, evidencia.plano_informacao_id)
    db.add(HistoricoContratacao(contratacao_id=contratacao_id, usuario_id=current_user.id,
        acao=f"Evidência do Plano marcada como {payload.status_validacao}",
        detalhe=f"Evidência #{evidencia.id}: {evidencia.descricao}"))
    db.commit()
    db.refresh(evidencia)
    return _evidencia_plano_to_out(evidencia, db)


@router.put("/contratacoes/{contratacao_id}/plano/evidencias/{evidencia_id}/criterios",
    response_model=EvidenciaPlanoOut)
def vincular_criterios_evidencia(
    contratacao_id: int, evidencia_id: int, payload: VincularCriteriosIn,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    evidencia = (db.query(EvidenciaPlano).join(PlanoInformacao).join(PlanoCardDecisao)
        .join(PlanoInvestigacao).filter(EvidenciaPlano.id == evidencia_id,
            PlanoInvestigacao.contratacao_id == contratacao_id).first())
    if evidencia is None:
        raise HTTPException(status_code=404, detail="Evidência não encontrada")
    plano_info = db.query(PlanoInformacao).filter_by(id=evidencia.plano_informacao_id).one()
    plano_card = db.query(PlanoCardDecisao).filter_by(id=plano_info.plano_card_id).one()
    criterios = db.query(CriterioCardCatalogo).filter(
        CriterioCardCatalogo.card_id == plano_card.card_id,
        CriterioCardCatalogo.codigo.in_(payload.criterios)).all()
    if len(criterios) != len(set(payload.criterios)):
        raise HTTPException(status_code=400, detail="Critério inexistente ou pertencente a outro Card")
    db.query(EvidenciaCriterio).filter_by(evidencia_id=evidencia.id).delete()
    for criterio in criterios:
        db.add(EvidenciaCriterio(evidencia_id=evidencia.id, criterio_id=criterio.id))
    invalidar_conhecimento_por_informacao(db, evidencia.plano_informacao_id)
    db.commit()
    return _evidencia_plano_to_out(evidencia, db)


@router.post("/contratacoes/{contratacao_id}/plano/evidencias/{evidencia_id}/substituir",
    response_model=EvidenciaPlanoOut)
def resolver_substituicao_evidencia(
    contratacao_id: int, evidencia_id: int, payload: SubstituirEvidenciaIn,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    def _evidencia_escopada(eid: int):
        return (db.query(EvidenciaPlano).join(PlanoInformacao).join(PlanoCardDecisao)
            .join(PlanoInvestigacao).filter(EvidenciaPlano.id == eid,
                PlanoInvestigacao.contratacao_id == contratacao_id).first())
    nova = _evidencia_escopada(evidencia_id)
    anterior = _evidencia_escopada(payload.evidencia_anterior_id)
    if nova is None or anterior is None:
        raise HTTPException(status_code=404, detail="Evidência não encontrada")
    try:
        substituir_evidencia(db, nova, anterior)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(nova)
    return _evidencia_plano_to_out(nova, db)


def _conhecimento_to_out(c: ConhecimentoCard, db: Session) -> ConhecimentoCardOut:
    item = db.query(PlanoCardDecisao).filter_by(id=c.plano_card_id).one()
    card = db.query(CardDecisaoCatalogo).filter_by(id=item.card_id).one()
    return ConhecimentoCardOut(id=c.id, plano_card_id=c.plano_card_id, codigo_card=card.codigo,
        versao=c.versao, conclusao=c.conclusao, motivacao=c.motivacao,
        fundamentacao=json.loads(c.fundamentacao_json), riscos=json.loads(c.riscos_json),
        recomendacoes=json.loads(c.recomendacoes_json), evidencias=json.loads(c.evidencias_json),
        robustez_pct=c.robustez_pct, status=c.status, aprovado_em=c.aprovado_em,
        cobertura_criterios=json.loads(c.cobertura_criterios_json),
        dimensoes_robustez=json.loads(c.dimensoes_robustez_json),
        fontes_confirmadas=json.loads(c.fontes_confirmadas_json))


@router.post("/contratacoes/{contratacao_id}/plano/conhecimentos", response_model=list[ConhecimentoCardOut])
def gerar_conhecimentos_cards(
    contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    plano = db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao_id).order_by(
        PlanoInvestigacao.versao.desc()).first()
    if plano is None:
        raise HTTPException(status_code=409, detail="Plano de Investigação não encontrado")
    conhecimentos = gerar_conhecimentos(db, plano)
    db.commit()
    return [_conhecimento_to_out(c, db) for c in conhecimentos]


@router.get("/contratacoes/{contratacao_id}/plano/conhecimentos", response_model=list[ConhecimentoCardOut])
def listar_conhecimentos_cards(
    contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    rows = (db.query(ConhecimentoCard).join(PlanoCardDecisao).join(PlanoInvestigacao)
        .filter(PlanoInvestigacao.contratacao_id == contratacao_id)
        .order_by(ConhecimentoCard.plano_card_id, ConhecimentoCard.versao.desc()).all())
    return [_conhecimento_to_out(c, db) for c in rows]


@router.patch("/contratacoes/{contratacao_id}/plano/conhecimentos/{conhecimento_id}",
    response_model=ConhecimentoCardOut)
def revisar_conhecimento_card(
    contratacao_id: int, conhecimento_id: int, payload: RevisarConhecimentoIn,
    db: Session = Depends(get_db), current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    conhecimento = (db.query(ConhecimentoCard).join(PlanoCardDecisao).join(PlanoInvestigacao)
        .filter(ConhecimentoCard.id == conhecimento_id,
            PlanoInvestigacao.contratacao_id == contratacao_id).first())
    if conhecimento is None:
        raise HTTPException(status_code=404, detail="Conhecimento não encontrado")
    ultimo = (db.query(ConhecimentoCard).filter_by(plano_card_id=conhecimento.plano_card_id)
        .order_by(ConhecimentoCard.versao.desc()).first())
    if ultimo is None or ultimo.id != conhecimento.id:
        raise HTTPException(status_code=409, detail="Somente a versão mais recente pode ser revisada")
    if conhecimento.status == "aguardando_evidencia" and payload.status == "aprovado":
        raise HTTPException(status_code=409, detail="Conhecimento com evidências obrigatórias pendentes")
    card_item = db.query(PlanoCardDecisao).filter_by(id=conhecimento.plano_card_id).one()
    card_catalogo = db.query(CardDecisaoCatalogo).filter_by(id=card_item.card_id).one()
    minimo = robustez_minima_aprovacao(card_catalogo.codigo)
    if payload.status == "aprovado" and conhecimento.robustez_pct < minimo:
        raise HTTPException(status_code=409,
            detail=f"O Card {card_catalogo.codigo} exige robustez mínima de {minimo}% para aprovação")
    conhecimento.status = payload.status
    conhecimento.aprovado_por_usuario_id = current_user.id if payload.status == "aprovado" else None
    conhecimento.aprovado_em = datetime.now(timezone.utc).replace(tzinfo=None) if payload.status == "aprovado" else None
    db.commit()
    db.refresh(conhecimento)
    return _conhecimento_to_out(conhecimento, db)


@router.post("/contratacoes/{contratacao_id}/plano/consolidar-bcc", response_model=BaseConhecimentoOut)
def consolidar_bcc_cards(
    contratacao_id: int, db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_active_user),
):
    _exigir_novo_fluxo()
    _buscar_contratacao_ou_404(contratacao_id, db, current_user.id)
    plano = db.query(PlanoInvestigacao).filter_by(contratacao_id=contratacao_id).order_by(
        PlanoInvestigacao.versao.desc()).first()
    if plano is None:
        raise HTTPException(status_code=409, detail="Plano não encontrado")
    conhecimentos = []
    for item in db.query(PlanoCardDecisao).filter_by(plano_id=plano.id).all():
        ultimo = db.query(ConhecimentoCard).filter_by(plano_card_id=item.id).order_by(
            ConhecimentoCard.versao.desc()).first()
        if ultimo:
            conhecimentos.append(ultimo)
    if not conhecimentos:
        raise HTTPException(status_code=409, detail="Gere os conhecimentos dos Cards antes da consolidação")
    bcc, _ = consolidar_bcc(db, contratacao_id, conhecimentos)
    db.commit()
    db.refresh(bcc)
    return _bcc_to_out(bcc)
