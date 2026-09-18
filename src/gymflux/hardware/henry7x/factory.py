"""Factory que decide mock vs real conforme plataforma + env."""

from __future__ import annotations

import os
import struct
import sys

from loguru import logger

from gymflux.hardware.henry7x.interface import Henry7xDriver


def _modo_catraca_configurado() -> str | None:
    """Modo gravado na aba Configurações ("mock"/"real"); None se ausente/legado.

    Só vale quando o usuário escolheu explicitamente (chave existe no JSON);
    JSON legado sem a chave mantém o comportamento anterior (settings).
    """
    try:
        import json

        from gymflux.ui.config_store import ConfigStore

        store = ConfigStore()
        caminho = store.caminho
        if not caminho.exists():
            return None
        data = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "modo_catraca" not in data:
            return None
        return "mock" if store.load().modo_catraca == "mock" else "real"
    except Exception:
        return None


def get_henry_driver(prefer_mock: bool | None = None) -> Henry7xDriver:
    """Retorna driver adequado (Fase 5.1: dual-env transparente).

    - Se prefer_mock=True (ou GYMFLUX_HENRY_MOCK=1) -> MockHenry7x
    - Se prefer_mock None: env GYMFLUX_HENRY_MOCK > UiConfig.modo_catraca (Fase 5.2)
      > settings.henry_mock
    - Se sys.platform != win32 -> MockHenry7x (com aviso)
    - Se Windows 64-bit -> Henry7xHelperClient (UI x64 + helper 32-bit via IPC);
      sem helper instalado -> MockHenry7x (com aviso). NUNCA importa win32com.
    - Se Windows 32-bit -> RealHenry7x (COM in-proc); falha -> MockHenry7x.
    """
    from gymflux.config.settings import get_settings

    settings = get_settings()
    env_mock = os.getenv("GYMFLUX_HENRY_MOCK")
    if prefer_mock is None:
        if env_mock is not None:
            prefer_mock = env_mock == "1"
        else:
            modo = _modo_catraca_configurado()
            prefer_mock = (modo == "mock") if modo is not None else settings.henry_mock

    if prefer_mock:
        logger.info("Factory: usando MockHenry7x (GYMFLUX_HENRY_MOCK=1)")
        from gymflux.hardware.henry7x.mock import MockHenry7x

        return MockHenry7x()

    if sys.platform != "win32":
        logger.warning(f"Factory: platform={sys.platform} != win32 -> fallback MockHenry7x")
        from gymflux.hardware.henry7x.mock import MockHenry7x

        return MockHenry7x()

    # Aqui sys.platform == "win32" (não-win32 já retornou acima).
    bits = struct.calcsize("P") * 8
    if bits != 32:
        # Windows 64-bit: UI x64 sobe helper 32-bit oculto via IPC (Fase 5.1).
        # Este processo NUNCA importa win32com (só o helper importa).
        try:
            from gymflux.hardware.henry7x.helper_client import Henry7xHelperClient

            logger.info("Factory: usando Henry7xHelperClient (helper 32-bit via IPC)")
            return Henry7xHelperClient()
        except Exception as e:
            logger.warning(f"Factory: helper indisponível ({e}) -> fallback MockHenry7x")
            from gymflux.hardware.henry7x.mock import MockHenry7x

            return MockHenry7x()

    # Windows 32-bit + mock desativado -> tenta real
    try:
        from gymflux.hardware.henry7x.real import RealHenry7x

        dll_path = os.getenv("GYMFLUX_HENRY_DLL_PATH", settings.henry_dll_path)
        logger.info(f"Factory: usando RealHenry7x dll={dll_path}")
        return RealHenry7x(dll_path=dll_path)
    except Exception as e:
        logger.exception(f"Factory: falha ao criar RealHenry7x ({e}) -> fallback mock")
        from gymflux.hardware.henry7x.mock import MockHenry7x

        return MockHenry7x()
