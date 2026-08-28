"""add knowledge robustness dimensions

Revision ID: 7a51e820df02
Revises: 5f4c92ab107e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7a51e820df02"
down_revision: Union[str, Sequence[str], None] = "5f4c92ab107e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conhecimentos_cards") as batch_op:
        batch_op.add_column(sa.Column("dimensoes_robustez_json", sa.Text(),
            nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("conhecimentos_cards") as batch_op:
        batch_op.drop_column("dimensoes_robustez_json")
