"""fase 4.5 fechamento mensal do caixa

Revision ID: 9a0cf12f3688
Revises: 3f9a2c1bd4e5
Create Date: 2026-09-12

Tabela `fechamentos_caixa` (mes único, total recebido, fechado_em).
Não altera migrations aplicadas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a0cf12f3688"
down_revision: str | Sequence[str] | None = "3f9a2c1bd4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "fechamentos_caixa",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("mes", sa.String(7), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("fechado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mes"),
    )
    op.create_index("ix_fechamentos_caixa_mes", "fechamentos_caixa", ["mes"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_fechamentos_caixa_mes", table_name="fechamentos_caixa")
    op.drop_table("fechamentos_caixa")
