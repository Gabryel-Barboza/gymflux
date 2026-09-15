"""FichaViewModel — Qt-free, salvar/listar por aluno ordenado por data desc."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from gymflux.core.ficha import AvaliacaoFisica


class FichaRepoProto(Protocol):
    def salvar(self, avaliacao: AvaliacaoFisica) -> AvaliacaoFisica: ...
    def buscar_por_id(self, avaliacao_id: str) -> AvaliacaoFisica | None: ...
    def listar_por_aluno(self, aluno_id: str) -> list[AvaliacaoFisica]: ...
    def listar(self) -> list[AvaliacaoFisica]: ...
    def remover(self, avaliacao_id: str) -> None: ...


@dataclass
class FichaViewModel:
    repo: FichaRepoProto
    commit: Callable[[], None] | None = None

    def _commit(self) -> None:
        if self.commit is not None:
            self.commit()

    def salvar(
        self,
        *,
        aluno_id: str,
        data: date | None = None,
        peso_kg: float | str | None = None,
        altura_cm: float | str | None = None,
        gordura_pct: float | str | None = None,
        medidas: dict[str, Any] | str | None = None,
        problemas_saude: str | None = None,
        restricoes: str | None = None,
        medicamentos: str | None = None,
        contato_emergencia: str | None = None,
        avaliacao_id: str | None = None,
    ) -> AvaliacaoFisica:
        # normaliza
        d = data or date.today()

        def _to_float(v: Any, nome: str) -> float | None:
            if v is None or (isinstance(v, str) and not v.strip()):
                return None
            try:
                f = float(str(v).replace(",", ".").strip())
            except (TypeError, ValueError) as e:
                raise ValueError(f"{nome} deve ser numérico.") from e
            return f

        peso = _to_float(peso_kg, "Peso")
        altura = _to_float(altura_cm, "Altura")
        gordura = _to_float(gordura_pct, "Gordura")

        med = medidas

        avaliacao = AvaliacaoFisica(
            id=avaliacao_id or f"ava-{uuid.uuid4().hex[:8]}",
            aluno_id=aluno_id.strip(),
            data=d,
            peso_kg=peso,
            altura_cm=altura,
            gordura_pct=gordura,
            medidas=med or {},  # type: ignore[arg-type]
            problemas_saude=problemas_saude,
            restricoes=restricoes,
            medicamentos=medicamentos,
            contato_emergencia=contato_emergencia,
        )
        self.repo.salvar(avaliacao)
        self._commit()
        return avaliacao

    def listar_por_aluno(self, aluno_id: str) -> list[AvaliacaoFisica]:
        lst = self.repo.listar_por_aluno(aluno_id)
        return sorted(lst, key=lambda a: a.data, reverse=True)

    def listar(self) -> list[AvaliacaoFisica]:
        return sorted(self.repo.listar(), key=lambda a: a.data, reverse=True)

    def remover(self, avaliacao_id: str) -> None:
        self.repo.remover(avaliacao_id)
        self._commit()

    def buscar(self, avaliacao_id: str) -> AvaliacaoFisica | None:
        return self.repo.buscar_por_id(avaliacao_id)
