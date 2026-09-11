"""PlanoModel — SQLAlchemy 2.0 Typed."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from gymflow.infra.db import Base


class PlanoModel(Base):
    __tablename__ = "planos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    duracao_dias: Mapped[int] = mapped_column(nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tolerancia_dias: Mapped[int] = mapped_column(nullable=False, default=3)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="MENSAL")

    def __repr__(self) -> str:
        return f"<PlanoModel id={self.id} nome={self.nome} duracao={self.duracao_dias}>"
