"""FuncionarioModel — SQLAlchemy 2.0 Typed."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from gymflux.infra.db import Base


class FuncionarioModel(Base):
    __tablename__ = "funcionarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    senha_hash: Mapped[str | None] = mapped_column(String(160), nullable=True, default=None)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    horarios: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    dias: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    foto: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<FuncionarioModel id={self.id} nome={self.nome} ativo={self.ativo}>"
