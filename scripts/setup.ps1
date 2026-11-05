param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    & $PythonExe -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12+ required'"
    if ($LASTEXITCODE -ne 0) { throw 'Python version check failed' }
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        & $PythonExe -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements-dev.lock
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    & '.\.venv\Scripts\python.exe' -m pip install --no-build-isolation --no-deps -e '.[dev]'
    if ($LASTEXITCODE -ne 0) { throw 'Package installation failed' }
    Write-Host 'Setup complete. Run scripts/verify.ps1. Initialize the DB explicitly with migrate.'
} finally { Pop-Location }
