"""repair databases created by an early partial investigation migration

Revision ID: 5f4c92ab107e
Revises: 3d23a62c9b41
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "5f4c92ab107e"
down_revision: Union[str, Sequence[str], None] = "3d23a62c9b41"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()
    if "contratacao_id" not in _columns("pesquisas"):
        with op.batch_alter_table("pesquisas") as batch_op:
            batch_op.add_column(sa.Column("contratacao_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_pesquisa_contratacao", "contratacoes",
                ["contratacao_id"], ["id"])

    plano_card_columns = _columns("plano_cards_decisao")
    with op.batch_alter_table("plano_cards_decisao") as batch_op:
        if "dispensa_status" not in plano_card_columns:
            batch_op.add_column(sa.Column("dispensa_status", sa.String(30)))
        if "dispensa_revisada_por_usuario_id" not in plano_card_columns:
            batch_op.add_column(sa.Column("dispensa_revisada_por_usuario_id", sa.Integer()))
            batch_op.create_foreign_key("fk_plano_card_revisor", "usuarios",
                ["dispensa_revisada_por_usuario_id"], ["id"])
        if "dispensa_revisada_em" not in plano_card_columns:
            batch_op.add_column(sa.Column("dispensa_revisada_em", sa.DateTime()))

    if "criterios_cards_catalogo" not in tables:
        op.create_table("criterios_cards_catalogo",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("card_id", sa.Integer(), nullable=False),
            sa.Column("codigo", sa.String(30), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=False),
            sa.Column("peso", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["card_id"], ["cards_decisao_catalogo.id"]),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("codigo"))
        op.create_index("ix_criterios_cards_catalogo_id", "criterios_cards_catalogo", ["id"])

    if "plano_informacoes" not in tables:
        op.create_table("plano_informacoes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("plano_card_id", sa.Integer(), nullable=False),
            sa.Column("informacao_id", sa.Integer(), nullable=False),
            sa.Column("estrategia", sa.String(30), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("justificativa_estrategia", sa.Text()),
            sa.Column("valor_json", sa.Text()), sa.Column("origem", sa.String(50)),
            sa.Column("confianca", sa.String(20)),
            sa.ForeignKeyConstraint(["plano_card_id"], ["plano_cards_decisao.id"]),
            sa.ForeignKeyConstraint(["informacao_id"], ["informacoes_catalogo.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("plano_card_id", "informacao_id", name="uq_plano_card_informacao"))
        op.create_index("ix_plano_informacoes_id", "plano_informacoes", ["id"])

    if "plano_informacao_id" not in _columns("perguntas_contratacao"):
        with op.batch_alter_table("perguntas_contratacao") as batch_op:
            batch_op.add_column(sa.Column("plano_informacao_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_pergunta_plano_informacao", "plano_informacoes",
                ["plano_informacao_id"], ["id"])

    tables = _tables()
    if "evidencias_plano" not in tables:
        op.create_table("evidencias_plano",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("plano_informacao_id", sa.Integer(), nullable=False),
            sa.Column("tipo", sa.String(30), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=False),
            sa.Column("conteudo_json", sa.Text(), nullable=False),
            sa.Column("origem", sa.String(100), nullable=False),
            sa.Column("metodo_obtencao", sa.String(50), nullable=False),
            sa.Column("confianca", sa.String(20), nullable=False),
            sa.Column("hash_conteudo", sa.String(64), nullable=False),
            sa.Column("status_validacao", sa.String(30), nullable=False),
            sa.Column("estado", sa.String(30), nullable=False),
            sa.Column("substitui_evidencia_id", sa.Integer(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["plano_informacao_id"], ["plano_informacoes.id"]),
            sa.ForeignKeyConstraint(["substitui_evidencia_id"], ["evidencias_plano.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("plano_informacao_id", "hash_conteudo", name="uq_evidencia_info_hash"))
        op.create_index("ix_evidencias_plano_id", "evidencias_plano", ["id"])

    if "evidencias_criterios" not in tables:
        op.create_table("evidencias_criterios",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("evidencia_id", sa.Integer(), nullable=False),
            sa.Column("criterio_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["evidencia_id"], ["evidencias_plano.id"]),
            sa.ForeignKeyConstraint(["criterio_id"], ["criterios_cards_catalogo.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("evidencia_id", "criterio_id", name="uq_evidencia_criterio"))

    if "conhecimentos_cards" not in tables:
        op.create_table("conhecimentos_cards",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("plano_card_id", sa.Integer(), nullable=False),
            sa.Column("versao", sa.Integer(), nullable=False),
            sa.Column("conclusao", sa.Text(), nullable=False),
            sa.Column("motivacao", sa.Text(), nullable=False),
            sa.Column("fundamentacao_json", sa.Text(), nullable=False),
            sa.Column("riscos_json", sa.Text(), nullable=False),
            sa.Column("recomendacoes_json", sa.Text(), nullable=False),
            sa.Column("evidencias_json", sa.Text(), nullable=False),
            sa.Column("cobertura_criterios_json", sa.Text(), nullable=False),
            sa.Column("robustez_pct", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("aprovado_por_usuario_id", sa.Integer()),
            sa.Column("aprovado_em", sa.DateTime()),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["plano_card_id"], ["plano_cards_decisao.id"]),
            sa.ForeignKeyConstraint(["aprovado_por_usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("plano_card_id", "versao", name="uq_conhecimento_card_versao"))
        op.create_index("ix_conhecimentos_cards_id", "conhecimentos_cards", ["id"])

    if "snapshots_bcc" not in tables:
        op.create_table("snapshots_bcc",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("contratacao_id", sa.Integer(), nullable=False),
            sa.Column("versao", sa.Integer(), nullable=False),
            sa.Column("dados_json", sa.Text(), nullable=False),
            sa.Column("hash_conteudo", sa.String(64), nullable=False),
            sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["contratacao_id"], ["contratacoes.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("contratacao_id", "versao", name="uq_snapshot_bcc_versao"))
        op.create_index("ix_snapshots_bcc_id", "snapshots_bcc", ["id"])


def downgrade() -> None:
    # Reparação de uma revisão histórica: as estruturas pertencem logicamente à c51d8b93a210.
    # A remoção continua sendo responsabilidade do downgrade daquela revisão.
    pass
