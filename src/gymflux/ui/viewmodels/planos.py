"""PlanosViewModel — CRUD de planos (Qt-free, sem service dedicado)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from gymflux.core.plano import Plano, TipoPlano


class PlanoRepoProto(Protocol):
    def salvar(self, plano: Plano) -> Plano: ...
    def buscar_por_id(self, plano_id: str) -> Plano | None: ...
    def listar(self) -> list[Plano]: ...
    def remover(self, plano_id: str) -> None: ...


DURACAO_POR_TIPO: dict[TipoPlano, int] = {
    TipoPlano.DIARIO: 1,
    TipoPlano.MENSAL: 30,
    TipoPlano.TRIMESTRAL: 90,
    TipoPlano.SEMESTRAL: 180,
    TipoPlano.ANUAL: 365,
}


@dataclass
class PlanosViewModel:
    repo: PlanoRepoProto
    commit: Callable[[], None] | None = None

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    def listar(self) -> list[Plano]:
        return sorted(self.repo.listar(), key=lambda p: p.nome.lower())

    def salvar(
        self,
        *,
        nome: str,
        tipo: TipoPlano | str,
        valor: Decimal | float | str,
        tolerancia_dias: int = 3,
        duracao_dias: int | None = None,
        plano_id: str | None = None,
    ) -> Plano:
        tipo_enum = TipoPlano(tipo) if isinstance(tipo, str) else tipo
        if duracao_dias is None:
            if tipo_enum == TipoPlano.PERSONALIZADO:
                raise ValueError("Plano PERSONALIZADO exige duracao_dias explícita")
            duracao_dias = DURACAO_POR_TIPO[tipo_enum]
        plano = Plano(
            id=plano_id or f"plano-{uuid.uuid4().hex[:8]}",
            nome=nome.strip(),
            duracao_dias=duracao_dias,
            valor=Decimal(str(valor)),
            tolerancia_dias=tolerancia_dias,
            tipo=tipo_enum,
        )
        self.repo.salvar(plano)
        self._commit()
        return plano

    def remover(self, plano_id: str) -> None:
        self.repo.remover(plano_id)
        self._commit()
