"""AlunoModel — SQLAlchemy 2.0 Typed."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from gymflux.infra.db import Base


class AlunoModel(Base):
    __tablename__ = "alunos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(14), unique=True, index=True, nullable=True)
    data_nasc: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ATIVO")
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    endereco: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    bloqueado_manual: Mapped[bool] = mapped_column(nullable=False, default=False)
    # PIN de catraca em TEXTO (Fase 4.8, decisão do dono — risco aceito).
    senha: Mapped[str | None] = mapped_column(String(8), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AlunoModel id={self.id} nome={self.nome} cpf={self.cpf}>"
