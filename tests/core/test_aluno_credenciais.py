"""Credenciais estilo SCA: senha numérica (hash) + cartão."""

from __future__ import annotations

import pytest

from gymflow.core.aluno import (
    Aluno,
    conferir_senha,
    gerar_senha_hash,
    validar_senha_numerica,
)


def test_senha_valida_4_a_8_digitos():
    assert validar_senha_numerica("1234") == "1234"
    assert validar_senha_numerica(" 12345678 ") == "12345678"


@pytest.mark.parametrize("ruim", ["", "123", "123456789", "12a4", "abcd", "12 34", "-1234"])
def test_senha_invalida_rejeita(ruim: str):
    with pytest.raises(ValueError):
        validar_senha_numerica(ruim)


def test_hash_nunca_contem_texto_e_verifica():
    h = gerar_senha_hash("1234")
    assert "1234" not in h
    assert conferir_senha("1234", h) is True
    assert conferir_senha("4321", h) is False
    assert conferir_senha("1234", None) is False
    assert conferir_senha("1234", "formato-antigo") is False


def test_salts_distintos_geram_hashes_distintos():
    h1 = gerar_senha_hash("1234")
    h2 = gerar_senha_hash("1234")
    assert h1 != h2
    assert conferir_senha("1234", h1) is True
    assert conferir_senha("1234", h2) is True


def test_aluno_definir_e_verificar_senha():
    a = Aluno(id="a1", nome="Ana")
    assert a.tem_credencial is False
    a.definir_senha("1234")
    assert a.senha_hash is not None and "1234" not in a.senha_hash
    assert a.verificar_senha("1234") is True
    assert a.verificar_senha("0000") is False
    assert a.tem_credencial is True
    with pytest.raises(ValueError):
        a.definir_senha("12")


def test_aluno_cartao_normaliza():
    a = Aluno(id="a1", nome="Ana")
    a.definir_cartao("  TAG-42 ")
    assert a.cartao_id == "TAG-42"
    assert a.tem_credencial is True
    a.definir_cartao("   ")
    assert a.cartao_id is None
