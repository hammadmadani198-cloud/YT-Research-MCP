# YT Research: general YouTube metadata/video tools only.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$env:YT_RESEARCH_GENERAL = '1'
$env:YTNMCP_RESEARCH_ONLY = '1'
$env:NEXLEV_API_KEY = $null
$env:YTNMCP_DB_PATH = Join-Path $Root 'data\research.sqlite3'
$TempRoot = Join-Path $Root 'data\runtime-tmp'
New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
$env:TEMP = $TempRoot
$env:TMP = $TempRoot
$env:TMPDIR = $TempRoot
Push-Location $Root
try {
    & (Join-Path $Root '.venv\Scripts\python.exe') -m youtube_niche_mcp.server
    $code = $LASTEXITCODE
} finally { Pop-Location }
exit $code
