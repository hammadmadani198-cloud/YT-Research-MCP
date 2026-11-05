$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    & '.\.venv\Scripts\python.exe' -m youtube_niche_mcp.server
    $ServerExit = $LASTEXITCODE
} finally { Pop-Location }
exit $ServerExit
