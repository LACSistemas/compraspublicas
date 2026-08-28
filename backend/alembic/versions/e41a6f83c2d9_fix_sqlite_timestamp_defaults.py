"""Replace non-portable timestamp defaults in existing databases.

Revision ID: e41a6f83c2d9
Revises: d89f7a2c4e10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e41a6f83c2d9"
down_revision: str | None = "d89f7a2c4e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in inspector.get_table_names():
        columns = [
            column
            for column in inspector.get_columns(table_name)
            if "now()" in str(column.get("default") or "").lower()
        ]
        if not columns:
            continue

        batch_options = {"recreate": "always"} if bind.dialect.name == "sqlite" else {}
        with op.batch_alter_table(table_name, **batch_options) as batch_op:
            for column in columns:
                batch_op.alter_column(
                    column["name"],
                    existing_type=column["type"],
                    existing_nullable=column["nullable"],
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                )


def downgrade() -> None:
    # `CURRENT_TIMESTAMP` is valid on every supported database. Reintroducing
    # `now()` would make SQLite writes fail again, so this data repair is kept.
    pass
