"""Validação da senha numérica estilo SCA (4-8 dígitos)."""

from __future__ import annotations

import pytest

from gymflow.core.aluno import validar_senha_numerica


def test_senha_valida_4_a_8_digitos():
    assert validar_senha_numerica("1234") == "1234"
    assert validar_senha_numerica(" 12345678 ") == "12345678"


@pytest.mark.parametrize("ruim", ["", "123", "123456789", "12a4", "abcd", "12 34", "-1234"])
def test_senha_invalida_rejeita(ruim: str):
    with pytest.raises(ValueError):
        validar_senha_numerica(ruim)
