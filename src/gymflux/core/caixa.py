"""FechamentoCaixa — domínio puro, sem I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

MES_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validar_mes(mes: str) -> str:
    """Valida competência AAAA-MM. Retorna normalizada (strip)."""
    normalizado = mes.strip()
    if not MES_RE.match(normalizado):
        raise ValueError(f"mês deve estar no formato AAAA-MM (recebido {mes!r})")
    return normalizado


@dataclass(slots=True)
class FechamentoCaixa:
    """Congela o total recebido de um mês; mês fechado bloqueia novos registros."""

    id: str
    mes: str
    total: Decimal
    fechado_em: datetime

    def __post_init__(self) -> None:
        self.mes = validar_mes(self.mes)
        self.total = Decimal(str(self.total))
        if self.total < Decimal("0"):
            raise ValueError("total não pode ser negativo")
