"""Factory que decide mock vs real conforme plataforma + env."""

from __future__ import annotations

import os
import struct
import sys

from loguru import logger

from gymflow.hardware.henry7x.interface import Henry7xDriver


def get_henry_driver(prefer_mock: bool | None = None) -> Henry7xDriver:
    """Retorna driver adequado.

    - Se GYMFLOW_HENRY_MOCK=1 ou prefer_mock=True -> MockHenry7x
    - Se sys.platform != win32 -> MockHenry7x (com aviso)
    - Se Python 64-bit -> MockHenry7x + RuntimeError opcional (DLL 32-bit não carrega)
    - Caso contrário -> RealHenry7x
    """
    from gymflow.config.settings import get_settings

    settings = get_settings()
    env_mock = os.getenv("GYMFLOW_HENRY_MOCK")
    if prefer_mock is None:
        prefer_mock = env_mock == "1" if env_mock is not None else settings.henry_mock

    if prefer_mock:
        logger.info("Factory: usando MockHenry7x (GYMFLOW_HENRY_MOCK=1)")
        from gymflow.hardware.henry7x.mock import MockHenry7x

        return MockHenry7x()

    if sys.platform != "win32":
        logger.warning(f"Factory: platform={sys.platform} != win32 -> fallback MockHenry7x")
        from gymflow.hardware.henry7x.mock import MockHenry7x

        return MockHenry7x()

    bits = struct.calcsize("P") * 8
    if bits != 32:
        logger.warning(
            f"Factory: Python {bits}-bit não pode carregar kernel7x.dll 32-bit -> MockHenry7x"
        )
        # Em prod estrito, poderíamos levantar:
        # raise RuntimeError("kernel7x.dll 32-bit requer Python 32-bit")
        from gymflow.hardware.henry7x.mock import MockHenry7x

        return MockHenry7x()

    # Windows 32-bit + mock desativado -> tenta real
    try:
        from gymflow.hardware.henry7x.real import RealHenry7x

        dll_path = os.getenv("GYMFLOW_HENRY_DLL_PATH", settings.henry_dll_path)
        logger.info(f"Factory: usando RealHenry7x dll={dll_path}")
        return RealHenry7x(dll_path=dll_path)
    except Exception as e:
        logger.exception(f"Factory: falha ao criar RealHenry7x ({e}) -> fallback mock")
        from gymflow.hardware.henry7x.mock import MockHenry7x

        return MockHenry7x()
