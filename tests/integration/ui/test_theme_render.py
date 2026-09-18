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
    assert "background-color: #E8EDF1" in qapp.styleSheet()
    assert "border: 1px solid #C8D0D8" in qapp.styleSheet()
    assert w.isVisible()


def test_inputs_modernos_renderizam_claro_escuro(qapp, qtbot):
    """Fase 5.4 (smoke): spin/combo/date/time aplicam o QSS global sem erro."""
    from PySide6.QtWidgets import QComboBox, QDateEdit, QSpinBox, QTimeEdit, QWidget

    from gymflux.ui.theme import ModoTema, stylesheet

    for modo in (ModoTema.ESCURO, ModoTema.CLARO):
        qapp.setStyleSheet(stylesheet(modo))
        w = QWidget()
        qtbot.addWidget(w)
        for cls in (QSpinBox, QComboBox, QDateEdit, QTimeEdit):
            cls(w).show()
        w.show()
        qapp.processEvents()
        assert w.isVisible()
    qapp.setStyleSheet(stylesheet(ModoTema.ESCURO))
