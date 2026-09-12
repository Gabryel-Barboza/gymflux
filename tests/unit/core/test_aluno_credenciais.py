"""Credencial do Aluno: PIN em texto (Fase 4.8, decisão do dono)."""

from __future__ import annotations

import pytest

from gymflux.core.aluno import Aluno


def test_aluno_definir_e_verificar_senha_visivel():
    a = Aluno(id="a1", nome="Ana")
    assert a.tem_credencial is False
    a.definir_senha("1234")
    assert a.senha == "1234"  # texto puro, exibido no perfil
    assert a.verificar_senha("1234") is True
    assert a.verificar_senha("0000") is False
    assert a.verificar_senha("12") is False  # inválida nunca levanta
    assert a.tem_credencial is True
    with pytest.raises(ValueError):
        a.definir_senha("12")


def test_aluno_limpar_senha():
    a = Aluno(id="a1", nome="Ana")
    a.definir_senha("1234")
    a.limpar_senha()
    assert a.senha is None
    assert a.tem_credencial is False
    assert a.verificar_senha("1234") is False


def test_aluno_sem_cartao():
    # cartão removido na Fase 4.8: nem campo nem método existem mais
    a = Aluno(id="a1", nome="Ana")
    assert not hasattr(a, "cartao_id")
    assert not hasattr(a, "definir_cartao")
    assert not hasattr(a, "senha_hash")
