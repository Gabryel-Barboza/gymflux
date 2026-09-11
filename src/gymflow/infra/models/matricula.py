"""MatriculaModel — SQLAlchemy 2.0 Typed."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from gymflow.infra.db import Base


class MatriculaModel(Base):
    __tablename__ = "matriculas"
    __table_args__ = (Index("ix_matriculas_aluno_ativa", "aluno_id", "ativa"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    aluno_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("alunos.id", ondelete="CASCADE"), nullable=False
    )
    plano_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("planos.id", ondelete="RESTRICT"), nullable=False
    )
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fim: Mapped[date] = mapped_column(Date, nullable=False)
    ativa: Mapped[bool] = mapped_column(nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<MatriculaModel id={self.id} aluno={self.aluno_id} plano={self.plano_id}>"
