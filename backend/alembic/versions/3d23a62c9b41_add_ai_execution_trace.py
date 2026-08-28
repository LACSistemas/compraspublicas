"""add AI execution trace

Revision ID: 3d23a62c9b41
Revises: c51d8b93a210
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3d23a62c9b41"
down_revision: Union[str, Sequence[str], None] = "c51d8b93a210"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("execucoes_ia",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contratacao_id", sa.Integer(), nullable=False),
        sa.Column("plano_id", sa.Integer(), nullable=True),
        sa.Column("fase", sa.String(50), nullable=False),
        sa.Column("hash_entrada", sa.String(64), nullable=False),
        sa.Column("modelo", sa.String(100)),
        sa.Column("prompt_versao", sa.String(50), nullable=False),
        sa.Column("prompt_texto", sa.Text(), nullable=False),
        sa.Column("entrada_json", sa.Text(), nullable=False),
        sa.Column("catalogo_json", sa.Text()),
        sa.Column("saida_json", sa.Text()),
        sa.Column("tokens_input", sa.Integer()),
        sa.Column("tokens_output", sa.Integer()),
        sa.Column("tokens_total", sa.Integer()),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("erro_mensagem", sa.Text()),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["contratacao_id"], ["contratacoes.id"]),
        sa.ForeignKeyConstraint(["plano_id"], ["planos_investigacao.id"]),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_execucoes_ia_id", "execucoes_ia", ["id"])
    op.create_index("ix_execucoes_ia_hash_entrada", "execucoes_ia", ["hash_entrada"])
    op.create_index("ix_execucoes_ia_fase_hash", "execucoes_ia", ["fase", "hash_entrada"])


def downgrade() -> None:
    op.drop_index("ix_execucoes_ia_fase_hash", table_name="execucoes_ia")
    op.drop_table("execucoes_ia")
