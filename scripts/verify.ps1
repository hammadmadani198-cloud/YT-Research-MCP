$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    & '.\.venv\Scripts\python.exe' -m youtube_niche_mcp verify
    $VerificationExit = $LASTEXITCODE
} finally { Pop-Location }
exit $VerificationExit
