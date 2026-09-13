"""fase 4.10 endereco aluno

Revision ID: d3e8f1a2c4b9
Revises: b2c4d6e8f0a1
Create Date: 2026-09-13

Adiciona coluna alunos.endereco (Text nullable).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e8f1a2c4b9"
down_revision: str | Sequence[str] | None = "b2c4d6e8f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("alunos") as batch:
        batch.add_column(sa.Column("endereco", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("alunos") as batch:
        batch.drop_column("endereco")
