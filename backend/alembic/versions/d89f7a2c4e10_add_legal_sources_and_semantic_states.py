"""add legal sources and semantic states

Revision ID: d89f7a2c4e10
Revises: b417e60a8d33
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d89f7a2c4e10"
down_revision: Union[str, Sequence[str], None] = "b417e60a8d33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("plano_informacoes") as batch_op:
        batch_op.add_column(sa.Column("estado_semantico", sa.String(30), nullable=False,
            server_default="nao_informado"))
    with op.batch_alter_table("conhecimentos_cards") as batch_op:
        batch_op.add_column(sa.Column("fontes_confirmadas_json", sa.Text(), nullable=False,
            server_default="[]"))
    op.create_table("fontes_juridicas",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False), sa.Column("titulo", sa.String(500), nullable=False),
        sa.Column("referencia", sa.String(300), nullable=False), sa.Column("url_oficial", sa.Text(), nullable=False),
        sa.Column("orgao_emissor", sa.String(200), nullable=False),
        sa.Column("confirmada", sa.Boolean(), nullable=False), sa.Column("metadados_json", sa.Text(), nullable=False),
        sa.Column("verificada_em", sa.DateTime()), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"))
    op.create_index("ix_fontes_juridicas_id", "fontes_juridicas", ["id"])
    op.create_index("ix_fontes_juridicas_codigo", "fontes_juridicas", ["codigo"], unique=True)
    op.create_table("cards_fontes_juridicas",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("fonte_id", sa.Integer(), nullable=False), sa.Column("dispositivo", sa.String(200), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards_decisao_catalogo.id"]),
        sa.ForeignKeyConstraint(["fonte_id"], ["fontes_juridicas.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "fonte_id", "dispositivo", name="uq_card_fonte_dispositivo"))


def downgrade() -> None:
    op.drop_table("cards_fontes_juridicas")
    op.drop_table("fontes_juridicas")
    with op.batch_alter_table("conhecimentos_cards") as batch_op:
        batch_op.drop_column("fontes_confirmadas_json")
    with op.batch_alter_table("plano_informacoes") as batch_op:
        batch_op.drop_column("estado_semantico")
