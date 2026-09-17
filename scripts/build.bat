@echo off
REM GymFlux build Windows — PyInstaller + Inno Setup (Fase 5)
REM Uso: scripts\build.bat
REM Saida: dist\GymFlux.exe + dist\installer\GymFlux-Setup-vX.Y.Z.exe (se ISCC no PATH)
REM Pre-reqs: Python 3.11 x86 + uv + Inno Setup 6

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
echo [build] GymFlux v%VERSION%

REM --- python bits ---
python -c "import struct; print(struct.calcsize('P')*8)" 2>nul
if %errorlevel% neq 0 (
    echo [aviso] python nao detectado
) else (
    for /f "delims=" %%b in ('python -c "import struct; print(struct.calcsize('P')*8)"') do set BITS=%%b
    echo [build] Python bits: !BITS!
    if not "!BITS!"=="32" echo [aviso] Python nao e 32-bit - COM Henry 7x so testavel em 32-bit!
)

REM --- uv sync ---
where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo [build] uv sync --extra ui ...
    uv sync --extra ui
    if %errorlevel% neq 0 ( popd & exit /b 1 )
) else (
    echo [aviso] uv nao encontrado - pulando uv sync
)

REM --- PyInstaller ---
if not exist gymflux.spec (
    echo [erro] gymflux.spec nao encontrado
    popd & exit /b 1
)
where uv >nul 2>&1
if %errorlevel% equ 0 (
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
        echo [erro] pyinstaller nao encontrado
        popd & exit /b 1
    )
)

if exist dist\GymFlux.exe (
    echo [build] OK dist\GymFlux.exe
    dir dist\GymFlux.exe
) else (
    echo [aviso] dist\GymFlux.exe nao encontrado apos PyInstaller
)

REM --- Inno Setup (ISCC) ---
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
echo   dist\GymFlux.exe
echo   dist\installer\GymFlux-Setup-v%VERSION%.exe (se Inno Setup instalado)
popd
endlocal
