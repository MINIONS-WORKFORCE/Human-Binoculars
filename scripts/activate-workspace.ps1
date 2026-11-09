# Dot-source this file: . .\scripts\activate-workspace.ps1
# Node is portable and local to this workspace; no system PATH changes.
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$activateFile = Join-Path $workspaceRoot '.venv\Scripts\Activate.ps1'
if (-not (Test-Path -LiteralPath $activateFile)) {
    throw 'Missing .venv. Follow README setup first.'
}
. $activateFile
$workspaceNode = Get-ChildItem -LiteralPath (Join-Path $workspaceRoot '.venv\node') -Directory |
    Where-Object { $_.Name -like 'node-v24.*-win-x64' } |
    Sort-Object Name -Descending |
    Select-Object -First 1
if (-not $workspaceNode) {
    throw 'Missing portable Node 24 in .venv/node.'
}
if (($env:Path -split ';') -notcontains $workspaceNode.FullName) {
    $env:Path = $workspaceNode.FullName + ';' + $env:Path
}
Write-Host 'Workspace Python and Node are active in this terminal.'
