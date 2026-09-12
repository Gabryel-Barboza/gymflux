"""Hash PBKDF2 da senha (salts, verificação, default prod).

Roda com ``GYMFLOW_PBKDF2_ITERATIONS=1000`` via fixture autouse em
``tests/conftest.py`` — o ``test_default_prod_mantem_100_mil`` garante que o
default de produção NÃO foi reduzido (sem hashear, só lê a constante).
"""

from __future__ import annotations

from gymflow.core import aluno as aluno_mod
from gymflow.core.aluno import (
    _PBKDF2_ITERACOES,
    _iteracoes_pbkdf2,
    conferir_senha,
    gerar_senha_hash,
)


def test_default_prod_mantem_100_mil(monkeypatch):
    assert _PBKDF2_ITERACOES == 100_000
    monkeypatch.delenv("GYMFLOW_PBKDF2_ITERATIONS", raising=False)
    assert _iteracoes_pbkdf2() == 100_000
    monkeypatch.setenv("GYMFLOW_PBKDF2_ITERATIONS", "lixo")
    assert _iteracoes_pbkdf2() == 100_000


def test_env_configura_iteracoes_e_hash_carrega_contagem(monkeypatch):
    monkeypatch.setenv("GYMFLOW_PBKDF2_ITERATIONS", "1000")
    assert _iteracoes_pbkdf2() == 1000
    h = gerar_senha_hash("1234")
    assert h.startswith("pbkdf2_sha256$1000$")
    assert conferir_senha("1234", h) is True
    assert aluno_mod._ENV_PBKDF2_ITERACOES == "GYMFLOW_PBKDF2_ITERATIONS"


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
