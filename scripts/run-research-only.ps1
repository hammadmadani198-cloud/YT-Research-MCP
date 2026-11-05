# Start the existing Phase-8 MCP with only research tools visible.
# The two intent-only watch tools remain installed but hidden.
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:YTNMCP_RESEARCH_ONLY = '1'
Push-Location $ProjectRoot
try {
    & '.\.venv\Scripts\python.exe' -m youtube_niche_mcp.server
    $ServerExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $ServerExit
