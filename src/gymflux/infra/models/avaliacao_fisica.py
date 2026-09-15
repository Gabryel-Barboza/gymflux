"""AvaliacaoFisicaModel — SQLAlchemy 2.0 Typed."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gymflux.infra.db import Base


class AvaliacaoFisicaModel(Base):
    __tablename__ = "avaliacoes_fisicas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    aluno_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    peso_kg: Mapped[float | None] = mapped_column(nullable=True)
    altura_cm: Mapped[float | None] = mapped_column(nullable=True)
    gordura_pct: Mapped[float | None] = mapped_column(nullable=True)
    medidas: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    problemas_saude: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    restricoes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    medicamentos: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    contato_emergencia: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"<AvaliacaoFisicaModel id={self.id} aluno={self.aluno_id} data={self.data}>"
