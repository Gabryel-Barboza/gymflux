"""fase 4.6 acesso_logs.funcionario_id (antifraude)

Revision ID: a41f0c9d2e7b
Revises: f7e9182ac1bb
Create Date: 2026-09-12

- adiciona ``funcionario_id`` nullable + FK p/ funcionarios (SET NULL);
- torna ``aluno_id`` nullable (tentativa de funcionário não tem aluno).
Não altera migrations aplicadas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a41f0c9d2e7b"
down_revision: str | Sequence[str] | None = "f7e9182ac1bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("acesso_logs") as batch:
        batch.add_column(sa.Column("funcionario_id", sa.String(36), nullable=True))
        batch.create_index("ix_acesso_logs_funcionario_id", ["funcionario_id"])
        batch.create_foreign_key(
            "fk_acesso_logs_funcionario_id",
            "funcionarios",
            ["funcionario_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.alter_column("aluno_id", existing_type=sa.String(36), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("acesso_logs") as batch:
        batch.drop_constraint("fk_acesso_logs_funcionario_id", type_="foreignkey")
        batch.drop_index("ix_acesso_logs_funcionario_id")
        batch.drop_column("funcionario_id")
        batch.alter_column("aluno_id", existing_type=sa.String(36), nullable=False)
