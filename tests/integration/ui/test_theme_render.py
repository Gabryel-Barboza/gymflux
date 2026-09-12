"""Tema aplicado — QSS dos dois modos carrega e renderiza offscreen.

Smoke leve: um QWidget basta p/ provar que os dois stylesheets aplicam sem
erro e a janela aparece no offscreen (sem ``waitExposed`` — no offscreen o
expose é assíncrono e o wait custava ~0,5s; ``show()`` + ``processEvents()``
basta p/ ``isVisible()``). A janela completa de 7 abas é coberta em
``test_janela.py``.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from gymflux.ui.theme import AZUL, ModoTema, stylesheet


def test_modos_renderizam_offscreen(qapp, qtbot):
    qapp.setStyleSheet(stylesheet())
    assert AZUL in qapp.styleSheet()
    w = QWidget()
    qtbot.addWidget(w)
    w.show()
    qapp.processEvents()
    assert w.isVisible()
    qapp.setStyleSheet(stylesheet(ModoTema.ESCURO))
    qapp.processEvents()
    assert "background-color: #0F1113" in qapp.styleSheet()
    qapp.setStyleSheet(stylesheet(ModoTema.CLARO))
    qapp.processEvents()
    assert "background-color: #FFFFFF" in qapp.styleSheet()
    assert w.isVisible()
