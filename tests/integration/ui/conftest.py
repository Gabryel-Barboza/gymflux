"""Fixtures Qt de integração (offscreen centralizado em tests/conftest.py).

- ``ctx``: contexto em memória + driver mock conectado (escopo de função —
  cada teste cadastra CPFs repetidos, então VMs NUNCA são compartilhadas).
- ``dash``: ``DashboardView`` direta (sem a janela de 7 abas) p/ testes que
  só exercem o painel da catraca — economiza ~0,1s por teste.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="UI requer extra ui: uv sync --extra ui")

from gymflow.ui.app import AppContext, create_context
from gymflow.ui.views.dashboard import DashboardView

_AQUI = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        try:
            item.path.relative_to(_AQUI)
        except ValueError:
            continue
        item.add_marker(pytest.mark.ui)


@pytest.fixture
def ctx():
    context = create_context(use_db=False)
    context.bridge.driver.conectar("MOCK:1")
    yield context
    context.bridge.driver.desconectar()
    context.close()


@pytest.fixture
def dash(qtbot, ctx: AppContext) -> DashboardView:
    view = DashboardView(ctx.dashboard_vm, ctx.bridge)
    qtbot.addWidget(view)
    return view


@pytest.fixture(autouse=True)
def _destroi_janelas_no_teardown(qapp):
    """Evita acúmulo de widgets entre testes (economiza o repolish global).

    As views conectam lambdas que capturam ``self`` nos signals — ciclo que
    o GC não coleta (1000+ widgets vazados numa run, e cada setStyleSheet
    global repinta todos). Corrigir isso seria mudar código de produção
    (fora do escopo); aqui só destruímos os top-levels ao fim de cada
    teste. Roda DEPOIS do teardown do qtbot (fixture autouse monta antes,
    desmonta depois — LIFO), então não há double-close. Sem gc.collect:
    o ``delete`` imediato já quebra os ciclos no C++; o resto o GC
    automático recolhe.
    """
    yield
    from shiboken6 import delete, isValid

    for w in qapp.topLevelWidgets():
        try:
            if isValid(w):
                w.close()
                delete(w)  # imediato: deleteLater+processEvents não bastava aqui
        except RuntimeError:
            pass  # C++ já deletado
