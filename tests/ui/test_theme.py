"""Smoke do tema — paleta aprovada + QSS aplicado (offscreen)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6", reason="UI requer extra ui: uv sync --extra ui")

from gymflow.ui.app import build_window, create_context
from gymflow.ui.theme import (
    AZUL,
    FUNDO,
    LIMA,
    TEXTO,
    VERMELHO,
    estilo_resultado,
    stylesheet,
)
from gymflow.ui.views.dashboard import DashboardView


def test_paleta_aprovada():
    assert AZUL == "#5AC8FA"
    assert FUNDO == "#0F1113"
    assert LIMA == "#A3D65C"
    assert VERMELHO == "#E57373"
    assert TEXTO == "#F2F5F7"


def test_stylesheet_contem_paleta_e_seletores():
    qss = stylesheet()
    for cor in (AZUL, FUNDO, LIMA, TEXTO):
        assert cor in qss
    assert VERMELHO in estilo_resultado(False)  # negado vai inline no resultado
    for seletor in ("QPushButton", "QTabWidget", "QTableWidget", "QLineEdit", "QGroupBox"):
        assert seletor in qss


def test_estilo_resultado():
    assert LIMA in estilo_resultado(True)
    assert VERMELHO in estilo_resultado(False)
    assert LIMA not in estilo_resultado(None)
    assert VERMELHO not in estilo_resultado(None)


def test_tema_aplicado_nas_abas(qapp, qtbot):
    qapp.setStyleSheet(stylesheet())
    assert AZUL in qapp.styleSheet()
    ctx = create_context(use_db=False)
    ctx.bridge.driver.conectar("MOCK:1")
    try:
        win = build_window(ctx)
        qtbot.addWidget(win)
        assert win.tabs.count() == 6
        win.show()
        assert win.isVisible()
    finally:
        ctx.bridge.driver.desconectar()
        ctx.close()


def test_resultado_liberado_verde_negado_vermelho(qtbot, ctx):
    from datetime import date
    from decimal import Decimal

    from gymflow.core.plano import TipoPlano

    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)

    aluno = ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    dash.edt_aluno.setText(aluno.id)
    dash._liberar("ENTRADA")  # sem matrícula => NEGADO
    assert dash.lbl_resultado.text().startswith("NEGADO")
    assert VERMELHO in dash.lbl_resultado.styleSheet()

    plano = ctx.planos_vm.salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    ctx.alunos_vm.matricular(aluno.id, plano.id)
    ctx.pagamentos_vm.registrar(
        aluno_id=aluno.id, valor=Decimal("99.90"), data_vencimento=date.today(), pago=True
    )
    dash._liberar("ENTRADA")
    assert dash.lbl_resultado.text().startswith("LIBERADO")
    assert LIMA in dash.lbl_resultado.styleSheet()
