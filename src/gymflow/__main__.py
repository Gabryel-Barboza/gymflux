"""Entry point CLI `gymflow` — Fase 0 mock demo, sem deps pesadas."""

from __future__ import annotations

import argparse
import sys


def cmd_mock_demo(_args: argparse.Namespace) -> int:
    from gymflow.hardware.henry7x.factory import get_henry_driver
    from gymflow.hardware.henry7x.interface import Direcao

    driver = get_henry_driver()
    print(f"[GymFlow] Driver: {driver.__class__.__name__} (mock={driver.is_mock})")
    print("[GymFlow] Conectando...")
    ok = driver.conectar(porta="MOCK:1")
    print(f"[GymFlow] conectar() -> {ok} | status={driver.status()}")

    print("[GymFlow] Liberando catraca (ENTRADA)...")
    res = driver.liberar(Direcao.ENTRADA)
    print(f"[GymFlow] liberar() -> {res}")

    def on_giro(direcao, ts):
        print(f"[EVENTO] giro detectado direcao={direcao} ts={ts}")

    driver.on_giro(on_giro)
    print("[GymFlow] Aguardando giro simulado (2s)...")
    import time

    time.sleep(2.5)
    print(f"[GymFlow] status final: {driver.status()}")
    driver.desconectar()
    print("[GymFlow] desconectado.")
    return 0


def cmd_info(_args: argparse.Namespace) -> int:
    import platform
    import struct

    print("GymFlow — Sistema de gerenciamento para academias (Henry 7x)")
    print(f"  Python: {platform.python_version()} ({struct.calcsize('P') * 8}-bit)")
    print(f"  Platform: {sys.platform} / {platform.machine()}")
    print(f"  Executable: {sys.executable}")
    from gymflow.config.settings import get_settings

    s = get_settings()
    print(f"  Settings: mock={s.henry_mock} dll={s.henry_dll_path} db={s.db_url}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gymflow", description="GymFlow — Sistema de gerenciamento para academias"
    )
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
