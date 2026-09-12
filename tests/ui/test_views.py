"""Testes das telas com pytest-qt headless (offscreen, mock, sem hardware real)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6", reason="UI requer extra ui: uv sync --extra ui")

from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import QWidget

from gymflow.core.plano import TipoPlano
from gymflow.hardware.henry7x.interface import Direcao
from gymflow.hardware.henry7x.mock import MockHenry7x
from gymflow.ui.app import build_window
from gymflow.ui.catraca_bridge import CatracaBridge
from gymflow.ui.views.dashboard import DashboardView


def test_janela_principal_tem_4_abas(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    textos = [win.tabs.tabText(i) for i in range(win.tabs.count())]
    assert textos == ["Catraca", "Alunos", "Planos", "Pagamentos"]


def test_dashboard_renderiza_status_mock(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    view = win.tabs.widget(0)
    assert isinstance(view, DashboardView)
    view._refresh_status()
    assert view.lbl_online.text() == "SIM"
    assert "MockHenry7x" in view.lbl_driver.text()


def test_fluxo_completo_pela_ui_cadastra_e_libera(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)

    aluno = ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    plano = ctx.planos_vm.salvar(nome="Mensal", tipo=TipoPlano.MENSAL, valor=Decimal("99.90"))
    ctx.alunos_vm.matricular(aluno.id, plano.id)
    ctx.pagamentos_vm.registrar(
        aluno_id=aluno.id,
        valor=Decimal("99.90"),
        data_vencimento=date.today(),
        pago=True,
    )

    dash.edt_aluno.setText(aluno.id)
    dash._liberar("ENTRADA")
    assert dash.lbl_resultado.text().startswith("LIBERADO")
    assert dash.tbl_log.rowCount() == 1
    item_nome = dash.tbl_log.item(0, 1)
    assert item_nome is not None
    assert item_nome.text() == "Ana Silva"


def test_dashboard_negado_mostra_motivo(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    dash = win.tabs.widget(0)
    assert isinstance(dash, DashboardView)
    aluno = ctx.alunos_vm.cadastrar(nome="Sem Pagar", cpf="22255588846")
    dash.edt_aluno.setText(aluno.id)
    dash._liberar("ENTRADA")
    assert dash.lbl_resultado.text().startswith("NEGADO")


def test_alunos_view_busca_filtra(qtbot, ctx):
    win = build_window(ctx)
    qtbot.addWidget(win)
    view = win.tabs.widget(1)
    ctx.alunos_vm.cadastrar(nome="Ana Silva", cpf="11144477735")
    ctx.alunos_vm.cadastrar(nome="Bruno Souza", cpf="22255588846")
    view.edt_busca.setText("ana")
    assert view.tbl.rowCount() == 1
    view.edt_busca.clear()
    assert view.tbl.rowCount() == 2


def test_bridge_giro_chega_como_signal(qtbot):
    mock = MockHenry7x(auto_giro=False)
    bridge = CatracaBridge(driver=mock, porta="MOCK:1")
    qtbot.addWidget(QWidget())
    bridge.conectar()
    bridge.liberar_entrada()
    with qtbot.waitSignal(bridge.giro_detectado, timeout=2000) as blocker:
        mock.simular_giro(Direcao.ENTRADA)
    assert blocker.args[0] == "ENTRADA"
    bridge.desconectar()
