"""Pagamento — domínio puro."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class FormaPagamento(StrEnum):
    PIX = "PIX"
    DINHEIRO = "DINHEIRO"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    BOLETO = "BOLETO"
    TRANSFERENCIA = "TRANSFERENCIA"


@dataclass(frozen=True, slots=True)
class Pagamento:
    id: str
    aluno_id: str
    valor: Decimal
    data_vencimento: date
    data_pagamento: date | None = None
    forma: FormaPagamento | str | None = None
    competencia: str | None = None

    def __post_init__(self) -> None:
        if self.valor <= Decimal("0"):
            raise ValueError("valor deve ser > 0")
        # data_pagamento pode ser None = pendente / não pago

    @property
    def pago(self) -> bool:
        return self.data_pagamento is not None

    def dias_atraso(self, hoje: date) -> int:
        """Dias de atraso em relação ao vencimento.

        Se já pago, compara data_pagamento vs vencimento.
        Se pendente, compara hoje vs vencimento.
        Retorna 0 se ainda dentro do prazo.
        """
        referencia = self.data_pagamento if self.pago else hoje
        assert referencia is not None
        delta = (referencia - self.data_vencimento).days
        return max(0, delta)

    def dentro_tolerancia(self, hoje: date, tolerancia_dias: int) -> bool:
        return self.dias_atraso(hoje) <= tolerancia_dias


def pagamento_mais_recente(pagamentos: list[Pagamento]) -> Pagamento | None:
    if not pagamentos:
        return None
    return max(pagamentos, key=lambda p: p.data_vencimento)


def esta_adimplente(
    pagamentos: list[Pagamento],
    hoje: date,
    tolerancia_dias: int,
) -> bool:
    """RB01: tolerância de atraso.

    - Sem pagamentos => inadimplente (negado).
    - Considera o vencimento mais recente: se pago ou dentro da tolerância => adimplente.
    - Pagamento futuro (vencimento > hoje) => adimplente.
    """
    if tolerancia_dias < 0:
        raise ValueError("tolerancia_dias não pode ser negativo")
    recente = pagamento_mais_recente(pagamentos)
    if recente is None:
        return False
    # vencimento futuro ainda não exige pagamento
    if recente.data_vencimento > hoje:
        return True
    # se pendente (data_pagamento is None) e vencido beyond tolerancia => inadimplente
    if not recente.pago:
        return recente.dentro_tolerancia(hoje, tolerancia_dias)
    # pago: verifica se pagou dentro da tolerância
    return recente.dentro_tolerancia(hoje, tolerancia_dias)


def dias_em_atraso(pagamentos: list[Pagamento], hoje: date) -> int:
    recente = pagamento_mais_recente(pagamentos)
    if recente is None:
        return 0
    return recente.dias_atraso(hoje)
