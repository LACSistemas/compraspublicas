"""add investigation plan and catalogs

Revision ID: c51d8b93a210
Revises: 99d7acabe483
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c51d8b93a210"
down_revision: Union[str, Sequence[str], None] = "99d7acabe483"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pesquisas") as batch_op:
        batch_op.add_column(sa.Column("contratacao_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_pesquisa_contratacao", "contratacoes", ["contratacao_id"], ["id"])
    op.create_table("cards_decisao_catalogo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(300), nullable=False),
        sa.Column("pergunta_controle", sa.Text(), nullable=False),
        sa.Column("base_legal_json", sa.Text(), nullable=False),
        sa.Column("criterios_json", sa.Text(), nullable=False),
        sa.Column("evidencias_aceitas_json", sa.Text(), nullable=False),
        sa.Column("artefatos_impactados_json", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("codigo"))
    op.create_index("ix_cards_decisao_catalogo_id", "cards_decisao_catalogo", ["id"])
    op.create_index("ix_cards_decisao_catalogo_codigo", "cards_decisao_catalogo", ["codigo"], unique=True)
    op.create_table("informacoes_catalogo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(30), nullable=False),
        sa.Column("nome", sa.String(300), nullable=False),
        sa.Column("objetivo", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("obrigatoriedade", sa.String(20), nullable=False),
        sa.Column("estrategia_preferencial", sa.String(30), nullable=False),
        sa.Column("dominio_json", sa.Text(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("codigo"))
    op.create_index("ix_informacoes_catalogo_id", "informacoes_catalogo", ["id"])
    op.create_index("ix_informacoes_catalogo_codigo", "informacoes_catalogo", ["codigo"], unique=True)
    op.create_table("cards_informacoes",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("informacao_id", sa.Integer(), nullable=False), sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("obrigatoria", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards_decisao_catalogo.id"]),
        sa.ForeignKeyConstraint(["informacao_id"], ["informacoes_catalogo.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "informacao_id", name="uq_card_informacao"))
    op.create_table("planos_investigacao",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("contratacao_id", sa.Integer(), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["contratacao_id"], ["contratacoes.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contratacao_id", "versao", name="uq_plano_contratacao_versao"))
    op.create_index("ix_planos_investigacao_id", "planos_investigacao", ["id"])
    op.create_table("cards_dependencias",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("depende_de_card_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards_decisao_catalogo.id"]),
        sa.ForeignKeyConstraint(["depende_de_card_id"], ["cards_decisao_catalogo.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "depende_de_card_id", name="uq_card_dependencia"))
    op.create_table("criterios_cards_catalogo",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(30), nullable=False), sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("peso", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards_decisao_catalogo.id"]),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("codigo"))
    op.create_index("ix_criterios_cards_catalogo_id", "criterios_cards_catalogo", ["id"])
    op.create_table("plano_cards_decisao",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("plano_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False), sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("aplicavel", sa.Boolean(), nullable=False),
        sa.Column("justificativa_dispensa", sa.Text()), sa.Column("robustez_pct", sa.Integer(), nullable=False),
        sa.Column("dispensa_status", sa.String(30)),
        sa.Column("dispensa_revisada_por_usuario_id", sa.Integer()),
        sa.Column("dispensa_revisada_em", sa.DateTime()),
        sa.ForeignKeyConstraint(["plano_id"], ["planos_investigacao.id"]),
        sa.ForeignKeyConstraint(["card_id"], ["cards_decisao_catalogo.id"]), sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["dispensa_revisada_por_usuario_id"], ["usuarios.id"]),
        sa.UniqueConstraint("plano_id", "card_id", name="uq_plano_card"))
    op.create_index("ix_plano_cards_decisao_id", "plano_cards_decisao", ["id"])
    op.create_table("plano_informacoes",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("plano_card_id", sa.Integer(), nullable=False),
        sa.Column("informacao_id", sa.Integer(), nullable=False), sa.Column("estrategia", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("justificativa_estrategia", sa.Text()),
        sa.Column("valor_json", sa.Text()), sa.Column("origem", sa.String(50)),
        sa.Column("confianca", sa.String(20)),
        sa.ForeignKeyConstraint(["plano_card_id"], ["plano_cards_decisao.id"]),
        sa.ForeignKeyConstraint(["informacao_id"], ["informacoes_catalogo.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plano_card_id", "informacao_id", name="uq_plano_card_informacao"))
    op.create_index("ix_plano_informacoes_id", "plano_informacoes", ["id"])
    op.create_table("evidencias_plano",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plano_informacao_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False), sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("conteudo_json", sa.Text(), nullable=False), sa.Column("origem", sa.String(100), nullable=False),
        sa.Column("metodo_obtencao", sa.String(50), nullable=False), sa.Column("confianca", sa.String(20), nullable=False),
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
    op.create_table("evidencias_criterios",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("evidencia_id", sa.Integer(), nullable=False),
        sa.Column("criterio_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["evidencia_id"], ["evidencias_plano.id"]),
        sa.ForeignKeyConstraint(["criterio_id"], ["criterios_cards_catalogo.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidencia_id", "criterio_id", name="uq_evidencia_criterio"))
    op.create_table("conhecimentos_cards",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("plano_card_id", sa.Integer(), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False), sa.Column("conclusao", sa.Text(), nullable=False),
        sa.Column("motivacao", sa.Text(), nullable=False), sa.Column("fundamentacao_json", sa.Text(), nullable=False),
        sa.Column("riscos_json", sa.Text(), nullable=False), sa.Column("recomendacoes_json", sa.Text(), nullable=False),
        sa.Column("evidencias_json", sa.Text(), nullable=False), sa.Column("cobertura_criterios_json", sa.Text(), nullable=False),
        sa.Column("robustez_pct", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("aprovado_por_usuario_id", sa.Integer()),
        sa.Column("aprovado_em", sa.DateTime()), sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["plano_card_id"], ["plano_cards_decisao.id"]),
        sa.ForeignKeyConstraint(["aprovado_por_usuario_id"], ["usuarios.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plano_card_id", "versao", name="uq_conhecimento_card_versao"))
    op.create_index("ix_conhecimentos_cards_id", "conhecimentos_cards", ["id"])
    op.create_table("snapshots_bcc",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("contratacao_id", sa.Integer(), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False), sa.Column("dados_json", sa.Text(), nullable=False),
        sa.Column("hash_conteudo", sa.String(64), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["contratacao_id"], ["contratacoes.id"]), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contratacao_id", "versao", name="uq_snapshot_bcc_versao"))
    op.create_index("ix_snapshots_bcc_id", "snapshots_bcc", ["id"])
    with op.batch_alter_table("perguntas_contratacao") as batch_op:
        batch_op.add_column(sa.Column("plano_informacao_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_pergunta_plano_informacao", "plano_informacoes", ["plano_informacao_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("perguntas_contratacao") as batch_op:
        batch_op.drop_constraint("fk_pergunta_plano_informacao", type_="foreignkey")
        batch_op.drop_column("plano_informacao_id")
    for table in ("snapshots_bcc", "conhecimentos_cards", "evidencias_criterios", "evidencias_plano", "plano_informacoes", "plano_cards_decisao", "criterios_cards_catalogo", "cards_dependencias", "planos_investigacao", "cards_informacoes", "informacoes_catalogo", "cards_decisao_catalogo"):
        op.drop_table(table)
    with op.batch_alter_table("pesquisas") as batch_op:
        batch_op.drop_constraint("fk_pesquisa_contratacao", type_="foreignkey")
        batch_op.drop_column("contratacao_id")
