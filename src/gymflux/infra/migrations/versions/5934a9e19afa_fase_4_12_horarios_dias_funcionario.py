"""fase 4.12 horarios/dias funcionario

Revision ID: 5934a9e19afa
Revises: d3e8f1a2c4b9
Create Date: 2026-09-13

Adiciona colunas funcionarios.horarios e funcionarios.dias (Text/String nullable).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5934a9e19afa"
down_revision: str | Sequence[str] | None = "d3e8f1a2c4b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("funcionarios") as batch:
        batch.add_column(sa.Column("horarios", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("dias", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("funcionarios") as batch:
        batch.drop_column("dias")
        batch.drop_column("horarios")
