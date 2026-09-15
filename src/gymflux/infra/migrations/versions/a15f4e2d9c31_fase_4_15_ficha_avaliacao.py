"""Fase 4.15: ficha de avaliação física + saúde.

Revision ID: a15f4e2d9c31
Revises: f4a1b2c3d9e0
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a15f4e2d9c31"
down_revision: str | Sequence[str] | None = "f4a1b2c3d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cria tabela avaliacoes_fisicas."""
    op.create_table(
        "avaliacoes_fisicas",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "aluno_id",
            sa.String(length=36),
            sa.ForeignKey("alunos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("data", sa.Date(), nullable=False, index=True),
        sa.Column("peso_kg", sa.Float(), nullable=True),
        sa.Column("altura_cm", sa.Float(), nullable=True),
        sa.Column("gordura_pct", sa.Float(), nullable=True),
        sa.Column("medidas", sa.Text(), nullable=True),
        sa.Column("problemas_saude", sa.Text(), nullable=True),
        sa.Column("restricoes", sa.Text(), nullable=True),
        sa.Column("medicamentos", sa.Text(), nullable=True),
        sa.Column("contato_emergencia", sa.Text(), nullable=True),
    )
    with op.batch_alter_table("avaliacoes_fisicas") as batch:
        batch.create_index("ix_avaliacoes_aluno_data", ["aluno_id", "data"])


def downgrade() -> None:
    """Remove tabela."""
    op.drop_table("avaliacoes_fisicas")
