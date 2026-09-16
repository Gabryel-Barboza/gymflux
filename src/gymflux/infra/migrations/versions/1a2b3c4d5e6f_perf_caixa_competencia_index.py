"""perf caixa: índice em pagamentos.competencia (pushdown 4.16).

Revision ID: 1a2b3c4d5e6f
Revises: f4a1b2c3d9e0
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "1a2b3c4d5e6f"
down_revision: str | Sequence[str] | None = "a15f4e2d9c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    try:
        from sqlalchemy import inspect

        insp = inspect(bind)
        idxs = [i["name"] for i in insp.get_indexes("pagamentos")]
        if "ix_pagamentos_competencia" in idxs:
            return
    except Exception:
        pass
    with op.batch_alter_table("pagamentos") as batch:
        batch.create_index("ix_pagamentos_competencia", ["competencia"])


def downgrade() -> None:
    bind = op.get_bind()
    try:
        from sqlalchemy import inspect

        insp = inspect(bind)
        idxs = [i["name"] for i in insp.get_indexes("pagamentos")]
        if "ix_pagamentos_competencia" not in idxs:
            return
    except Exception:
        pass
    with op.batch_alter_table("pagamentos") as batch:
        batch.drop_index("ix_pagamentos_competencia")
