"""fase 4.5 funcionarios (entrada indefinida, senha numerica)

Revision ID: f7e9182ac1bb
Revises: 9a0cf12f3688
Create Date: 2026-09-12

Tabela `funcionarios` (id, nome, senha_hash, ativo).
Não altera migrations aplicadas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7e9182ac1bb"
down_revision: str | Sequence[str] | None = "9a0cf12f3688"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "funcionarios",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("senha_hash", sa.String(160), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("funcionarios")
