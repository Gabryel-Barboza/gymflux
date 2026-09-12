"""fase 4.3 credenciais aluno (senha_hash + cartao_id)

Revision ID: 3f9a2c1bd4e5
Revises: 8c81436e0086
Create Date: 2026-09-12

Autenticação estilo SCA: senha numérica (só hash com salt, nunca texto)
+ cartão. Não altera regras RB01-RB05 nem migrations aplicadas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f9a2c1bd4e5"
down_revision: str | Sequence[str] | None = "8c81436e0086"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("alunos", sa.Column("senha_hash", sa.String(160), nullable=True))
    op.add_column("alunos", sa.Column("cartao_id", sa.String(32), nullable=True))
    op.create_index("ix_alunos_cartao_id", "alunos", ["cartao_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_alunos_cartao_id", table_name="alunos")
    op.drop_column("alunos", "cartao_id")
    op.drop_column("alunos", "senha_hash")
