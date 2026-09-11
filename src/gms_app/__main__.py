"""Entry point CLI `gms` — Fase 0 mock demo, sem deps pesadas."""

from __future__ import annotations

import argparse
import sys


def cmd_mock_demo(_args: argparse.Namespace) -> int:
    from gms_app.hardware.henry7x.factory import get_henry_driver
    from gms_app.hardware.henry7x.interface import Direcao

    driver = get_henry_driver()
    print(f"[GMS] Driver: {driver.__class__.__name__} (mock={driver.is_mock})")
    print("[GMS] Conectando...")
    ok = driver.conectar(porta="MOCK:1")
    print(f"[GMS] conectar() -> {ok} | status={driver.status()}")

    print("[GMS] Liberando catraca (ENTRADA)...")
    res = driver.liberar(Direcao.ENTRADA)
    print(f"[GMS] liberar() -> {res}")

    def on_giro(direcao, ts):
        print(f"[EVENTO] giro detectado direcao={direcao} ts={ts}")

    driver.on_giro(on_giro)
    print("[GMS] Aguardando giro simulado (2s)...")
    import time

    time.sleep(2.5)
    print(f"[GMS] status final: {driver.status()}")
    driver.desconectar()
    print("[GMS] desconectado.")
    return 0


def cmd_info(_args: argparse.Namespace) -> int:
    import platform
    import struct

    print("GMS — Gym Management System")
    print(f"  Python: {platform.python_version()} ({struct.calcsize('P') * 8}-bit)")
    print(f"  Platform: {sys.platform} / {platform.machine()}")
    print(f"  Executable: {sys.executable}")
    from gms_app.config.settings import get_settings

    s = get_settings()
    print(f"  Settings: mock={s.henry_mock} dll={s.henry_dll_path} db={s.db_url}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gms", description="GMS — Gym Management System")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("mock-demo", help="demonstra hardware mockado (Linux)")
    sp.set_defaults(func=cmd_mock_demo)

    sp2 = sub.add_parser("info", help="mostra info do ambiente")
    sp2.set_defaults(func=cmd_info)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
