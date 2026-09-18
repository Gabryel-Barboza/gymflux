@echo off
REM GymFlux build Windows — dual-env transparente (Fase 5.1)
REM Uso: scripts\build.bat
REM Saida: dist\GymFlux.exe (x64 UI) + dist\GymFlux.HardwareHelper.exe (x86 COM)
REM        + dist\installer\GymFlux-Setup-vX.Y.Z.exe (se ISCC no PATH)
REM Pre-reqs: Python 3.11 x64 (+uv) e Python 3.11 x86 p/ o helper + Inno Setup 6
REM Opcional: set GYMFLUX_PYTHON_X86=C:\Python311-32\python.exe

setlocal EnableDelayedExpansion
pushd "%~dp0.."

REM --- versao de pyproject.toml ---
set "VERSION="
for /f "usebackq tokens=*" %%a in ("pyproject.toml") do (
    echo %%a | findstr /R /C:"^version *= *" >nul
    if !errorlevel! equ 0 (
        for /f "tokens=2 delims==" %%b in ("%%a") do (
            set "line=%%b"
            set "line=!line:"=!"
            set "line=!line: =!"
            set "VERSION=!line!"
        )
    )
)
if "%VERSION%"=="" (
    echo [erro] version nao encontrado em pyproject.toml
    popd & exit /b 1
)
echo [build] GymFlux v%VERSION% (dual-env)

REM --- UI x64 ---
where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo [build] uv sync --group dev --extra ui ...
    uv sync --group dev --extra ui
    if %errorlevel% neq 0 ( popd & exit /b 1 )
    echo [build] uv run pyinstaller gymflux.spec --noconfirm ...
    uv run pyinstaller gymflux.spec --noconfirm
    if %errorlevel% neq 0 ( popd & exit /b 1 )
) else (
    where pyinstaller >nul 2>&1
    if %errorlevel% equ 0 (
        echo [build] pyinstaller gymflux.spec --noconfirm ...
        pyinstaller gymflux.spec --noconfirm
        if %errorlevel% neq 0 ( popd & exit /b 1 )
    ) else (
        echo [erro] uv/pyinstaller nao encontrado
        popd & exit /b 1
    )
)

if exist dist\GymFlux.exe (
    echo [build] OK dist\GymFlux.exe
    dir dist\GymFlux.exe
) else (
    echo [aviso] dist\GymFlux.exe nao encontrado apos PyInstaller
)

REM --- Helper x86 (venv isolado .venv32) ---
set "PYTHON_X86="
if defined GYMFLUX_PYTHON_X86 (
    if exist "%GYMFLUX_PYTHON_X86%" set "PYTHON_X86=%GYMFLUX_PYTHON_X86%"
)
if not defined PYTHON_X86 (
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        py -3.11-32 -c "import struct,sys; assert struct.calcsize('P')*8==32; print(sys.executable)" > "%TEMP%\gymflux_pyx86.txt" 2>nul
        if !errorlevel! equ 0 (
            for /f "usebackq delims=" %%p in ("%TEMP%\gymflux_pyx86.txt") do set "PYTHON_X86=%%p"
        )
        del "%TEMP%\gymflux_pyx86.txt" 2>nul
    )
)

if not defined PYTHON_X86 (
    echo [aviso] Python 3.11 32-bit nao encontrado (py -3.11-32 ou GYMFLUX_PYTHON_X86).
    echo         Helper GymFlux.HardwareHelper.exe NAO gerado — instale Python x86 ou use o CI.
) else (
    echo [build] Python x86: !PYTHON_X86!
    if not exist henry_helper.spec (
        echo [erro] henry_helper.spec nao encontrado
        popd & exit /b 1
    )
    echo [build] UV_PROJECT_ENVIRONMENT=.venv32 uv sync --group dev --extra windows ...
    set "UV_PROJECT_ENVIRONMENT=.venv32"
    uv sync --group dev --extra windows --python "!PYTHON_X86!"
    if %errorlevel% neq 0 ( set "UV_PROJECT_ENVIRONMENT=" & popd & exit /b 1 )
    echo [build] UV_PROJECT_ENVIRONMENT=.venv32 pyinstaller henry_helper.spec ...
    uv run pyinstaller henry_helper.spec --noconfirm
    if %errorlevel% neq 0 ( set "UV_PROJECT_ENVIRONMENT=" & popd & exit /b 1 )
    set "UV_PROJECT_ENVIRONMENT="
    if exist dist\GymFlux.HardwareHelper.exe (
        echo [build] OK dist\GymFlux.HardwareHelper.exe
        dir dist\GymFlux.HardwareHelper.exe
    ) else (
        echo [aviso] dist\GymFlux.HardwareHelper.exe nao encontrado apos PyInstaller
    )
)

REM --- Inno Setup (ISCC) — empacota os dois exes ---
set "ISCC="
where iscc >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%p in ('where iscc') do set ISCC=%%p
) else (
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
    if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
)

if defined ISCC (
    if exist installer\gymflux.iss (
        echo [build] "%ISCC%" installer\gymflux.iss /DMyAppVersion=%VERSION% ...
        "%ISCC%" installer\gymflux.iss /DMyAppVersion=%VERSION%
        if %errorlevel% neq 0 ( popd & exit /b 1 )
        if exist dist\installer (
            echo [build] OK dist\installer\
            dir dist\installer\*.exe
        )
    ) else (
        echo [aviso] installer\gymflux.iss nao encontrado
    )
) else (
    echo [aviso] ISCC nao encontrado - instale Inno Setup 6: https://jrsoftware.org/isinfo.php
    echo         Depois rode: iscc installer\gymflux.iss /DMyAppVersion=%VERSION%
    echo         Saida esperada: dist\installer\GymFlux-Setup-v%VERSION%.exe
)

echo [build] concluido - v%VERSION%
echo   dist\GymFlux.exe (x64 UI)
echo   dist\GymFlux.HardwareHelper.exe (x86 helper, se Python 32-bit disponivel)
echo   dist\installer\GymFlux-Setup-v%VERSION%.exe (se Inno Setup instalado)
popd
endlocal
