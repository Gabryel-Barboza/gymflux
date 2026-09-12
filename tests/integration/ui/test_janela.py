"""Janela principal — abas e ícones (único teste que monta as 7 abas)."""

from __future__ import annotations

from gymflow.ui.app import build_window


def test_janela_principal_abas(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    textos = [win.tabs.tabText(i) for i in range(win.tabs.count())]
    assert textos == [
        "Catraca",
        "Alunos",
        "Planos",
        "Caixa",
        "Funcionários",
        "Frequência",
        "Configurações",
    ]
    # abas com ícones do sistema (sem assets binários)
    for i in range(win.tabs.count()):
        assert not win.tabs.tabIcon(i).isNull()
