"""fase 4.8 senha visivel do aluno, sem cartao

Revision ID: b2c4d6e8f0a1
Revises: a41f0c9d2e7b
Create Date: 2026-09-12

- adiciona ``alunos.senha`` (texto, 4-8 dígitos — decisão do dono, risco aceito);
- remove ``alunos.cartao_id`` (+ índice único) e ``alunos.senha_hash``.
- DADOS: hashes PBKDF2+salt NÃO são reversíveis — a migração zera o campo
  (``senha`` nasce NULL p/ todos) e loga aviso; a recepção recadastra os
  PINs pelo perfil. Downgrade recria as colunas vazias (sem restaurar nada).
Não altera regras RB01-RB05, hardware nem migrations aplicadas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from loguru import logger

# revision identifiers, used by Alembic.
revision: str = "b2c4d6e8f0a1"
down_revision: str | Sequence[str] | None = "a41f0c9d2e7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("alunos") as batch:
        batch.add_column(sa.Column("senha", sa.String(8), nullable=True))
        batch.drop_index("ix_alunos_cartao_id")
        batch.drop_column("cartao_id")
        batch.drop_column("senha_hash")
    logger.warning(
        "[4.8] alunos.senha_hash/cartao_id removidos; senha nasce NULL "
        "(hashes não são recuperáveis) — recadastrar PINs pelo perfil"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("alunos") as batch:
        batch.add_column(sa.Column("senha_hash", sa.String(160), nullable=True))
        batch.add_column(sa.Column("cartao_id", sa.String(32), nullable=True))
        batch.create_index("ix_alunos_cartao_id", ["cartao_id"], unique=True)
        batch.drop_column("senha")
