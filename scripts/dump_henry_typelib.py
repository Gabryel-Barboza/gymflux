#!/usr/bin/env python3
"""Despeja records/constantes da typelib Kernel7x.Kernel (Windows, ideal 32-bit).

Validado em Windows 10 64-bit (WOW64): o ProgID registrado é
``Kernel7x.Kernel`` (``Henry.Kernel7x`` NÃO existe — ver docs/DLL_CONTRACT.md).

Uso na VM de commissioning (Fase 3):

    C:\\Windows\\SysWOW64\\regsvr32 vendor\\Henry\\Henry7x\\Kernel7x.dll  (Admin)
    uv sync --group dev --extra windows  (com Python 32-bit se possível)
    uv run python scripts/dump_henry_typelib.py > dumps\\henry_typelib.txt

Roda em Windows 64-bit também (WOW64 carrega a DLL 32-bit), mas para
resultado completo use Python 32-bit. Em 64-bit o script tenta do mesmo
jeito e avisa se a typelib não carregar.

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

CONST_PREFIXES = (
    "csg",
    "can",
    "cb",
    "cv",
    "cmc",
    "ctc",
    "cl",
    "cca",
    "cg",
    "ctr",
    "cds",
    "cts",
    "cao",
    "sfr",
    "caf",
    "cme",
    "cp",
    "hcp",
)

# Ordem validada em Windows 10 (WOW64): Henry.Kernel7x NÃO existe no registro.
PROG_IDS = ("Kernel7x.Kernel", "Kernel7x.Hamster", "Kernel7x.Alternativo", "Henry.Kernel7x")


def main() -> int:
    if sys.platform != "win32":
        print("Disponível apenas em Windows (VM de commissioning).", file=sys.stderr)
        return 2
    bits = struct.calcsize("P") * 8
    if bits != 32:
        print(
            f"Aviso: Python {bits}-bit detectado. A DLL é 32-bit, então em Windows 64-bit "
            "o COM roda via WOW64. O script tentará mesmo assim; se falhar, "
            "instale Python 3.11 32-bit e rode novamente.",
            file=sys.stderr,
        )
    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError:
        print("pywin32 não instalado — uv sync --extra windows", file=sys.stderr)
        return 2

    com = None
    ultimo_erro: Exception | None = None
    for pid in PROG_IDS:
        try:
            try:
                com = win32com.client.gencache.EnsureDispatch(pid)
            except Exception:
                com = win32com.client.Dispatch(pid)
            print(f"ProgID usado: {pid}")
            break
        except Exception as e:
            ultimo_erro = e
            continue
    if com is None:
        print(
            f"Falha ao criar {PROG_IDS[0]}: {ultimo_erro} — rode regsvr32 kernel7x.dll",
            file=sys.stderr,
        )
        print(
            "Dica: confirme no registro se o ProgID existe:\n"
            "  reg query HKCR\\Kernel7x.Kernel /s\n"
            "  reg query HKLM\\SOFTWARE\\WOW6432Node\\Classes\\Kernel7x.Kernel /s\n"
            "Se não existir, registre com C:\\Windows\\SysWOW64\\regsvr32.exe como Admin.",
            file=sys.stderr,
        )
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
