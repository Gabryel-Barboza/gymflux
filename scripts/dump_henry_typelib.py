#!/usr/bin/env python3
"""Despeja records/constantes da typelib Henry.Kernel7x (só Windows 32-bit).

Uso na VM de commissioning (Fase 3):

    regsvr32 vendor\\Henry\\Henry7x\\Kernel7x.dll
    uv sync --group dev --extra windows
    uv run python scripts/dump_henry_typelib.py > dumps/henry_typelib.txt

Saída: valores das constantes (csg*/can*/cv*/cmc*/ctc*) e campos dos records
(SComConfig, SComSerial, SAcionaCtrl, SOperacaoCatraca, SResposta, SBeep).
Cole os trechos em docs/DLL_CONTRACT.md §3 e ajuste real.py se necessário.
"""

from __future__ import annotations

import struct
import sys

RECORDS = (
    "SComConfig",
    "SComSerial",
    "SComTcpip",
    "SVelocidade",
    "SAcionaCtrl",
    "SOperacaoCatraca",
    "SResposta",
    "SBeep",
    "SStatusGiro",
)

CONST_PREFIXES = ("csg", "can", "cb", "cv", "cmc", "ctc", "cl", "cca", "cg", "ctr", "cds",
                  "cts", "cao", "sfr", "caf", "cme", "cp", "hcp")


def main() -> int:
    if sys.platform != "win32" or struct.calcsize("P") * 8 != 32:
        print("Disponível apenas em Windows 32-bit (VM de commissioning).", file=sys.stderr)
        return 2
    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError:
        print("pywin32 não instalado — uv sync --extra windows", file=sys.stderr)
        return 2

    try:
        com = win32com.client.gencache.EnsureDispatch("Henry.Kernel7x")
    except Exception as e:
        print(f"Falha ao criar Henry.Kernel7x: {e} — rode regsvr32 kernel7x.dll", file=sys.stderr)
        return 1

    print("== Propriedades ==")
    for prop in ("Versao", "ListaPortasSeriais", "KernelLastError", "MoreRecentFirmware"):
        try:
            print(f"{prop} = {getattr(com, prop)!r}")
        except Exception as e:
            print(f"{prop} -> ERRO {e}")

    print("\n== Constantes ==")
    consts = win32com.client.constants
    achou = False
    for name in sorted(dir(consts)):
        if name.startswith(CONST_PREFIXES):
            try:
                print(f"{name} = {getattr(consts, name)!r}")
            except Exception as e:
                print(f"{name} -> ERRO {e}")
            achou = True
    if not achou:
        print("(nenhuma constante — makepy pode não ter carregado a typelib)")

    print("\n== Records ==")
    for rec_name in RECORDS:
        try:
            rec = win32com.client.Record(rec_name, com)
        except Exception as e:
            print(f"{rec_name} -> indisponível ({e})")
            continue
        campos = sorted(a for a in dir(rec) if not a.startswith("_"))
        print(f"{rec_name}: {', '.join(campos) if campos else '(sem campos visíveis)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
