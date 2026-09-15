"""vencimento_no_mes — clamp de dia 31 para meses curtos."""

from __future__ import annotations

from datetime import date

import pytest

from gymflux.core.plano import vencimento_no_mes


def test_clamp_fevereiro_normal():
    assert vencimento_no_mes(2026, 2, 31) == date(2026, 2, 28)
    assert vencimento_no_mes(2026, 2, 30) == date(2026, 2, 28)
    assert vencimento_no_mes(2026, 2, 28) == date(2026, 2, 28)
    assert vencimento_no_mes(2026, 2, 15) == date(2026, 2, 15)


def test_clamp_fevereiro_bissexto():
    assert vencimento_no_mes(2024, 2, 31) == date(2024, 2, 29)
    assert vencimento_no_mes(2024, 2, 29) == date(2024, 2, 29)
    assert vencimento_no_mes(2024, 2, 30) == date(2024, 2, 29)


def test_clamp_30_dias():
    # abr, jun, set, nov têm 30
    assert vencimento_no_mes(2026, 4, 31) == date(2026, 4, 30)
    assert vencimento_no_mes(2026, 6, 31) == date(2026, 6, 30)
    assert vencimento_no_mes(2026, 9, 31) == date(2026, 9, 30)
    assert vencimento_no_mes(2026, 11, 31) == date(2026, 11, 30)
    # 31 em mes 31 dias não clampa
    assert vencimento_no_mes(2026, 1, 31) == date(2026, 1, 31)
    assert vencimento_no_mes(2026, 7, 31) == date(2026, 7, 31)


def test_clamp_minimo_e_invalido():
    assert vencimento_no_mes(2026, 5, 0) == date(2026, 5, 1)
    assert vencimento_no_mes(2026, 5, -5) == date(2026, 5, 1)
    with pytest.raises(ValueError):
        vencimento_no_mes(2026, 13, 10)
    with pytest.raises(ValueError):
        vencimento_no_mes(2026, 0, 10)
