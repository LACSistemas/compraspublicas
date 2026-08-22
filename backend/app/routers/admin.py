from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_owner_user
from app.database import get_db
from app.models import UsoTokens, Usuario

router = APIRouter(prefix="/admin", tags=["admin"])


class UsuarioAdmin(BaseModel):
    id: int
    email: str
    nome: str
    is_active: bool
    is_owner: bool
    tokens_total: int
    criado_em: Optional[datetime]

    model_config = {"from_attributes": True}


class TokensPorDia(BaseModel):
    data: str
    total: int


class TokensPorTipo(BaseModel):
    tipo: str
    total: int
    media: float


class TopUsuario(BaseModel):
    email: str
    nome: str
    tokens_total: int


class EstatsFaseAdmin(BaseModel):
    total_chamadas: int
    media: float
    mediana: float
    variancia: float
    minimo: int
    maximo: int


class DashboardResponse(BaseModel):
    total_usuarios: int
    usuarios_ativos: int
    usuarios_aguardando: int
    tokens_hoje: int
    tokens_semana: int
    tokens_mes: int
    tokens_total: int
    media_tokens_etp: float
    media_tokens_tr: float
    media_tokens_pesquisa: float
    media_tokens_analise: float
    tokens_por_dia: List[TokensPorDia]
    tokens_por_tipo: List[TokensPorTipo]
    top_usuarios: List[TopUsuario]
    stats_perguntas_global: EstatsFaseAdmin
    stats_bcc_global: EstatsFaseAdmin


@router.get("/usuarios", response_model=List[UsuarioAdmin])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_owner_user),
):
    rows = (
        db.query(
            Usuario,
            func.coalesce(func.sum(UsoTokens.tokens_total), 0).label("tokens_total"),
        )
        .outerjoin(UsoTokens, UsoTokens.usuario_id == Usuario.id)
        .group_by(Usuario.id)
        .order_by(Usuario.criado_em.desc())
        .all()
    )
    result = []
    for user, tokens_total in rows:
        result.append(
            UsuarioAdmin(
                id=user.id,
                email=user.email,
                nome=user.nome,
                is_active=user.is_active,
                is_owner=user.is_owner,
                tokens_total=tokens_total,
                criado_em=user.criado_em,
            )
        )
    return result


@router.patch("/usuarios/{usuario_id}/ativar", response_model=UsuarioAdmin)
def ativar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_owner_user),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    user.is_active = True
    db.commit()
    db.refresh(user)
    tokens_total = (
        db.query(func.coalesce(func.sum(UsoTokens.tokens_total), 0))
        .filter(UsoTokens.usuario_id == usuario_id)
        .scalar()
    )
    return UsuarioAdmin(
        id=user.id, email=user.email, nome=user.nome,
        is_active=user.is_active, is_owner=user.is_owner,
        tokens_total=tokens_total, criado_em=user.criado_em,
    )


@router.patch("/usuarios/{usuario_id}/desativar", response_model=UsuarioAdmin)
def desativar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    owner: Usuario = Depends(get_owner_user),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if user.id == owner.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner não pode desativar a si mesmo")
    user.is_active = False
    db.commit()
    db.refresh(user)
    tokens_total = (
        db.query(func.coalesce(func.sum(UsoTokens.tokens_total), 0))
        .filter(UsoTokens.usuario_id == usuario_id)
        .scalar()
    )
    return UsuarioAdmin(
        id=user.id, email=user.email, nome=user.nome,
        is_active=user.is_active, is_owner=user.is_owner,
        tokens_total=tokens_total, criado_em=user.criado_em,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_owner_user),
):
    now = datetime.now(timezone.utc)
    hoje_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
    semana_inicio = hoje_inicio - timedelta(days=7)
    mes_inicio = hoje_inicio - timedelta(days=30)

    total_usuarios = db.query(func.count(Usuario.id)).scalar() or 0
    usuarios_ativos = db.query(func.count(Usuario.id)).filter(Usuario.is_active == True).scalar() or 0
    usuarios_aguardando = db.query(func.count(Usuario.id)).filter(Usuario.is_active == False).scalar() or 0

    def _tokens_desde(desde: datetime) -> int:
        return (
            db.query(func.coalesce(func.sum(UsoTokens.tokens_total), 0))
            .filter(UsoTokens.criado_em >= desde)
            .scalar()
        ) or 0

    def _media_tipo(tipo: str) -> float:
        return (
            db.query(func.avg(UsoTokens.tokens_total))
            .filter(UsoTokens.tipo == tipo)
            .scalar()
        ) or 0.0

    def _stats_tipo(tipo: str) -> EstatsFaseAdmin:
        rows = (
            db.query(UsoTokens.tokens_total)
            .filter(UsoTokens.tipo == tipo)
            .order_by(UsoTokens.tokens_total)
            .all()
        )
        values = [r.tokens_total or 0 for r in rows]
        n = len(values)
        if n == 0:
            return EstatsFaseAdmin(total_chamadas=0, media=0.0, mediana=0.0, variancia=0.0, minimo=0, maximo=0)
        media = sum(values) / n
        mid = n // 2
        mediana = float(values[mid]) if n % 2 == 1 else (values[mid - 1] + values[mid]) / 2.0
        variancia = sum((v - media) ** 2 for v in values) / n
        return EstatsFaseAdmin(
            total_chamadas=n,
            media=round(media, 2),
            mediana=round(mediana, 2),
            variancia=round(variancia, 2),
            minimo=values[0],
            maximo=values[-1],
        )

    tokens_hoje = _tokens_desde(hoje_inicio)
    tokens_semana = _tokens_desde(semana_inicio)
    tokens_mes = _tokens_desde(mes_inicio)
    tokens_total = _tokens_desde(datetime.min.replace(tzinfo=timezone.utc))

    media_etp = _media_tipo("etp")
    media_tr = _media_tipo("tr")
    media_pesquisa = _media_tipo("pesquisa")
    media_analise = _media_tipo("analise")

    # Tokens por dia — últimos 30 dias (uma query GROUP BY)
    tokens_dia_rows = (
        db.query(
            func.date(UsoTokens.criado_em).label("dia"),
            func.sum(UsoTokens.tokens_total).label("total"),
        )
        .filter(UsoTokens.criado_em >= mes_inicio)
        .group_by(func.date(UsoTokens.criado_em))
        .order_by(func.date(UsoTokens.criado_em))
        .all()
    )
    tokens_por_dia = [TokensPorDia(data=str(r.dia), total=r.total or 0) for r in tokens_dia_rows]

    # Tokens por tipo
    tokens_tipo_rows = (
        db.query(
            UsoTokens.tipo,
            func.sum(UsoTokens.tokens_total).label("total"),
            func.avg(UsoTokens.tokens_total).label("media"),
        )
        .group_by(UsoTokens.tipo)
        .all()
    )
    tokens_por_tipo = [
        TokensPorTipo(tipo=r.tipo, total=r.total or 0, media=float(r.media or 0))
        for r in tokens_tipo_rows
    ]

    # Top 10 usuários por consumo
    top_rows = (
        db.query(
            Usuario.email,
            Usuario.nome,
            func.coalesce(func.sum(UsoTokens.tokens_total), 0).label("tokens_total"),
        )
        .outerjoin(UsoTokens, UsoTokens.usuario_id == Usuario.id)
        .group_by(Usuario.id, Usuario.email, Usuario.nome)
        .order_by(func.coalesce(func.sum(UsoTokens.tokens_total), 0).desc())
        .limit(10)
        .all()
    )
    top_usuarios = [TopUsuario(email=r.email, nome=r.nome, tokens_total=r.tokens_total) for r in top_rows]

    stats_perguntas_global = _stats_tipo("perguntas_contratacao")
    stats_bcc_global = _stats_tipo("bcc_contratacao")

    return DashboardResponse(
        total_usuarios=total_usuarios,
        usuarios_ativos=usuarios_ativos,
        usuarios_aguardando=usuarios_aguardando,
        tokens_hoje=tokens_hoje,
        tokens_semana=tokens_semana,
        tokens_mes=tokens_mes,
        tokens_total=tokens_total,
        media_tokens_etp=float(media_etp),
        media_tokens_tr=float(media_tr),
        media_tokens_pesquisa=float(media_pesquisa),
        media_tokens_analise=float(media_analise),
        tokens_por_dia=tokens_por_dia,
        tokens_por_tipo=tokens_por_tipo,
        top_usuarios=top_usuarios,
        stats_perguntas_global=stats_perguntas_global,
        stats_bcc_global=stats_bcc_global,
    )
