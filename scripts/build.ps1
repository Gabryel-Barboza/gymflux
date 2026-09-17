# GymFlux build Windows — PyInstaller + Inno Setup (Fase 5)
# Uso (PowerShell 5+ / pwsh):
#   pwsh scripts/build.ps1
#   pwsh scripts/build.ps1 -SkipUvSync
# Saída:
#   dist/GymFlux.exe
#   dist/installer/GymFlux-Setup-vX.Y.Z.exe (se Inno Setup no PATH)
# Pré-reqs: Python 3.11 x86 + uv + (opcional) Inno Setup 6 (iscc.exe no PATH)

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
Write-Host "[build] GymFlux v$Version" -ForegroundColor Cyan
Write-Host "[build] Root: $Root"

# 2) verifica Python 32-bit (obrigatório para COM kernel7x.dll)
try {
    $bits = & python -c "import struct; print(struct.calcsize('P')*8)" 2>$null
    if ($bits) { Write-Host "[build] Python bits: $bits" }
    if ($bits -and $bits.Trim() -ne "32") {
        Write-Host "[aviso] Python não é 32-bit (detectado $bits-bit). Build da UI funciona, mas COM Henry 7x só testável em 32-bit!" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[aviso] não foi possível detectar bits do Python: $_" -ForegroundColor Yellow
}

# 3) uv sync
if (-not $SkipUvSync) {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "[build] uv sync --extra ui ..." -ForegroundColor DarkCyan
        uv sync --extra ui
        if ($LASTEXITCODE -ne 0) { throw "uv sync falhou ($LASTEXITCODE)" }
    } else {
        Write-Host "[aviso] uv não encontrado no PATH — pulando uv sync (instale https://docs.astral.sh/uv/)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[build] SkipUvSync ativo — pulando uv sync"
}

# 4) PyInstaller
$spec = Join-Path $Root "gymflux.spec"
if (-not (Test-Path $spec)) { throw "gymflux.spec não encontrado" }

# prefere `uv run pyinstaller` se uv disponível, senão pyinstaller direto
$pyinstallerOk = $false
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "[build] uv run pyinstaller gymflux.spec --noconfirm ..." -ForegroundColor DarkCyan
    uv run pyinstaller gymflux.spec --noconfirm
    $pyinstallerOk = ($LASTEXITCODE -eq 0)
    if (-not $pyinstallerOk) { throw "pyinstaller falhou ($LASTEXITCODE)" }
} elseif (Get-Command pyinstaller -ErrorAction SilentlyContinue) {
    Write-Host "[build] pyinstaller gymflux.spec --noconfirm ..." -ForegroundColor DarkCyan
    pyinstaller gymflux.spec --noconfirm
    $pyinstallerOk = ($LASTEXITCODE -eq 0)
    if (-not $pyinstallerOk) { throw "pyinstaller falhou ($LASTEXITCODE)" }
} else {
    throw "pyinstaller não encontrado (uv sync --group dev instala)"
}

$exe = Join-Path $Root "dist\GymFlux.exe"
if (Test-Path $exe) {
    Write-Host "[build] OK dist\GymFlux.exe" -ForegroundColor Green
    Get-Item $exe | Format-List Name, Length, LastWriteTime
} else {
    # PyInstaller onefile windowed gera dist/GymFlux.exe (sem .lower?) — verifica case alternativo
    $alt = Join-Path $Root "dist\GymFlux.exe"
    if (Test-Path $alt) { Write-Host "[build] OK $alt" -ForegroundColor Green }
    else { Write-Host "[aviso] dist\GymFlux.exe não encontrado após PyInstaller" -ForegroundColor Yellow }
}

# 5) Inno Setup (iscc)
$iss = Join-Path $Root "installer\gymflux.iss"
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) { $iscc = Get-Command ISCC -ErrorAction SilentlyContinue }
# caminho padrão do Inno Setup 6 no Windows
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
Write-Host "  dist\GymFlux.exe"
Write-Host "  dist\installer\GymFlux-Setup-v$Version.exe (se Inno Setup instalado)"
