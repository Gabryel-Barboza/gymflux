"""Ícones DPI-safe Fase 5.4 — tamanho real == icon_size com win32 simulado.

No Windows o QStyle entrega pixmaps nativos grandes e o DPR alto pinta
maior que no Linux; ``normalizar_icone`` reconstrói UM pixmap exato, então
``actualSize == lado`` em qualquer DPI. Header de abas NÃO é tocado aqui.
"""

from __future__ import annotations

import sys

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QStyle

from gymflux.ui import theme as theme_mod
from gymflux.ui.theme import icon_size, icone_preto, icone_vermelho, normalizar_icone


@pytest.fixture
def _win32(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "platform", "win32")
    backup = dict(theme_mod._ICONE_CACHE)
    theme_mod._ICONE_CACHE.clear()
    try:
        yield
    finally:
        theme_mod._ICONE_CACHE.clear()
        theme_mod._ICONE_CACHE.update(backup)


def test_icone_win32_tamanho_real(qapp, _win32):
    assert icon_size() == 16
    style = qapp.style()
    for fab in (icone_preto, icone_vermelho):
        icon = fab(style, QStyle.StandardPixmap.SP_DialogOkButton)
        assert not icon.isNull()
        # pixmap único exato: nada de 32/128px vazando
        assert icon.availableSizes() == [QSize(16, 16)]
        assert icon.actualSize(QSize(16, 16)) == QSize(16, 16)
        # DPR alto carrega pixels extras sem mudar o tamanho lógico
        pix = icon.pixmap(16, 16)
        assert pix.width() >= 16 and pix.height() >= 16
        btn = QPushButton("Salvar")
        btn.setIcon(icon)
        btn.setIconSize(QSize(icon_size(), icon_size()))
        assert btn.icon().actualSize(QSize(16, 16)).width() == 16
        assert btn.sizeHint().width() < 220


def test_normalizar_icone_nulo_e_linux(qapp):
    assert normalizar_icone(QIcon()).isNull()
    assert icon_size() == 22  # fora do win32, padrão Fase 5.3
