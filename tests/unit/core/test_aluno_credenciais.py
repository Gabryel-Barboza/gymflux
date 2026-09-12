"""Credenciais no Aluno: definir/verificar senha + normalização do cartão."""

from __future__ import annotations

import pytest

from gymflow.core.aluno import Aluno


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
