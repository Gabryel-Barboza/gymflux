"""Plano, Vigência e Matrícula — domínio puro."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum


def vencimento_no_mes(ano: int, mes: int, dia_base: int) -> date:
    """Dia de vencimento ancorado no dia da matrícula, com clamp no fim do mês.

    Ex: dia_base 31 em fev 2026 → 28, fev 2024 bissexto → 29, abr → 30.
    Valores de dia_base <1 clampam para 1; mes fora 1..12 levanta ValueError
    via ``calendar.monthrange``/``date``.
    Texto legível: ``Vencimento dia 31 em fevereiro cai no dia 28``.
    """
    if not 1 <= mes <= 12:
        raise ValueError("mês deve ser 1..12")
    dia = max(1, int(dia_base))
    ultimo = calendar.monthrange(ano, mes)[1]
    dia_clamp = min(dia, ultimo)
    return date(ano, mes, dia_clamp)


class TipoPlano(StrEnum):
    DIARIO = "DIARIO"
    MENSAL = "MENSAL"
    TRIMESTRAL = "TRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    ANUAL = "ANUAL"
    PERSONALIZADO = "PERSONALIZADO"


@dataclass(frozen=True, slots=True)
class Plano:
    """Plano de academia.

    `tolerancia_dias` é a tolerância de atraso de pagamento (RB01).
    """

    id: str
    nome: str
    duracao_dias: int
    valor: Decimal
    tolerancia_dias: int = 3
    tipo: TipoPlano = TipoPlano.PERSONALIZADO

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise ValueError("nome do plano não pode ser vazio")
        if self.duracao_dias <= 0:
            raise ValueError("duracao_dias deve ser > 0")
        if self.valor < Decimal("0"):
            raise ValueError("valor não pode ser negativo")
        if self.tolerancia_dias < 0:
            raise ValueError("tolerancia_dias não pode ser negativo")

    @classmethod
    def criar_mensal(
        cls,
        id: str = "mensal",
        nome: str = "Mensal",
        valor: Decimal | str | float = Decimal("99.90"),
        tolerancia_dias: int = 3,
    ) -> Plano:
        return cls(
            id=id,
            nome=nome,
            duracao_dias=30,
            valor=Decimal(str(valor)),
            tolerancia_dias=tolerancia_dias,
            tipo=TipoPlano.MENSAL,
        )

    @classmethod
    def criar_trimestral(
        cls,
        id: str = "trimestral",
        nome: str = "Trimestral",
        valor: Decimal | str | float = Decimal("259.90"),
        tolerancia_dias: int = 3,
    ) -> Plano:
        return cls(
            id=id,
            nome=nome,
            duracao_dias=90,
            valor=Decimal(str(valor)),
            tolerancia_dias=tolerancia_dias,
            tipo=TipoPlano.TRIMESTRAL,
        )

    @classmethod
    def criar_anual(
        cls,
        id: str = "anual",
        nome: str = "Anual",
        valor: Decimal | str | float = Decimal("999.90"),
        tolerancia_dias: int = 3,
    ) -> Plano:
        return cls(
            id=id,
            nome=nome,
            duracao_dias=365,
            valor=Decimal(str(valor)),
            tolerancia_dias=tolerancia_dias,
            tipo=TipoPlano.ANUAL,
        )


PLANOS_PADRAO: dict[str, Plano] = {
    "mensal": Plano.criar_mensal(),
    "trimestral": Plano.criar_trimestral(),
    "anual": Plano.criar_anual(),
}


@dataclass(frozen=True, slots=True)
class Vigencia:
    """Período de vigência de uma matrícula."""

    inicio: date
    fim: date

    def __post_init__(self) -> None:
        if self.fim < self.inicio:
            raise ValueError("fim não pode ser anterior a inicio")

    def contem(self, data: date) -> bool:
        return self.inicio <= data <= self.fim

    def expirada_em(self, data: date) -> bool:
        return data > self.fim

    def dias_restantes(self, data: date) -> int:
        if data > self.fim:
            return 0
        return (self.fim - data).days

    @classmethod
    def a_partir_de(cls, inicio: date, duracao_dias: int) -> Vigencia:
        if duracao_dias <= 0:
            raise ValueError("duracao_dias deve ser > 0")
        fim = inicio + timedelta(days=duracao_dias - 1)
        return cls(inicio=inicio, fim=fim)


@dataclass(slots=True)
class Matricula:
    """Vincula aluno ↔ plano com vigência."""

    aluno_id: str
    plano: Plano
    vigencia: Vigencia
    ativa: bool = True

    def vigente_em(self, data: date) -> bool:
        return self.ativa and self.vigencia.contem(data)

    def expirada_em(self, data: date) -> bool:
        return self.vigencia.expirada_em(data)

    def renovar(self, nova_vigencia: Vigencia) -> None:
        self.vigencia = nova_vigencia
        self.ativa = True

    def cancelar(self) -> None:
        self.ativa = False
