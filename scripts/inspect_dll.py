#!/usr/bin/env python3
"""Inspeciona kernel7x.dll e extrai exports, imports, strings.

Uso:
  uv run python scripts/inspect_dll.py vendor/kernel7x.dll
  uv run python scripts/inspect_dll.py --dump vendor/kernel7x.dll --output dumps/kernel7x.txt
  uv run python scripts/inspect_dll.py --strings vendor/kernel7x.dll

Funciona em Linux (via pefile) e Windows (pefile + dumpbin opcional).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def inspect_pefile(dll: Path) -> None:
    try:
        import pefile  # type: ignore[import-untyped]
    except ImportError:
        print("pefile não instalado. Rode: uv sync --group dev", file=sys.stderr)
        sys.exit(1)

    pe = pefile.PE(str(dll))
    print(f"== PE: {dll} ==")
    print(f"Machine: {hex(pe.FILE_HEADER.Machine)} ({'I386/32-bit' if pe.FILE_HEADER.Machine==0x14c else 'x64/AMD64' if pe.FILE_HEADER.Machine==0x8664 else 'outro'})")
    print(f"NumberOfSections: {pe.FILE_HEADER.NumberOfSections}")
    print(f"TimeDateStamp: {pe.FILE_HEADER.TimeDateStamp}")
    print(f"Characteristics: {hex(pe.FILE_HEADER.Characteristics)}")
    # bitness
    is_64 = pe.PE_TYPE == pefile.OPTIONAL_HEADER_MAGIC_PE_PLUS
    print(f"PE Type: {'PE32+ (64-bit)' if is_64 else 'PE32 (32-bit)'}")

    # Exports
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        print("\n-- Exports --")
        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            name = exp.name.decode(errors="ignore") if exp.name else "<ordinal>"
            print(f"  {exp.ordinal:4d} {name:40s} RVA={hex(exp.address)}")
    else:
        print("\n-- Exports: nenhum (ou stripped) --")

    # Imports
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        print("\n-- Imports --")
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll_name = entry.dll.decode(errors="ignore")
            print(f"  {dll_name}:")
            for imp in entry.imports[:20]:
                n = imp.name.decode(errors="ignore") if imp.name else f"ordinal {imp.ordinal}"
                print(f"    - {n}")
            if len(entry.imports) > 20:
                print(f"    ... +{len(entry.imports)-20} more")

    # Version info
    try:
        if hasattr(pe, "VS_VERSIONINFO"):
            print("\n-- VersionInfo presente (use --dump para detalhes) --")
    except Exception:
        pass


def dump_strings(dll: Path, pattern: str | None = None) -> None:
    print(f"\n== Strings em {dll} (filtrando {pattern or 'tudo'}) ==")
    # tenta usar `strings` binário se existir
    try:
        out = subprocess.check_output(["strings", str(dll)], text=True, errors="ignore")
        lines = out.splitlines()
    except FileNotFoundError:
        # fallback python puro: extrai sequências ASCII >=4
        data = dll.read_bytes()
        lines = re.findall(rb"[ -~]{4,}", data)
        lines = [l.decode(errors="ignore") for l in lines]

    pat = re.compile(pattern, re.IGNORECASE) if pattern else None
    filtered = [l for l in lines if pat.search(l)] if pat else lines
    for l in filtered[:500]:
        print(l)
    if len(filtered) > 500:
        print(f"... +{len(filtered)-500} linhas omitidas (use --output)")


def main() -> None:
    p = argparse.ArgumentParser(description="Inspeciona kernel7x.dll")
    p.add_argument("dll", type=Path, help="caminho para kernel7x.dll")
    p.add_argument("--dump", action="store_true", help="dump completo (pefile + strings)")
    p.add_argument("--strings", action="store_true", help="só strings")
    p.add_argument("--pattern", type=str, default=None, help="regex para filtrar strings (ex: conectar|libera)")
    p.add_argument("--output", type=Path, default=None, help="salva output em arquivo")
    args = p.parse_args()

    if not args.dll.exists():
        print(f"Arquivo não encontrado: {args.dll}", file=sys.stderr)
        sys.exit(2)

    # redireciona stdout se --output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        orig_stdout = sys.stdout
        sys.stdout = open(args.output, "w", encoding="utf-8")

    try:
        if args.strings:
            dump_strings(args.dll, args.pattern)
        else:
            inspect_pefile(args.dll)
            if args.dump:
                dump_strings(args.dll, args.pattern or r"conectar|libera|bloquea|henry|catraca|biometr|porta|baud|inicial|desconect|callback|evento|leitor|template|versao|status")
            # dica dumpbin
            print("\n-- Dica Windows: rode também `dumpbin /exports kernel7x.dll` para confirmar --")
    finally:
        if args.output:
            sys.stdout.close()  # type: ignore[attr-defined]
            sys.stdout = orig_stdout  # type: ignore[assignment]
            print(f"Dump salvo em {args.output}")


if __name__ == "__main__":
    main()
