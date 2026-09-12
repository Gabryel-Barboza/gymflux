"""Smoke do tema — paleta aprovada + QSS aplicado (offscreen)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6", reason="UI requer extra ui: uv sync --extra ui")

from gymflow.ui.app import build_window, create_context
from gymflow.ui.theme import (
    AZUL,
    BORDA,
    BORDA_CLARA,
    FUNDO,
    FUNDO_CLARO,
    LIMA,
    SUAVE_CLARO,
    TEXTO,
    TEXTO_CLARO,
    TEXTO_SUAVE,
    TINTA_SOBRE_ACENTO,
    VERMELHO,
    ModoTema,
    contraste,
    cores_indicador,
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


def test_modo_tema_e_stylesheet_parametrizado():
    assert stylesheet() == stylesheet(ModoTema.ESCURO)
    assert stylesheet("ESCURO") == stylesheet(ModoTema.ESCURO)
    claro = stylesheet(ModoTema.CLARO)
    assert stylesheet("claro") == claro
    # base trocada no claro (com indentação p/ não colidir substrings,
    # ex. "background-color: #1A1E22" contém "color: #1A1E22")...
    for regra in (
        "\n    background-color: #F2F5F7;",
        "\n    background-color: #FFFFFF;",
        "\n    color: #1A1E22;",
        "\n    color: #5A6B78;",
        "\n    border: 1px solid #D5DCE2;",
    ):
        assert regra in claro
        assert regra not in stylesheet()
    # ...acentos mantidos nos dois (AZUL/LIMA no QSS; VERMELHO vive nos
    # estilos inline de resultado/selo — ver abaixo)
    for cor in (AZUL, LIMA):
        assert cor in stylesheet()
        assert cor in claro
    for seletor in (
        "QPushButton",
        "QTabWidget",
        "QTableWidget",
        "QLineEdit",
        "QGroupBox",
        "PlanoCard",
    ):
        assert seletor in stylesheet()
        assert seletor in claro


def test_estilo_resultado_modo_claro_usa_selos():
    claro_ok = estilo_resultado(True, ModoTema.CLARO)
    assert LIMA in claro_ok and TINTA_SOBRE_ACENTO in claro_ok
    claro_neg = estilo_resultado(False, "CLARO")
    assert VERMELHO in claro_neg and TINTA_SOBRE_ACENTO in claro_neg
    neutro = estilo_resultado(None, ModoTema.CLARO)
    assert SUAVE_CLARO in neutro
    assert LIMA not in neutro and VERMELHO not in neutro


def test_cores_indicador_online():
    assert cores_indicador(True) == (LIMA, None)
    assert cores_indicador(False) == (VERMELHO, None)
    assert cores_indicador(True, ModoTema.CLARO) == (TINTA_SOBRE_ACENTO, LIMA)
    assert cores_indicador(False, "CLARO") == (TINTA_SOBRE_ACENTO, VERMELHO)


def test_contraste_minimo_texto_fundo():
    assert contraste("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.1)
    assert contraste(AZUL, AZUL) == pytest.approx(1.0)
    # corpo de texto: >= 7 nos dois modos
    assert contraste(TEXTO, FUNDO) >= 7.0
    assert contraste(TEXTO_CLARO, FUNDO_CLARO) >= 7.0
    # texto suave: >= 4.5 nos dois modos
    assert contraste(TEXTO_SUAVE, FUNDO) >= 4.5
    assert contraste(SUAVE_CLARO, FUNDO_CLARO) >= 4.5
    # títulos/cabeçalhos em negrito: >= 4.5 (claro usa tinta escura)
    assert contraste(AZUL, FUNDO) >= 4.5
    assert contraste(TEXTO_CLARO, FUNDO_CLARO) >= 4.5
    # texto sobre preenchimento de acento: >= 4.5
    for preenchimento in (AZUL, LIMA, VERMELHO):
        assert contraste(TINTA_SOBRE_ACENTO, preenchimento) >= 4.5
    # botões desabilitados: >= 3.0 documentado (WCAG isenta desabilitado)
    assert contraste(TEXTO_SUAVE, BORDA) >= 4.5
    assert contraste(SUAVE_CLARO, BORDA_CLARA) >= 3.0
    # selo FECHADO: texto com borda no escuro, preenchido no claro
    from gymflow.ui.theme import estilo_selo

    assert VERMELHO in estilo_selo()
    assert VERMELHO in estilo_selo(ModoTema.CLARO)
    assert contraste(TINTA_SOBRE_ACENTO, VERMELHO) >= 4.5


def test_tema_aplicado_nas_abas(qapp, qtbot):
    qapp.setStyleSheet(stylesheet())
    assert AZUL in qapp.styleSheet()
    ctx = create_context(use_db=False)
    ctx.bridge.driver.conectar("MOCK:1")
    try:
        win = build_window(ctx)
        qtbot.addWidget(win)
        assert win.tabs.count() == 7
        win.show()
        assert win.isVisible()
    finally:
        ctx.bridge.driver.desconectar()
        ctx.close()


def test_ambos_modos_renderizam_offscreen(qapp, qtbot):
    ctx = create_context(use_db=False)
    ctx.bridge.driver.conectar("MOCK:1")
    try:
        win = build_window(ctx)
        qtbot.addWidget(win)
        win.show()
        qapp.setStyleSheet(stylesheet(ModoTema.ESCURO))
        qtbot.waitExposed(win)
        assert "background-color: #0F1113" in qapp.styleSheet()
        qapp.setStyleSheet(stylesheet(ModoTema.CLARO))
        qtbot.waitExposed(win)
        assert "background-color: #FFFFFF" in qapp.styleSheet()
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
    ctx.caixa_vm.registrar(
        aluno_id=aluno.id, valor=Decimal("99.90"), data_vencimento=date.today(), pago=True
    )
    dash._liberar("ENTRADA")
    assert dash.lbl_resultado.text().startswith("LIBERADO")
    assert LIMA in dash.lbl_resultado.styleSheet()
