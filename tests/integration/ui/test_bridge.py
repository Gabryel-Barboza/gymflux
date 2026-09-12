"""CatracaBridge — giro do mock chega como signal Qt."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from gymflow.hardware.henry7x.interface import Direcao
from gymflow.hardware.henry7x.mock import MockHenry7x
from gymflow.ui.catraca_bridge import CatracaBridge


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
