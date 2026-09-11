"""PagamentoRepository — Protocol + SQLAlchemy."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from gymflow.core.pagamento import Pagamento
from gymflow.infra.models.pagamento import PagamentoModel


class PagamentoRepository(Protocol):
    def salvar(self, pagamento: Pagamento) -> Pagamento: ...
    def buscar_por_id(self, pagamento_id: str) -> Pagamento | None: ...
    def listar_por_aluno(self, aluno_id: str) -> list[Pagamento]: ...
    def listar(self) -> list[Pagamento]: ...
    def remover(self, pagamento_id: str) -> None: ...
    def total(self) -> int: ...


def _model_to_domain(m: PagamentoModel) -> Pagamento:
    return Pagamento(
        id=m.id,
        aluno_id=m.aluno_id,
        valor=Decimal(str(m.valor)),
        data_vencimento=m.vencimento,
        data_pagamento=m.data_pagamento,
        forma=m.forma,
        competencia=m.competencia,
    )


def _domain_to_model(p: Pagamento) -> PagamentoModel:
    return PagamentoModel(
        id=p.id,
        aluno_id=p.aluno_id,
        valor=Decimal(str(p.valor)),
        vencimento=p.data_vencimento,
        data_pagamento=p.data_pagamento,
        forma=str(p.forma) if p.forma else None,
        competencia=p.competencia,
    )


class PagamentoRepositorySQLAlchemy:
    def __init__(self, session: Session) -> None:
        self.session = session

    def salvar(self, pagamento: Pagamento) -> Pagamento:
        existing = self.session.get(PagamentoModel, pagamento.id)
        if existing is None:
            model = _domain_to_model(pagamento)
            self.session.add(model)
        else:
            existing.aluno_id = pagamento.aluno_id
            existing.valor = Decimal(str(pagamento.valor))
            existing.vencimento = pagamento.data_vencimento
            existing.data_pagamento = pagamento.data_pagamento
            existing.forma = str(pagamento.forma) if pagamento.forma else None
            existing.competencia = pagamento.competencia
        self.session.flush()
        return pagamento

    def buscar_por_id(self, pagamento_id: str) -> Pagamento | None:
        m = self.session.get(PagamentoModel, pagamento_id)
        return _model_to_domain(m) if m else None

    def listar_por_aluno(self, aluno_id: str) -> list[Pagamento]:
        stmt = select(PagamentoModel).where(PagamentoModel.aluno_id == aluno_id)
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def listar(self) -> list[Pagamento]:
        stmt = select(PagamentoModel)
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def remover(self, pagamento_id: str) -> None:
        m = self.session.get(PagamentoModel, pagamento_id)
        if m:
            self.session.delete(m)
            self.session.flush()

    def total(self) -> int:
        stmt = select(PagamentoModel)
        return len(self.session.execute(stmt).scalars().all())

    def limpar(self) -> None:
        self.session.query(PagamentoModel).delete()
        self.session.flush()


class PagamentoRepositoryMemoria:
    def __init__(self) -> None:
        self._pagamentos: dict[str, Pagamento] = {}

    def salvar(self, pagamento: Pagamento) -> Pagamento:
        self._pagamentos[pagamento.id] = pagamento
        return pagamento

    def buscar_por_id(self, pagamento_id: str) -> Pagamento | None:
        return self._pagamentos.get(pagamento_id)

    def listar_por_aluno(self, aluno_id: str) -> list[Pagamento]:
        return [p for p in self._pagamentos.values() if p.aluno_id == aluno_id]

    def listar(self) -> list[Pagamento]:
        return list(self._pagamentos.values())

    def remover(self, pagamento_id: str) -> None:
        self._pagamentos.pop(pagamento_id, None)

    def total(self) -> int:
        return len(self._pagamentos)

    def limpar(self) -> None:
        self._pagamentos.clear()
