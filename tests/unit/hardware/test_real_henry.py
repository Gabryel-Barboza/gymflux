"""Fase 3 — driver real Henry 7x.

- Em Linux/macOS ou Python 64-bit: valida a falha graciosa (RuntimeError) e a
  regra da factory (nunca retorna o driver real fora de Windows 32-bit).
- Teste de integração com hardware real: só roda na VM Windows 32-bit com
  catraca conectada (skip automático nos demais ambientes).
"""

from __future__ import annotations

import os
import struct
import sys

import pytest


def test_real_henry_falha_graciosa_fora_de_windows():
    if sys.platform == "win32" and struct.calcsize("P") * 8 == 32:
        pytest.skip("só fora de Windows 32-bit")
    from gymflux.hardware.henry7x.real import RealHenry7x

    with pytest.raises(RuntimeError, match="Windows"):
        RealHenry7x()


def test_factory_nunca_retorna_real_fora_de_win32():
    if sys.platform == "win32" and struct.calcsize("P") * 8 == 32:
        pytest.skip("só fora de Windows 32-bit")
    from gymflux.hardware.henry7x.factory import get_henry_driver
    from gymflux.hardware.henry7x.real import RealHenry7x

    driver = get_henry_driver(prefer_mock=False)
    # Fase 5.1: win64 usa helper IPC (ou mock sem helper); nunca COM in-proc.
    assert not isinstance(driver, RealHenry7x)
    assert "win32com" not in sys.modules
    if sys.platform != "win32":
        assert driver.is_mock  # Linux: fallback mock


def test_normalizar_porta():
    from gymflux.hardware.henry7x.real import _normalizar_porta

    assert _normalizar_porta(3) == "COM3"
    assert _normalizar_porta("3") == "COM3"
    assert _normalizar_porta("com3") == "COM3"
    assert _normalizar_porta("COM3") == "COM3"
    with pytest.raises(ValueError, match="porta serial"):
        _normalizar_porta("192.168.0.100")
    with pytest.raises(ValueError, match="porta serial"):
        _normalizar_porta("MOCK:1")


_requer_hw = pytest.mark.skipif(
    sys.platform != "win32"
    or struct.calcsize("P") * 8 != 32
    or os.getenv("GYMFLUX_HENRY_HW") != "1",
    reason="requer VM Windows 32-bit + catraca (GYMFLUX_HENRY_HW=1)",
)


@_requer_hw
def test_integracao_conectar_liberar_bloquear():
    """Checklist DLL_CONTRACT §4.1 automatizado (VM Windows 32-bit)."""
    from gymflux.hardware.henry7x.interface import Direcao, ResultadoCatraca
    from gymflux.hardware.henry7x.real import RealHenry7x

    porta = os.getenv("GYMFLUX_HENRY_PORTA", "COM1")
    eventos: list = []
    driver = RealHenry7x()
    try:
        assert driver.conectar(porta)
        assert driver.status()["online"] is True
        driver.on_giro(lambda d, ts: eventos.append((d, ts)))
        assert driver.liberar(Direcao.ENTRADA) is ResultadoCatraca.LIBERADO
        driver.bloquear()
    finally:
        driver.desconectar()
    assert driver.status()["online"] is False
