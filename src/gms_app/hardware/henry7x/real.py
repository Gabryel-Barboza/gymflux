"""Esqueleto RealHenry7x — só funciona em Windows 32-bit com kernel7x.dll.

Este arquivo NÃO tenta carregar a DLL em Linux — falha graciosamente.
Preencha `docs/DLL_CONTRACT.md` e complete `argtypes`/`restype` conforme
a inspeção real (dumpbin / pefile).
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from gms_app.hardware.henry7x.interface import (
    Direcao,
    GiroCallback,
    Henry7xDriver,
    ResultadoCatraca,
)


class RealHenry7x(Henry7xDriver):
    is_mock = False

    def __init__(self, dll_path: str | Path = "vendor/kernel7x.dll") -> None:
        if sys.platform != "win32":
            raise RuntimeError("RealHenry7x disponível apenas em Windows")
        import struct

        if struct.calcsize("P") * 8 != 32:
            raise RuntimeError("RealHenry7x requer Python 32-bit para carregar kernel7x.dll")

        self.dll_path: Path = Path(dll_path)
        if not self.dll_path.exists():
            raise FileNotFoundError(f"DLL não encontrada: {self.dll_path.resolve()}")

        # Carregamento stdcall (WinAPI). Henry tipicamente usa stdcall -> WinDLL
        # Se a DLL usar cdecl, troque para ctypes.CDLL
        try:
            self._dll = ctypes.WinDLL(str(self.dll_path))
        except OSError as e:
            raise RuntimeError(f"Falha ao carregar {self.dll_path}: {e}") from e

        self._callbacks: list[GiroCallback] = []
        self._conectado: bool = False

        self._bind_functions()
        logger.info(f"[RealHenry7x] DLL carregada: {self.dll_path}")

    def _bind_functions(self) -> None:
        """Declare argtypes/restype aqui após preencher DLL_CONTRACT.md.

        Exemplo (AJUSTE conforme dump real):

        self._dll.Conecta.argtypes = [ctypes.c_int, ctypes.c_int]
        self._dll.Conecta.restype = ctypes.c_int
        self._dll.LiberaCatraca.argtypes = [ctypes.c_int]
        self._dll.LiberaCatraca.restype = ctypes.c_int
        """
        # TODO: preencher após inspeção — por enquanto tenta descobrir dinamicamente
        # Se exports não existirem, falhará explicitamente no primeiro uso
        pass

    # --- API ---

    def conectar(self, porta: str | int, timeout_ms: int = 5000) -> bool:
        logger.info(f"[RealHenry7x] conectar porta={porta} timeout={timeout_ms}")
        # TODO: chamar self._dll.Conecta / Inicializa conforme contrato
        # Ex:
        # ret = self._dll.Conecta(int(porta), timeout_ms)
        # self._conectado = (ret == 0)
        # return self._conectado
        raise NotImplementedError(
            "RealHenry7x.conectar() precisa do contrato real — "
            "preencha docs/DLL_CONTRACT.md e implemente _bind_functions()"
        )

    def desconectar(self) -> None:
        logger.info("[RealHenry7x] desconectar")
        # TODO: self._dll.Desconecta()
        self._conectado = False

    def liberar(self, direcao: Direcao) -> ResultadoCatraca:
        if not self._conectado:
            return ResultadoCatraca.ERRO
        logger.info(f"[RealHenry7x] liberar {direcao.name}")
        # TODO: mapear direcao -> int esperado pela DLL
        # ret = self._dll.LiberaCatraca(1 if direcao == Direcao.ENTRADA else 2)
        # return ResultadoCatraca.LIBERADO if ret == 0 else ResultadoCatraca.ERRO
        raise NotImplementedError("Implementar após contrato")

    def bloquear(self) -> None:
        logger.info("[RealHenry7x] bloquear")
        # TODO: self._dll.BloqueiaCatraca()

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
