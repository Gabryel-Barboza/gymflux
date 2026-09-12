"""AcessoLogModel — SQLAlchemy 2.0 Typed."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gymflux.infra.db import Base


class AcessoLogModel(Base):
    __tablename__ = "acesso_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    aluno_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=True, index=True
    )
    funcionario_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("funcionarios.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    direcao: Mapped[str] = mapped_column(String(10), nullable=False)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(40), nullable=True, default=None)
    detalhes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    catraca_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    timeout: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<AcessoLogModel id={self.id} aluno={self.aluno_id} res={self.resultado}>"
