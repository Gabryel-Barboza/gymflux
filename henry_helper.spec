# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec helper 32-bit Henry 7x — Fase 5.1 (Windows x86, sem UI).

Onefile console (console=True p/ debug; o cliente sobe oculto com
CREATE_NO_WINDOW), nome GymFlux.HardwareHelper. Roda `helper_main.py`, que
carrega kernel7x.dll via COM in-proc e fala JSON lines no stdio.
Pathex src/. Datas: nenhuma (só hardware, sem DB). Hiddenimports mínimos:
win32com (gencache p/ SComConfig/SAcionaCtrl) + comtypes (fallback) + loguru.
PySide6/SQLAlchemy/pydantic EXCLUÍDOS (helper não tem UI nem DB).
Build (Python 3.11 x86, ex.: .venv32 ou CI job build-helper):
    pyinstaller henry_helper.spec --noconfirm
"""

from pathlib import Path

block_cipher = None

_icon_candidates = [
    Path("src/gymflux/ui/assets/icon.ico"),
]
icon = None
for _p in _icon_candidates:
    if _p.exists():
        icon = str(_p)
        break

a = Analysis(
    ["src/gymflux/hardware/henry7x/helper_main.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        # COM 32-bit (pywin32) — gencache é crítico para SComConfig/SAcionaCtrl
        "win32com",
        "win32com.client",
        "win32com.client.gencache",
        "win32com.server",
        "pythoncom",
        "pywintypes",
        # fallback comtypes (SComConfig via VT_RECORD)
        "comtypes",
        "comtypes.gen",
        "comtypes.client",
        # util
        "loguru",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # helper é headless e sem DB: nada de Qt/SQLAlchemy/pydantic/testes.
    excludes=[
        "tests",
        "pytest",
        "pytest_qt",
        "pytest_mock",
        "PySide6",
        "shiboken6",
        "sqlalchemy",
        "alembic",
        "mako",
        "pydantic",
        "pydantic_settings",
        "dotenv",
        "platformdirs",
        "pefile",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="GymFlux.HardwareHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
