"""DetalhesDialog Fase 5.2 — retry real via bridge + auto-retry (offscreen, mock)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from gymflux.hardware.henry7x.interface import (
    Direcao,
    GiroCallback,
    Henry7xDriver,
    ResultadoCatraca,
)
from gymflux.ui.catraca_bridge import CatracaBridge
from gymflux.ui.views.dashboard import DashboardView, DetalhesDialog


class _DriverQueFalha(Henry7xDriver):
    """Sem equipamento: conectar/status levantam (falha graciosa no bridge)."""

    is_mock = False

    def conectar(self, porta: str | int, timeout_ms: int = 5000) -> bool:
        raise RuntimeError("sem equipamento (regsvr32 pendente)")

    def desconectar(self) -> None:
        pass

    def liberar(self, direcao: Direcao) -> ResultadoCatraca:
        return ResultadoCatraca.ERRO

    def bloquear(self) -> None:
        pass

    def on_giro(self, callback: GiroCallback) -> None:
        pass

    def off_giro(self, callback: GiroCallback) -> None:
        pass

    def status(self) -> dict[str, Any]:
        raise RuntimeError("sem equipamento (regsvr32 pendente)")


def _texto_tabela(dlg: DetalhesDialog, rotulo: str) -> str:
    for row in range(dlg.tbl.rowCount()):
        item = dlg.tbl.item(row, 0)
        if item is not None and item.text() == rotulo:
            valor = dlg.tbl.item(row, 1)
            assert valor is not None
            return valor.text()
    raise AssertionError(f"linha {rotulo} ausente")


def test_detalhes_mostra_desconectado_e_reconecta_mock(qtbot, ctx):
    ctx.bridge.driver.desconectar()
    chamadas: list[bool] = []
    dlg = DetalhesDialog(ctx.bridge, None, on_reconnect=chamadas.append)
    qtbot.addWidget(dlg)
    dlg.show()
    assert _texto_tabela(dlg, "Conexão") == "Desconectada"
    assert dlg.btn_reconectar.isVisible()

    qtbot.mouseClick(dlg.btn_reconectar, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: chamadas == [True], timeout=5000)  # mock conecta em <1s
    assert _texto_tabela(dlg, "Conexão") == "Conectada"
    assert dlg.btn_reconectar.isEnabled()
    assert dlg.btn_reconectar.text() == "Tentar reconectar"


def test_detalhes_falha_mostra_erro_vermelho(qtbot):
    bridge = CatracaBridge(driver=_DriverQueFalha(), porta="COM3")
    chamadas: list[bool] = []
    dlg = DetalhesDialog(bridge, None, on_reconnect=chamadas.append)
    qtbot.addWidget(dlg)
    dlg.show()

    qtbot.mouseClick(dlg.btn_reconectar, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: chamadas == [False], timeout=5000)
    # linha "Atenção" com o erro em vermelho (ErrorDescription/ThreadLastError)
    for row in range(dlg.tbl.rowCount()):
        rotulo = dlg.tbl.item(row, 0)
        if rotulo is not None and rotulo.text() == "Atenção":
            valor = dlg.tbl.item(row, 1)
            assert valor is not None and "sem equipamento" in valor.text()
            assert valor.foreground().color().name().lower() == "#e57373"
            return
    raise AssertionError("linha Atenção ausente após falha")


def test_detalhes_dict_legado_sem_retry(qtbot):
    dlg = DetalhesDialog({"online": True, "mock": True})
    qtbot.addWidget(dlg)
    assert not dlg.btn_reconectar.isVisible()
    assert _texto_tabela(dlg, "Conexão") == "Conectada"
    assert _texto_tabela(dlg, "Modo") == "Demonstração — sem equipamento"


def test_auto_retry_reconecta_sozinho(qtbot, dash: DashboardView, ctx):
    dash._retry_timer.setInterval(100)  # acelera o teste (prod: 2000ms)
    ctx.bridge.driver.desconectar()
    dash._refresh_status()
    assert "NÃO" in dash.lbl_compacto.text()
    qtbot.wait(1500)  # timer + thread mock
    assert ctx.bridge.status()["online"] is True
    assert "reconec" in dash.lbl_resultado.text().lower()
