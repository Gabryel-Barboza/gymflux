"""Fase 5.1 — IPC do helper 32-bit (via mock, sem DLL).

Sobe ``helper_main.py`` como subprocesso (mesmo protocolo do
``GymFlux.HardwareHelper.exe``) e valida conectar/liberar/status/giro via
``Henry7xHelperClient``. Sem DLL: falha graciosa (RuntimeError no conectar,
status offline sem levantar).
"""

from __future__ import annotations

import struct
import subprocess
import sys
import threading

import pytest

from gymflux.hardware.henry7x.helper_client import Henry7xHelperClient, resolve_helper_cmd
from gymflux.hardware.henry7x.interface import Direcao, ResultadoCatraca


def _mock_cmd() -> list[str]:
    return [
        sys.executable,
        "-m",
        "gymflux.hardware.henry7x.helper_main",
        "--mock",
        "--giro-delay-s",
        "0.05",
    ]


def _make_client() -> Henry7xHelperClient:
    return Henry7xHelperClient(cmd=_mock_cmd(), stderr=subprocess.DEVNULL)


def test_resolve_helper_cmd_explicito():
    cmd = [sys.executable, "-m", "x"]
    assert resolve_helper_cmd(cmd) == cmd


def test_resolve_helper_cmd_sem_exe(monkeypatch, tmp_path):
    monkeypatch.delenv("GYMFLUX_HELPER_EXE", raising=False)
    monkeypatch.delenv("GYMFLUX_HELPER_DIR", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python"))
    with pytest.raises(FileNotFoundError):
        resolve_helper_cmd()


def test_helper_mock_conectar_liberar_status():
    client = _make_client()
    try:
        assert client.conectar("MOCK:1") is True
        st = client.status()
        assert st["online"] is True
        assert st["via_helper"] is True
        assert client.liberar(Direcao.ENTRADA) is ResultadoCatraca.LIBERADO
        client.bloquear()
    finally:
        client.desconectar()
    assert client.status()["online"] is False


def test_helper_mock_giro_event():
    client = _make_client()
    recebido: threading.Event = threading.Event()
    dados: dict = {}
    try:
        assert client.conectar("MOCK:1") is True

        def on_giro(direcao: Direcao, ts: float) -> None:
            dados["direcao"] = direcao
            dados["ts"] = ts
            recebido.set()

        client.on_giro(on_giro)
        assert client.liberar(Direcao.ENTRADA) is ResultadoCatraca.LIBERADO
        assert recebido.wait(timeout=5.0), "giro do helper não chegou via IPC"
        assert dados["direcao"] is Direcao.ENTRADA
    finally:
        client.desconectar()


def test_helper_sem_dll_falha_graciosa():
    """Sem --mock e sem DLL: conectar levanta RuntimeError, status não levanta."""
    client = Henry7xHelperClient(
        cmd=[sys.executable, "-m", "gymflux.hardware.henry7x.helper_main"],
        stderr=subprocess.DEVNULL,
    )
    try:
        if sys.platform == "win32" and struct.calcsize("P") * 8 == 32:
            pytest.skip("sem DLL só fora de Windows 32-bit")
        with pytest.raises(RuntimeError):
            client.conectar("COM3")
        st = client.status()
        assert st["online"] is False
    finally:
        client.desconectar()


def test_factory_win64_nao_importa_win32com(monkeypatch):
    """Simula Windows 64-bit: factory tenta helper, cai p/ mock sem win32com."""
    import struct as _struct

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(_struct, "calcsize", lambda _fmt: 8)
    monkeypatch.delenv("GYMFLUX_HELPER_EXE", raising=False)
    monkeypatch.delenv("GYMFLUX_HELPER_DIR", raising=False)
    sys.modules.pop("win32com", None)
    sys.modules.pop("win32com.client", None)

    from gymflux.hardware.henry7x.factory import get_henry_driver

    driver = get_henry_driver(prefer_mock=False)
    assert driver.is_mock  # sem helper instalado -> fallback mock
    assert "win32com" not in sys.modules
    assert "win32com.client" not in sys.modules
