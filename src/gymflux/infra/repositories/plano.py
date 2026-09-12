"""PlanoRepository — Protocol + SQLAlchemy."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from gymflux.core.plano import Plano, TipoPlano
from gymflux.infra.models.plano import PlanoModel


class PlanoRepository(Protocol):
    def salvar(self, plano: Plano) -> Plano: ...
    def buscar_por_id(self, plano_id: str) -> Plano | None: ...
    def listar(self) -> list[Plano]: ...
    def remover(self, plano_id: str) -> None: ...
    def total(self) -> int: ...


def _model_to_domain(m: PlanoModel) -> Plano:
    tipo = TipoPlano(m.tipo) if m.tipo in TipoPlano._value2member_map_ else TipoPlano.PERSONALIZADO
    return Plano(
        id=m.id,
        nome=m.nome,
        duracao_dias=int(m.duracao_dias),
        valor=Decimal(str(m.valor)),
        tolerancia_dias=int(m.tolerancia_dias),
        tipo=tipo,
    )


def _domain_to_model(plano: Plano) -> PlanoModel:
    return PlanoModel(
        id=plano.id,
        nome=plano.nome,
        duracao_dias=plano.duracao_dias,
        valor=Decimal(str(plano.valor)),
        tolerancia_dias=plano.tolerancia_dias,
        tipo=plano.tipo.value if isinstance(plano.tipo, TipoPlano) else str(plano.tipo),
    )


class PlanoRepositorySQLAlchemy:
    def __init__(self, session: Session) -> None:
        self.session = session

    def salvar(self, plano: Plano) -> Plano:
        existing = self.session.get(PlanoModel, plano.id)
        if existing is None:
            model = _domain_to_model(plano)
            self.session.add(model)
        else:
            existing.nome = plano.nome
            existing.duracao_dias = plano.duracao_dias
            existing.valor = Decimal(str(plano.valor))
            existing.tolerancia_dias = plano.tolerancia_dias
            existing.tipo = (
                plano.tipo.value if isinstance(plano.tipo, TipoPlano) else str(plano.tipo)
            )
        self.session.flush()
        return plano

    def buscar_por_id(self, plano_id: str) -> Plano | None:
        m = self.session.get(PlanoModel, plano_id)
        return _model_to_domain(m) if m else None

    def listar(self) -> list[Plano]:
        stmt = select(PlanoModel)
        return [_model_to_domain(m) for m in self.session.execute(stmt).scalars().all()]

    def remover(self, plano_id: str) -> None:
        m = self.session.get(PlanoModel, plano_id)
        if m:
            self.session.delete(m)
            self.session.flush()

    def total(self) -> int:
        stmt = select(PlanoModel)
        return len(self.session.execute(stmt).scalars().all())

    def limpar(self) -> None:
        self.session.query(PlanoModel).delete()
        self.session.flush()


class PlanoRepositoryMemoria:
    def __init__(self) -> None:
        self._planos: dict[str, Plano] = {}

    def salvar(self, plano: Plano) -> Plano:
        self._planos[plano.id] = plano
        return plano

    def buscar_por_id(self, plano_id: str) -> Plano | None:
        return self._planos.get(plano_id)

    def listar(self) -> list[Plano]:
        return list(self._planos.values())

    def remover(self, plano_id: str) -> None:
        self._planos.pop(plano_id, None)

    def total(self) -> int:
        return len(self._planos)

    def limpar(self) -> None:
        self._planos.clear()
