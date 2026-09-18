# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec GymFlux — Fase 5.1 (Windows 64-bit, UI PySide6).

Onefile windowed (console=False), nome GymFlux. Processo principal x64 NUNCA
toca COM: fala com o helper 32-bit (henry_helper.spec) via IPC stdio.
Pathex src/ para `import gymflux`. Datas: alembic.ini + migrations + assets.
Hiddenimports: helper_client + sqlalchemy/alembic/loguru. win32com/comtypes
são EXCLUÍDOS de propósito (só o helper bundla COM). Build (Python 3.11 x64):
    pyinstaller gymflux.spec --noconfirm
"""

from pathlib import Path

block_cipher = None

# ícone: usa src/gymflux/ui/assets/icon.ico se existir, senão sem ícone (padrão)
_icon_candidates = [
    Path("src/gymflux/ui/assets/icon.ico"),
    Path("src/gymflux/ui/assets/gymflux.ico"),
    Path("src/gymflux/ui/assets/logo.ico"),
]
icon = None
for _p in _icon_candidates:
    if _p.exists():
        icon = str(_p)
        break

# datas: só inclui se existir em dev (evita erro de build Linux sem ui)
datas = []
if Path("alembic.ini").exists():
    datas.append(("alembic.ini", "."))
# migrations sempre existem em dev; em bundle vão para _MEIPASS/src/gymflux/infra/migrations
# (alembic.ini %(here)s aponta para lá)
if Path("src/gymflux/infra/migrations").exists():
    datas.append(("src/gymflux/infra/migrations", "src/gymflux/infra/migrations"))
if Path("src/gymflux/ui/assets").exists():
    datas.append(("src/gymflux/ui/assets", "src/gymflux/ui/assets"))
# LICENSE para About dialog quando possível
if Path("LICENSE").exists():
    datas.append(("LICENSE", "."))


a = Analysis(
    ["src/gymflux/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # IPC com o helper 32-bit (processo x64 nunca importa COM direto)
        "gymflux.hardware.henry7x.helper_client",
        # infra
        "sqlalchemy",
        "sqlalchemy.sql.default_comparator",
        "sqlalchemy.ext.declarative",
        "alembic",
        "alembic.config",
        # util
        "loguru",
        "platformdirs",
        "pydantic",
        "pydantic_settings",
        "pefile",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # COM 32-bit mora SÓ no helper (henry_helper.spec); fora do exe x64.
    excludes=[
        "tests",
        "pytest",
        "pytest_qt",
        "pytest_mock",
        "win32com",
        "pythoncom",
        "pywintypes",
        "comtypes",
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
    name="GymFlux",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
