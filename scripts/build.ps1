# GymFlux build Windows — dual-env transparente (Fase 5.1)
# Uso (PowerShell 5+ / pwsh):
#   pwsh scripts/build.ps1
#   pwsh scripts/build.ps1 -SkipUvSync
#   $env:GYMFLUX_PYTHON_X86="C:\Python311-32\python.exe"; pwsh scripts/build.ps1
# Saída:
#   dist/GymFlux.exe (x64, UI PySide6)
#   dist/GymFlux.HardwareHelper.exe (x86, COM 32-bit oculto)
#   dist/installer/GymFlux-Setup-vX.Y.Z.exe (se Inno Setup no PATH)
# Pré-reqs: Python 3.11 x64 (+uv) e Python 3.11 x86 p/ o helper + Inno Setup 6.

param(
    [switch]$SkipUvSync
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# resolve raiz do projeto (este script está em scripts/)
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

# 1) versão de pyproject.toml (regex ^version = "x.y.z")
$pyproject = Join-Path $Root "pyproject.toml"
if (-not (Test-Path $pyproject)) { throw "pyproject.toml não encontrado em $Root" }
$raw = Get-Content $pyproject -Raw
if ($raw -match '(?m)^\s*version\s*=\s*"([^"]+)"') {
    $Version = $Matches[1]
} else {
    throw "version não encontrado em pyproject.toml"
}
Write-Host "[build] GymFlux v$Version (dual-env)" -ForegroundColor Cyan
Write-Host "[build] Root: $Root"

function Get-PythonBits($Exe) {
    try {
        $bits = & $Exe -c "import struct; print(struct.calcsize('P')*8)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $bits) { return $bits.Trim() }
    } catch { }
    return $null
}

function Invoke-PyInstaller($Spec) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "[build] uv run pyinstaller $Spec --noconfirm ..." -ForegroundColor DarkCyan
        uv run pyinstaller $Spec --noconfirm
        if ($LASTEXITCODE -ne 0) { throw "pyinstaller $Spec falhou ($LASTEXITCODE)" }
    } elseif (Get-Command pyinstaller -ErrorAction SilentlyContinue) {
        Write-Host "[build] pyinstaller $Spec --noconfirm ..." -ForegroundColor DarkCyan
        pyinstaller $Spec --noconfirm
        if ($LASTEXITCODE -ne 0) { throw "pyinstaller $Spec falhou ($LASTEXITCODE)" }
    } else {
        throw "pyinstaller não encontrado (uv sync --group dev instala)"
    }
}

# 2) UI x64 (Python atual — deve ser 64-bit p/ PySide6)
$bits = Get-PythonBits "python"
if ($bits) { Write-Host "[build] Python UI (x64 esperado): $bits-bit" }
$specUi = Join-Path $Root "gymflux.spec"
if (-not (Test-Path $specUi)) { throw "gymflux.spec não encontrado" }

if (-not $SkipUvSync) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "[build] uv sync --group dev --extra ui ..." -ForegroundColor DarkCyan
        uv sync --group dev --extra ui
        if ($LASTEXITCODE -ne 0) { throw "uv sync (ui) falhou ($LASTEXITCODE)" }
    } else {
        Write-Host "[aviso] uv não encontrado — pulando uv sync" -ForegroundColor Yellow
    }
} else {
    Write-Host "[build] SkipUvSync ativo — pulando uv sync"
}

Invoke-PyInstaller "gymflux.spec"
$exeUi = Join-Path $Root "dist\GymFlux.exe"
if (Test-Path $exeUi) {
    Write-Host "[build] OK dist\GymFlux.exe" -ForegroundColor Green
    Get-Item $exeUi | Format-List Name, Length, LastWriteTime
} else {
    Write-Host "[aviso] dist\GymFlux.exe não encontrado após PyInstaller" -ForegroundColor Yellow
}

# 3) Helper x86 (Python 32-bit isolado em .venv32)
$PythonX86 = $null
if ($env:GYMFLUX_PYTHON_X86 -and (Test-Path $env:GYMFLUX_PYTHON_X86)) {
    $PythonX86 = $env:GYMFLUX_PYTHON_X86
    Write-Host "[build] Python x86 via GYMFLUX_PYTHON_X86: $PythonX86"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        $out = & py -3.11-32 -c "import struct,sys; assert struct.calcsize('P')*8==32; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            $PythonX86 = $out.Trim().Split("`n")[-1].Trim()
            Write-Host "[build] Python x86 via py -3.11-32: $PythonX86"
        }
    } catch { }
}
if (-not $PythonX86) {
    Write-Host "[aviso] Python 3.11 32-bit não encontrado (py -3.11-32 ou GYMFLUX_PYTHON_X86)." -ForegroundColor Yellow
    Write-Host "        Helper GymFlux.HardwareHelper.exe NÃO gerado — instale Python x86 ou use o CI." -ForegroundColor Yellow
    Write-Host "        No Linux: esperado (helper só builda em Windows)." -ForegroundColor Yellow
} else {
    $specHelper = Join-Path $Root "henry_helper.spec"
    if (-not (Test-Path $specHelper)) { throw "henry_helper.spec não encontrado" }
    if (-not $SkipUvSync) {
        Write-Host "[build] UV_PROJECT_ENVIRONMENT=.venv32 uv sync --group dev --extra windows ..." -ForegroundColor DarkCyan
        $env:UV_PROJECT_ENVIRONMENT = ".venv32"
        try {
            uv sync --group dev --extra windows --python $PythonX86
            if ($LASTEXITCODE -ne 0) { throw "uv sync (.venv32) falhou ($LASTEXITCODE)" }
        } finally {
            Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue
        }
    }
    Write-Host "[build] UV_PROJECT_ENVIRONMENT=.venv32 pyinstaller henry_helper.spec ..." -ForegroundColor DarkCyan
    $env:UV_PROJECT_ENVIRONMENT = ".venv32"
    try {
        Invoke-PyInstaller "henry_helper.spec"
    } finally {
        Remove-Item Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue
    }
    $exeHelper = Join-Path $Root "dist\GymFlux.HardwareHelper.exe"
    if (Test-Path $exeHelper) {
        Write-Host "[build] OK dist\GymFlux.HardwareHelper.exe" -ForegroundColor Green
        Get-Item $exeHelper | Format-List Name, Length, LastWriteTime
    } else {
        Write-Host "[aviso] dist\GymFlux.HardwareHelper.exe não encontrado" -ForegroundColor Yellow
    }
}

# 4) Inno Setup (iscc) — empacota os dois exes
$iss = Join-Path $Root "installer\gymflux.iss"
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) { $iscc = Get-Command ISCC -ErrorAction SilentlyContinue }
if (-not $iscc) {
    $cands = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($cand in $cands) {
        if (Test-Path $cand) { $iscc = Get-Item $cand; break }
    }
}

if ($iscc -and (Test-Path $iss)) {
    $isccPath = if ($iscc.Source) { $iscc.Source } elseif ($iscc.Path) { $iscc.Path } else { "$iscc" }
    Write-Host "[build] iscc $iss /DMyAppVersion=$Version ..." -ForegroundColor DarkCyan
    & $isccPath "$iss" "/DMyAppVersion=$Version"
    if ($LASTEXITCODE -ne 0) { throw "iscc falhou ($LASTEXITCODE)" }
    $installerDir = Join-Path $Root "dist\installer"
    if (Test-Path $installerDir) {
        Write-Host "[build] OK dist\installer\" -ForegroundColor Green
        Get-ChildItem $installerDir -Filter *.exe | Format-Table Name, Length, LastWriteTime
    }
} else {
    if (-not (Test-Path $iss)) {
        Write-Host "[aviso] installer\gymflux.iss não encontrado — pulando Inno Setup" -ForegroundColor Yellow
    } elseif (-not $iscc) {
        Write-Host "[aviso] ISCC não encontrado no PATH — instale Inno Setup 6 (https://jrsoftware.org/isinfo.php) e rode: iscc installer\gymflux.iss /DMyAppVersion=$Version" -ForegroundColor Yellow
        Write-Host "        Saída esperada quando instalado: dist\installer\GymFlux-Setup-v$Version.exe" -ForegroundColor Yellow
    }
}

Write-Host "[build] concluído — v$Version" -ForegroundColor Green
Write-Host "  dist\GymFlux.exe (x64 UI)"
Write-Host "  dist\GymFlux.HardwareHelper.exe (x86 helper, se Python 32-bit disponível)"
Write-Host "  dist\installer\GymFlux-Setup-v$Version.exe (se Inno Setup instalado)"
