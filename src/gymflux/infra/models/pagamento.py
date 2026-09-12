"""PagamentoModel — SQLAlchemy 2.0 Typed."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from gymflux.infra.db import Base


class PagamentoModel(Base):
    __tablename__ = "pagamentos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    aluno_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # coluna no banco chama "pagamento" (spec), atributo python data_pagamento p/ compat domínio
    data_pagamento: Mapped[date | None] = mapped_column(
        "pagamento", Date, nullable=True, default=None
    )
    forma: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    competencia: Mapped[str | None] = mapped_column(String(7), nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<PagamentoModel id={self.id} aluno={self.aluno_id} venc={self.vencimento}>"
