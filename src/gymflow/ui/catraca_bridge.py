"""Ponte Qt <-> Henry7xDriver — ÚNICO ponto da UI que conhece ``hardware/*``.

Views/ViewModels NUNCA importam ``hardware`` direto: falam com ``CatracaBridge``.
O driver invoca o callback de giro em thread própria (``threading.Timer`` no
mock, polling no driver real); o bridge reemite via ``Signal`` Qt, que é
thread-safe e chega na thread da GUI como queued connection.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from PySide6.QtCore import QObject, Signal

from gymflow.hardware.henry7x.factory import get_henry_driver
from gymflow.hardware.henry7x.interface import Direcao, Henry7xDriver


class CatracaBridge(QObject):
    """Adapta ``Henry7xDriver.on_giro`` para Signals Qt + expõe ações/status."""

    giro_detectado = Signal(str, float)  # (direcao nome, timestamp epoch)
    status_changed = Signal(dict)  # snapshot de driver.status()

    def __init__(
        self,
        driver: Henry7xDriver | None = None,
        porta: str = "MOCK:1",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._driver: Henry7xDriver = driver if driver is not None else get_henry_driver()
        self._porta = porta
        self._driver.on_giro(self._on_giro_thread)
        self._ultimo_resultado = ""

    # -- callback vindo de thread do driver ---------------------------------
    def _on_giro_thread(self, direcao: Direcao, ts: float) -> None:
        self.giro_detectado.emit(direcao.name, ts)

    # -- ações ---------------------------------------------------------------
    def conectar(self) -> bool:
        try:
            ok = self._driver.conectar(porta=self._porta)
        except Exception as e:
            logger.warning(f"[CatracaBridge] conectar({self._porta}) falhou: {e}")
            return False
        self.status_changed.emit(self.status())
        return ok

    def desconectar(self) -> None:
        try:
            self._driver.desconectar()
        except Exception as e:
            logger.warning(f"[CatracaBridge] desconectar falhou: {e}")
        self.status_changed.emit(self.status())

    def liberar_entrada(self) -> str:
        """Pulso físico SEM decisão (uso interno/teste). UI usa o service."""
        return self._liberar(Direcao.ENTRADA)

    def liberar_saida(self) -> str:
        return self._liberar(Direcao.SAIDA)

    def _liberar(self, direcao: Direcao) -> str:
        try:
            res = self._driver.liberar(direcao)
            self._ultimo_resultado = res.name
        except Exception as e:
            logger.warning(f"[CatracaBridge] liberar({direcao.name}) falhou: {e}")
            self._ultimo_resultado = f"ERRO: {e}"
        self.status_changed.emit(self.status())
        return self._ultimo_resultado

    def bloquear(self) -> None:
        try:
            self._driver.bloquear()
        except Exception as e:
            logger.warning(f"[CatracaBridge] bloquear() falhou: {e}")
        self.status_changed.emit(self.status())

    # -- leitura --------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        try:
            st = dict(self._driver.status())
        except Exception as e:
            logger.warning(f"[CatracaBridge] status() falhou: {e}")
            st = {"online": False, "erro": str(e)}
        st.setdefault("online", False)
        st.setdefault("bloqueada", True)
        st.setdefault("mock", bool(self._driver.is_mock))
        st["driver"] = type(self._driver).__name__
        st["porta"] = self._porta
        return st

    @property
    def driver(self) -> Henry7xDriver:
        return self._driver
