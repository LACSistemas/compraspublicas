"""add price research campaigns

Revision ID: f62c84d19a07
Revises: e41a6f83c2d9
"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "f62c84d19a07"
down_revision: str | None = "e41a6f83c2d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "campanhas_pesquisa_precos" not in tables:
        op.create_table("campanhas_pesquisa_precos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contratacao_id", sa.Integer(), sa.ForeignKey("contratacoes.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="planejada"),
        sa.Column("objeto_canonico_json", sa.Text(), nullable=False),
        sa.Column("max_consultas", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("resultado_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("erro_mensagem", sa.Text()),
        sa.Column("aprovado_por_usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id")),
        sa.Column("aprovado_em", sa.DateTime()),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("atualizado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_campanhas_pesquisa_precos_contratacao_id", "campanhas_pesquisa_precos", ["contratacao_id"])
    if "consultas_pesquisa_precos" not in tables:
        op.create_table("consultas_pesquisa_precos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campanha_id", sa.Integer(), sa.ForeignKey("campanhas_pesquisa_precos.id"), nullable=False),
        sa.Column("pesquisa_id", sa.Integer(), sa.ForeignKey("pesquisas.id")),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("termo", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("processos_encontrados", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processos_novos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erro_mensagem", sa.Text()),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_consultas_pesquisa_precos_campanha_id", "consultas_pesquisa_precos", ["campanha_id"])
    if "observacoes_precos" not in tables:
        op.create_table("observacoes_precos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campanha_id", sa.Integer(), sa.ForeignKey("campanhas_pesquisa_precos.id"), nullable=False),
        sa.Column("consulta_id", sa.Integer(), sa.ForeignKey("consultas_pesquisa_precos.id"), nullable=False),
        sa.Column("chave_fonte", sa.String(64), nullable=False),
        sa.Column("processo_url", sa.Text(), nullable=False),
        sa.Column("numero_processo", sa.String(200)), sa.Column("comprador", sa.String(500)),
        sa.Column("descricao_item", sa.Text(), nullable=False),
        sa.Column("quantidade", sa.String(100)), sa.Column("unidade", sa.String(100)),
        sa.Column("valor_unitario", sa.String(80), nullable=False),
        sa.Column("tipo_valor", sa.String(30), nullable=False, server_default="referencia"),
        sa.Column("aderencia_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comparavel", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("motivo_exclusao", sa.Text()), sa.Column("documento_origem", sa.Text()),
        sa.Column("status_validacao", sa.String(30), nullable=False, server_default="pendente"),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_observacoes_precos_campanha_id", "observacoes_precos", ["campanha_id"])
        op.create_index("ix_observacoes_precos_chave_fonte", "observacoes_precos", ["chave_fonte"], unique=True)


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for table in ("observacoes_precos", "consultas_pesquisa_precos", "campanhas_pesquisa_precos"):
        if table in tables:
            op.drop_table(table)
