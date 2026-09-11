"""Esqueleto RealHenry7x — COM 32-bit Henry.Kernel7x (não ctypes.WinDLL).

Descoberta 2026-09-11: Kernel7x.dll é COM/OLE (DllRegisterServer, 4 exports),
não DLL plana. Acesso real é via `win32com.client.Dispatch("Henry.Kernel7x")`
em Windows 32-bit. Serial via SComConfig + AdicionaCard. Ver docs/DLL_CONTRACT.md:30.

Este arquivo falha graciosamente em Linux.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from gymflow.hardware.henry7x.interface import (
    Direcao,
    GiroCallback,
    Henry7xDriver,
    ResultadoCatraca,
)


class RealHenry7x(Henry7xDriver):
    is_mock = False

    def __init__(self, dll_path: str | Path = "vendor/Henry/Henry7x/Kernel7x.dll") -> None:
        if sys.platform != "win32":
            raise RuntimeError("RealHenry7x disponível apenas em Windows")
        import struct

        if struct.calcsize("P") * 8 != 32:
            raise RuntimeError("RealHenry7x requer Python 32-bit (WOW64) para COM Henry.Kernel7x")

        self.dll_path: Path = Path(dll_path)
        # COM precisa estar registrado: regsvr32 Kernel7x.dll (32-bit)
        # Verificar registro é opcional — Dispatch falha se não registrado
        try:
            import win32com.client  # type: ignore[import-not-found]

            self._com = win32com.client.Dispatch("Henry.Kernel7x")
        except ImportError as e:
            raise RuntimeError("pywin32 não instalado — uv sync --extra windows") from e
        except Exception as e:  # COM não registrado ou DLL faltando
            raise RuntimeError(
                f"Falha ao criar COM Henry.Kernel7x ({e}) — rode regsvr32 {self.dll_path}"
            ) from e

        self._callbacks: list[GiroCallback] = []
        self._conectado: bool = False
        logger.info(f"[RealHenry7x] COM Henry.Kernel7x criado (dll={self.dll_path})")

    def _bind_functions(self) -> None:
        """Não necessário para COM — métodos já expostos via Dispatch.
        Manter para compat, mapeamento em docs/DLL_CONTRACT.md:30.
        Ex: self._com.AdicionaCard(SComConfig, card_id), self._com.ListaPortasSeriais
        """
        pass

    # --- API ---

    def conectar(self, porta: str | int, timeout_ms: int = 5000) -> bool:
        # Serial: porta = "COM3" ou int 3; usar SComConfig + AdicionaCard
        logger.info(f"[RealHenry7x] conectar porta={porta} timeout={timeout_ms}")
        # TODO: mapear para COM real após analisar Explicativos/ + fdb
        # Ex (pseudo):
        # cfg = self._com.CriaSComConfig()  # struct SComConfig
        # cfg.Porta = str(porta)
        # cfg.Baud = 9600
        # ok = self._com.AdicionaCard(cfg, 1)  # card 1 = catraca 1
        # self._conectado = bool(ok)
        # return self._conectado
        raise NotImplementedError(
            "RealHenry7x.conectar() serial pendente — "
            "ver docs/DLL_CONTRACT.md:30 SComConfig + AdicionaCard + ListaPortasSeriais"
        )

    def desconectar(self) -> None:
        logger.info("[RealHenry7x] desconectar")
        # TODO: self._com.RemoveCard(1) ou similar
        self._conectado = False

    def liberar(self, direcao: Direcao) -> ResultadoCatraca:
        if not self._conectado:
            return ResultadoCatraca.ERRO
        logger.info(f"[RealHenry7x] liberar {direcao.name}")
        # TODO: Envia config + libera via catraca serial
        # Henry usa Envia* / Recebe* e ColetaEventos polling — mapear direcao
        raise NotImplementedError("Implementar após mapear EnviaTipoCatraca / ColetaEventos")

    def bloquear(self) -> None:
        logger.info("[RealHenry7x] bloquear")
        # TODO: self._com.Bloqueia? / RemoveCard

    def on_giro(self, callback: GiroCallback) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)
        # TODO: se DLL usa callback nativo, registrar via ctypes.WINFUNCTYPE

    def off_giro(self, callback: GiroCallback) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def status(self) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        dll = str(self.dll_path)
        return {
            "online": self._conectado,
            "mock": False,
            "dll": dll,
            # TODO: consultar DLL: firmware, contador, etc
        }
