"""fase_4_14_created_at_aluno — garante coluna created_at (idempotente).

Revision ID: f4a1b2c3d9e0
Revises: ef0330e40ade
Create Date: 2026-09-14

Nota: AlunoModel já tem created_at com server_default, mas DBs criados via
alembic antes desta revisão não tinham a coluna (só via create_all). Esta
migração garante a coluna de forma idempotente.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a1b2c3d9e0"
down_revision: str | Sequence[str] | None = "ef0330e40ade"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema — adiciona created_at se ainda não existir."""
    bind = op.get_bind()
    try:
        from sqlalchemy import inspect

        insp = inspect(bind)
        cols = [c["name"] for c in insp.get_columns("alunos")]
        if "created_at" in cols:
            return
    except Exception:
        pass
    # SQLite não suporta NOT NULL sem default, usa server_default
    op.add_column(
        "alunos",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
    )
    # backfill se null
    import contextlib

    with contextlib.suppress(Exception):
        txt = sa.text("UPDATE alunos SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        op.execute(txt)


def downgrade() -> None:
    """Downgrade schema — remove created_at se existir."""
    bind = op.get_bind()
    try:
        from sqlalchemy import inspect

        insp = inspect(bind)
        cols = [c["name"] for c in insp.get_columns("alunos")]
        if "created_at" not in cols:
            return
    except Exception:
        pass
    with op.batch_alter_table("alunos") as batch:
        batch.drop_column("created_at")
