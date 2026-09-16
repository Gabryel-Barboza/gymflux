"""PagamentoRepository — Protocol + SQLAlchemy."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from gymflux.core.pagamento import Pagamento
from gymflux.infra.models.pagamento import PagamentoModel


class PagamentoRepository(Protocol):
    def salvar(self, pagamento: Pagamento) -> Pagamento: ...
    def buscar_por_id(self, pagamento_id: str) -> Pagamento | None: ...
    def listar_por_aluno(self, aluno_id: str) -> list[Pagamento]: ...
    def listar(self) -> list[Pagamento]: ...
    def remover(self, pagamento_id: str) -> None: ...
    def total(self) -> int: ...
    def listar_por_mes(
        self, mes: str | None, limit: int | None = None, offset: int = 0
    ) -> list[Pagamento]: ...
    def contar_por_mes(self, mes: str | None) -> int: ...
    def totais_por_mes(self, mes: str | None) -> tuple[Decimal, Decimal, Decimal]: ...
    def meses_distintos(self) -> list[str]: ...


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


def _mes_where(mes: str | None):  # type: ignore[no-untyped-def]
    if mes is None:
        return None
    return or_(
        PagamentoModel.competencia == mes,
        and_(
            PagamentoModel.competencia.is_(None),
            func.strftime("%Y-%m", PagamentoModel.vencimento) == mes,
        ),
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

    # -- pushdown (Fase 4.16) -------------------------------------------------
    def listar_por_mes(
        self, mes: str | None, limit: int | None = None, offset: int = 0
    ) -> list[Pagamento]:
        where = _mes_where(mes)
        stmt = select(PagamentoModel).order_by(PagamentoModel.vencimento.desc())
        if where is not None:
            stmt = stmt.where(where)
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        elif offset:
            stmt = stmt.offset(offset)
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def contar_por_mes(self, mes: str | None) -> int:
        where = _mes_where(mes)
        stmt = select(func.count()).select_from(PagamentoModel)
        if where is not None:
            stmt = stmt.where(where)
        return int(self.session.execute(stmt).scalar_one() or 0)

    def totais_por_mes(self, mes: str | None) -> tuple[Decimal, Decimal, Decimal]:
        where = _mes_where(mes)
        recebido_expr = func.coalesce(
            func.sum(
                case((PagamentoModel.data_pagamento.is_not(None), PagamentoModel.valor), else_=0)
            ),
            0,
        )
        pendente_expr = func.coalesce(
            func.sum(
                case((PagamentoModel.data_pagamento.is_(None), PagamentoModel.valor), else_=0)
            ),
            0,
        )
        stmt = select(recebido_expr, pendente_expr)
        if where is not None:
            stmt = stmt.where(where)
        row = self.session.execute(stmt).one()
        recebido = Decimal(str(row[0] or 0))
        pendente = Decimal(str(row[1] or 0))
        return recebido, pendente, recebido + pendente

    def meses_distintos(self) -> list[str]:
        # coalesce(competencia, strftime) cobre os dois casos
        expr = func.coalesce(
            PagamentoModel.competencia, func.strftime("%Y-%m", PagamentoModel.vencimento)
        )
        stmt = select(expr.distinct())
        rows = [r[0] for r in self.session.execute(stmt).all() if r[0]]
        return sorted(set(rows), reverse=True)

    def remover(self, pagamento_id: str) -> None:
        m = self.session.get(PagamentoModel, pagamento_id)
        if m:
            self.session.delete(m)
            self.session.flush()

    def total(self) -> int:
        stmt = select(func.count()).select_from(PagamentoModel)
        return int(self.session.execute(stmt).scalar_one() or 0)

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

    def _mes_match(self, p: Pagamento, mes: str | None) -> bool:
        if mes is None:
            return True
        comp = p.competencia
        if comp is not None:
            return comp == mes
        return p.data_vencimento.strftime("%Y-%m") == mes

    def listar_por_mes(
        self, mes: str | None, limit: int | None = None, offset: int = 0
    ) -> list[Pagamento]:
        vals = [p for p in self._pagamentos.values() if self._mes_match(p, mes)]
        vals.sort(key=lambda p: p.data_vencimento, reverse=True)
        if offset:
            vals = vals[offset:]
        if limit is not None:
            vals = vals[:limit]
        return vals

    def contar_por_mes(self, mes: str | None) -> int:
        return sum(1 for p in self._pagamentos.values() if self._mes_match(p, mes))

    def totais_por_mes(self, mes: str | None) -> tuple[Decimal, Decimal, Decimal]:
        recebido = Decimal("0")
        pendente = Decimal("0")
        for p in self._pagamentos.values():
            if not self._mes_match(p, mes):
                continue
            if p.pago:
                recebido += p.valor
            else:
                pendente += p.valor
        return recebido, pendente, recebido + pendente

    def meses_distintos(self) -> list[str]:
        vals = set()
        for p in self._pagamentos.values():
            vals.add(p.competencia or p.data_vencimento.strftime("%Y-%m"))
        return sorted(vals, reverse=True)

    def remover(self, pagamento_id: str) -> None:
        self._pagamentos.pop(pagamento_id, None)

    def total(self) -> int:
        return len(self._pagamentos)

    def limpar(self) -> None:
        self._pagamentos.clear()
