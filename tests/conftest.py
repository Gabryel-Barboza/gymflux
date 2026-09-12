"""Garantias globais da suite (lido antes de qualquer test module).

- ``QT_QPA_PLATFORM=offscreen`` centralizado: nenhum teste Qt abre janela.
- PBKDF2 rápido: ``GYMFLOW_PBKDF2_ITERATIONS`` baixo via fixture autouse.
  O default prod (100_000) segue intacto — ver ``_iteracoes_pbkdf2`` em
  ``gymflow.core.aluno`` e o teste-guarda em ``unit/core/test_senha_hash.py``.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(autouse=True)
def _pbkdf2_rapido_nos_testes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Acelera gerar/verificar senha (~0,15s -> ~0,002s por op).

    Escopo de função via monkeypatch: vaza nada p/ prod nem entre suites.
    """
    monkeypatch.setenv("GYMFLOW_PBKDF2_ITERATIONS", "1000")
