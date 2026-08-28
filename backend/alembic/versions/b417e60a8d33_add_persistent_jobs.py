"""add persistent jobs

Revision ID: b417e60a8d33
Revises: 7a51e820df02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b417e60a8d33"
down_revision: Union[str, Sequence[str], None] = "7a51e820df02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("jobs_execucao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contratacao_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("referencia_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("etapa", sa.String(100), nullable=False),
        sa.Column("tentativa", sa.Integer(), nullable=False),
        sa.Column("max_tentativas", sa.Integer(), nullable=False),
        sa.Column("checkpoint_json", sa.Text(), nullable=False),
        sa.Column("erro_mensagem", sa.Text()),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["contratacao_id"], ["contratacoes.id"]),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_jobs_execucao_id", "jobs_execucao", ["id"])
    op.create_index("ix_jobs_contratacao_status", "jobs_execucao", ["contratacao_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_jobs_contratacao_status", table_name="jobs_execucao")
    op.drop_table("jobs_execucao")
