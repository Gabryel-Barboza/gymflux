"""Tray — bandeja com fallback Linux (offscreen)."""

from __future__ import annotations

import contextlib

import pytest

pytestmark = pytest.mark.ui

try:
    from PySide6.QtWidgets import QSystemTrayIcon

    HAS_QT = True
except Exception:  # pragma: no cover
    HAS_QT = False

pytestmark = pytest.mark.skipif(not HAS_QT, reason="Qt não disponível")


def test_fechar_com_tray_disponivel_minimiza(qtbot, qapp, monkeypatch):
    """Fechar com tray disponível → hide() e não quit()."""
    from PySide6.QtGui import QCloseEvent

    from gymflux.ui.app import build_window, create_context

    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))

    ctx = create_context(use_db=False)
    # garante que o driver está conectado para não interferir
    with contextlib.suppress(Exception):
        ctx.bridge.conectar()
    win = build_window(ctx)
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win, timeout=2000)

    # força tray visível (offscreen não tem bandeja real)
    if getattr(win, "tray", None) is not None:
        # em offscreen o show() da bandeja pode falhar — força flag
        with contextlib.suppress(Exception):
            win.tray.show()
        # mock isVisible para simular bandeja ativa
        monkeypatch.setattr(win.tray, "isVisible", lambda: True)

    # garante que a janela está visível antes de fechar
    assert win.isVisible()
    ev = QCloseEvent()
    win.closeEvent(ev)
    assert ev.isAccepted() is False
    assert not win.isVisible()

    # DoubleClick reabre
    # simula activated
    win._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
    assert win.isVisible()

    win.close()
    # limpeza: esconde tray para não deixar órfão no teste
    if getattr(win, "tray", None) is not None:
        with contextlib.suppress(Exception):
            win.tray.hide()


def test_fallback_linux_sem_tray_fecha_normal(qtbot, monkeypatch):
    """Sem bandeja disponível → closeEvent faz close normal."""
    from PySide6.QtGui import QCloseEvent

    from gymflux.ui.app import build_window, create_context

    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: False))

    ctx = create_context(use_db=False)
    win = build_window(ctx)
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win, timeout=2000)

    assert getattr(win, "tray", None) is None or not win.tray.isVisible()

    ev = QCloseEvent()
    win.closeEvent(ev)
    assert ev.isAccepted() is True


def test_giros_titulo_preto_container_tema(qtbot):
    """Só o título Giros é preto; container/lista seguem o tema."""
    from PySide6.QtWidgets import QApplication

    from gymflux.ui.app import build_window, create_context
    from gymflux.ui.theme import ModoTema, stylesheet

    app = QApplication.instance()
    assert app is not None
    ctx = create_context(use_db=False)
    win = build_window(ctx)
    qtbot.addWidget(win)
    # força tema claro
    app.setStyleSheet(stylesheet(ModoTema.CLARO))
    win.show()
    qtbot.waitExposed(win, timeout=2000)
    # força sync
    with contextlib.suppress(Exception):
        win.dashboard_view._aplicar_fundo_containers(False)
    # título tem fundo preto #0F1113 com texto claro
    titulo_style = win.dashboard_view.lbl_giros_titulo.styleSheet()
    assert "#0F1113" in titulo_style
    assert "color: #F2F5F7" in titulo_style
    # lista segue o tema (sem preto forçado)
    lst_style = win.dashboard_view.lst_giros.styleSheet()
    assert "#0F1113" not in lst_style
    # container segue tema (painel claro, não preto)
    frame_style = win.dashboard_view.frame_giros.styleSheet()
    assert "#0F1113" not in frame_style
