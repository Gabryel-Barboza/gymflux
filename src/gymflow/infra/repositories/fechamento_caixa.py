"""FechamentoCaixaRepository — Protocol + SQLAlchemy impl + Memória."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from gymflow.core.caixa import FechamentoCaixa
from gymflow.infra.models.fechamento_caixa import FechamentoCaixaModel


class FechamentoCaixaRepository(Protocol):
    def salvar(self, fechamento: FechamentoCaixa) -> FechamentoCaixa: ...
    def buscar_por_mes(self, mes: str) -> FechamentoCaixa | None: ...
    def listar(self) -> list[FechamentoCaixa]: ...
    def remover(self, fechamento_id: str) -> None: ...
    def total(self) -> int: ...


def _model_to_domain(m: FechamentoCaixaModel) -> FechamentoCaixa:
    return FechamentoCaixa(
        id=m.id,
        mes=m.mes,
        total=Decimal(str(m.total)),
        fechado_em=m.fechado_em,
    )


def _domain_to_model(f: FechamentoCaixa) -> FechamentoCaixaModel:
    return FechamentoCaixaModel(
        id=f.id,
        mes=f.mes,
        total=Decimal(str(f.total)),
        fechado_em=f.fechado_em,
    )


class FechamentoCaixaRepositorySQLAlchemy:
    def __init__(self, session: Session) -> None:
        self.session = session

    def salvar(self, fechamento: FechamentoCaixa) -> FechamentoCaixa:
        existing = self.session.get(FechamentoCaixaModel, fechamento.id)
        if existing is None:
            self.session.add(_domain_to_model(fechamento))
        else:
            existing.mes = fechamento.mes
            existing.total = Decimal(str(fechamento.total))
            existing.fechado_em = fechamento.fechado_em
        self.session.flush()
        return fechamento

    def buscar_por_mes(self, mes: str) -> FechamentoCaixa | None:
        stmt = select(FechamentoCaixaModel).where(FechamentoCaixaModel.mes == mes.strip())
        m = self.session.execute(stmt).scalars().first()
        return _model_to_domain(m) if m else None

    def listar(self) -> list[FechamentoCaixa]:
        stmt = select(FechamentoCaixaModel)
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def remover(self, fechamento_id: str) -> None:
        m = self.session.get(FechamentoCaixaModel, fechamento_id)
        if m:
            self.session.delete(m)
            self.session.flush()

    def total(self) -> int:
        stmt = select(FechamentoCaixaModel)
        return len(self.session.execute(stmt).scalars().all())

    def limpar(self) -> None:
        self.session.query(FechamentoCaixaModel).delete()
        self.session.flush()


class FechamentoCaixaRepositoryMemoria:
    def __init__(self) -> None:
        self._fechamentos: dict[str, FechamentoCaixa] = {}

    def salvar(self, fechamento: FechamentoCaixa) -> FechamentoCaixa:
        self._fechamentos[fechamento.id] = fechamento
        return fechamento

    def buscar_por_mes(self, mes: str) -> FechamentoCaixa | None:
        for f in self._fechamentos.values():
            if f.mes == mes.strip():
                return f
        return None

    def listar(self) -> list[FechamentoCaixa]:
        return list(self._fechamentos.values())

    def remover(self, fechamento_id: str) -> None:
        self._fechamentos.pop(fechamento_id, None)

    def total(self) -> int:
        return len(self._fechamentos)

    def limpar(self) -> None:
        self._fechamentos.clear()
