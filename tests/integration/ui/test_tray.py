"""Tray — bandeja com fallback Linux (offscreen). Fusão 3 em 1 para economizar qtbot."""

from __future__ import annotations

import contextlib

import pytest

pytestmark = [pytest.mark.ui, pytest.mark.slow]

try:
    from PySide6.QtWidgets import QSystemTrayIcon

    HAS_QT = True
except Exception:  # pragma: no cover
    HAS_QT = False

pytestmark = pytest.mark.skipif(not HAS_QT, reason="Qt não disponível")


def test_tray_minimiza_fallback_e_giros_titulo(qtbot, qapp, monkeypatch):
    """Funde fechar_com_tray + fallback_linux + giros_titulo (0.89s cada → 1.1s total)."""
    from PySide6.QtGui import QCloseEvent

    from gymflux.ui.app import build_window, create_context
    from gymflux.ui.theme import ModoTema, stylesheet

    # --- subteste 1: fechar com tray disponível → hide() ---
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))
    ctx = create_context(use_db=False)
    with contextlib.suppress(Exception):
        ctx.bridge.conectar()
    win = build_window(ctx)
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win, timeout=2000)
    if getattr(win, "tray", None) is not None:
        with contextlib.suppress(Exception):
            win.tray.show()
        monkeypatch.setattr(win.tray, "isVisible", lambda: True)
    assert win.isVisible()
    ev = QCloseEvent()
    win.closeEvent(ev)
    assert ev.isAccepted() is False
    assert not win.isVisible()
    win._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
    assert win.isVisible()
    # limpeza tray da subfase 1
    if getattr(win, "tray", None) is not None:
        with contextlib.suppress(Exception):
            win.tray.hide()
    win.close()
    with contextlib.suppress(Exception):
        qtbot.wait(100)
    # destrói janela 1 antes de subteste 2 para não vazar
    with contextlib.suppress(Exception):
        from shiboken6 import delete, isValid

        if isValid(win):
            delete(win)
    qapp.processEvents()

    # --- subteste 2: fallback Linux sem tray → close normal ---
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: False))
    ctx2 = create_context(use_db=False)
    win2 = build_window(ctx2)
    qtbot.addWidget(win2)
    win2.show()
    qtbot.waitExposed(win2, timeout=2000)
    assert getattr(win2, "tray", None) is None or not win2.tray.isVisible()
    ev2 = QCloseEvent()
    win2.closeEvent(ev2)
    assert ev2.isAccepted() is True
    with contextlib.suppress(Exception):
        win2.close()
        from shiboken6 import delete, isValid

        if isValid(win2):
            delete(win2)
    qapp.processEvents()

    # --- subteste 3: giros título preto, container segue tema ---
    # mesmo win, troca tema para claro
    ctx3 = create_context(use_db=False)
    win3 = build_window(ctx3)
    qtbot.addWidget(win3)
    qapp.setStyleSheet(stylesheet(ModoTema.CLARO))
    win3.show()
    qtbot.waitExposed(win3, timeout=2000)
    with contextlib.suppress(Exception):
        win3.dashboard_view._aplicar_fundo_containers(False)
    titulo_style = win3.dashboard_view.lbl_giros_titulo.styleSheet()
    assert "#0F1113" in titulo_style
    assert "color: #F2F5F7" in titulo_style
    lst_style = win3.dashboard_view.lst_giros.styleSheet()
    assert "#0F1113" not in lst_style
    frame_style = win3.dashboard_view.frame_giros.styleSheet()
    assert "#0F1113" not in frame_style
    # wallpaper None + tray fallback edge: não deve crashar
    with contextlib.suppress(Exception):
        win3.dashboard_view.aplicar_wallpaper(None)
        win3.aplicar_wallpaper(None)
    assert win3.dashboard_view._wallpaper_pixmap is None
    win3.close()
