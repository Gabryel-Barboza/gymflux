"""FechamentoCaixaModel — SQLAlchemy 2.0 Typed."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from gymflux.infra.db import Base


class FechamentoCaixaModel(Base):
    __tablename__ = "fechamentos_caixa"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    mes: Mapped[str] = mapped_column(String(7), nullable=False, unique=True, index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fechado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<FechamentoCaixaModel id={self.id} mes={self.mes} total={self.total}>"
