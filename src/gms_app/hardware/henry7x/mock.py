"""Mock fiel da Henry 7x — roda em Linux sem DLL."""

from __future__ import annotations

import threading
import time
from typing import Any

from loguru import logger

from gms_app.hardware.henry7x.interface import (
    Direcao,
    GiroCallback,
    Henry7xDriver,
    ResultadoCatraca,
)


class MockHenry7x(Henry7xDriver):
    is_mock = True

    def __init__(self, *, auto_giro: bool = True, giro_delay_s: float = 1.0) -> None:
        self._conectado = False
        self._bloqueada = True
        self._callbacks: list[GiroCallback] = []
        self._auto_giro = auto_giro
        self._giro_delay_s = giro_delay_s
        self._ultima_liberacao: Direcao | None = None
        self._timer: threading.Timer | None = None
        self._contador_giros = 0
        self._lock = threading.Lock()

    def conectar(self, porta: str | int, timeout_ms: int = 5000) -> bool:
        with self._lock:
            logger.info(f"[MockHenry7x] conectar porta={porta} timeout={timeout_ms}ms")
            self._conectado = True
            self._bloqueada = True
        return True

    def desconectar(self) -> None:
        with self._lock:
            logger.info("[MockHenry7x] desconectar")
            self._conectado = False
            self._bloqueada = True
            if self._timer:
                self._timer.cancel()
                self._timer = None

    def liberar(self, direcao: Direcao) -> ResultadoCatraca:
        with self._lock:
            if not self._conectado:
                logger.warning("[MockHenry7x] liberar() sem conexão -> ERRO")
                return ResultadoCatraca.ERRO
            logger.info(f"[MockHenry7x] liberar direcao={direcao.name}")
            self._bloqueada = False
            self._ultima_liberacao = direcao
            if self._auto_giro:
                if self._timer:
                    self._timer.cancel()
                self._timer = threading.Timer(
                    self._giro_delay_s, self._disparar_giro, args=(direcao,)
                )
                self._timer.daemon = True
                self._timer.start()
            return ResultadoCatraca.LIBERADO

    def bloquear(self) -> None:
        with self._lock:
            logger.info("[MockHenry7x] bloquear")
            self._bloqueada = True
            if self._timer:
                self._timer.cancel()
                self._timer = None

    def on_giro(self, callback: GiroCallback) -> None:
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def off_giro(self, callback: GiroCallback) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "online": self._conectado,
                "bloqueada": self._bloqueada,
                "mock": True,
                "contador_giros": self._contador_giros,
                "ultima_liberacao": self._ultima_liberacao.name if self._ultima_liberacao else None,
                "firmware": "MOCK-0.1.0",
            }

    # teste helper — dispara giro manualmente
    def simular_giro(self, direcao: Direcao | None = None) -> None:
        d = direcao or self._ultima_liberacao or Direcao.ENTRADA
        self._disparar_giro(d)

    def _disparar_giro(self, direcao: Direcao) -> None:
        cbs: list[GiroCallback]
        with self._lock:
            if self._bloqueada:
                logger.info("[MockHenry7x] giro ignorado — catraca bloqueada")
                return
            self._contador_giros += 1
            self._bloqueada = True  # catraca trava após giro
            cbs = list(self._callbacks)
            logger.info(f"[MockHenry7x] giro! direcao={direcao.name} total={self._contador_giros}")
        ts = time.time()
        for cb in cbs:
            try:
                cb(direcao, ts)
            except Exception as e:
                logger.exception(f"callback giro falhou: {e}")
