# Installe le skill maieutik pour Claude Code et/ou Codex (Windows PowerShell).
#
# Usage : .\scripts\install.ps1 [-Target claude|codex|all] [-Project]
param(
    [ValidateSet("claude", "codex", "all")]
    [string]$Target = "all",
    [switch]$Project
)

$ErrorActionPreference = "Stop"
$base = if ($Project) { (Get-Location).Path } else { $HOME }
$src = Join-Path (Split-Path -Parent $PSScriptRoot) "skills\maieutik"

if (-not (Test-Path (Join-Path $src "SKILL.md"))) {
    throw "SKILL.md introuvable dans $src"
}

function Install-To([string]$dest) {
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item -Recurse -Force (Join-Path $src "*") $dest
    Get-ChildItem -Path $dest -Recurse -Directory -Filter "__pycache__" |
        Remove-Item -Recurse -Force
    Write-Host "Installé : $dest"
}

if ($Target -in @("claude", "all")) { Install-To (Join-Path $base ".claude\skills\maieutik") }
if ($Target -in @("codex", "all")) { Install-To (Join-Path $base ".agents\skills\maieutik") }

Write-Host "Terminé. Redémarrer l'agent ou recharger les skills si nécessaire."
