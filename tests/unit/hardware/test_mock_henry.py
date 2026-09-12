from gymflux.hardware.henry7x.factory import get_henry_driver
from gymflux.hardware.henry7x.interface import Direcao


def test_mock_henry_fluxo_basico():
    driver = get_henry_driver(prefer_mock=True)
    assert driver.is_mock
    assert driver.conectar("MOCK:1")
    assert driver.status()["online"] is True
    res = driver.liberar(Direcao.ENTRADA)
    assert res.name == "LIBERADO"
    driver.bloquear()
    assert driver.status()["bloqueada"] is True
    driver.desconectar()
    assert driver.status()["online"] is False


def test_factory_linux_forca_mock(monkeypatch):
    monkeypatch.setenv("GYMFLUX_HENRY_MOCK", "1")
    d = get_henry_driver()
    assert d.is_mock


def test_mock_henry_teclado_fila_fifo():
    from gymflux.hardware.henry7x.mock import MockHenry7x

    driver = MockHenry7x(auto_giro=False)
    assert driver.conectar("MOCK:1")
    assert driver.consumir_tecla() is None
    driver.simular_teclado("1234")
    driver.simular_teclado(" 5678 ")
    assert driver.teclas_pendentes() == ["1234", "5678"]
    assert driver.consumir_tecla() == "1234"
    assert driver.teclas_pendentes() == ["5678"]
    driver.desconectar()
