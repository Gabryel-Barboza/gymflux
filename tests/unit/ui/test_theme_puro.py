"""Tema puro — paleta, QSS parametrizado e contraste (Qt-free, sem qapp).

Não importa PySide: roda em qualquer env, mesmo sem o extra ``ui``.
"""

from __future__ import annotations

import pytest

from gymflux.ui.theme import (
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
    from gymflux.ui.theme import estilo_selo

    assert VERMELHO in estilo_selo()
    assert VERMELHO in estilo_selo(ModoTema.CLARO)
    assert contraste(TINTA_SOBRE_ACENTO, VERMELHO) >= 4.5
