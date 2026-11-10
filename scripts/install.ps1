# Installe le skill maieutik pour Claude Code et/ou Codex (Windows PowerShell),
# avec le skill security-audit de Cloudflare.
#
# Usage : .\scripts\install.ps1 [-Target claude|codex|all] [-Project] [-SansAudit]
#
# Le skill security-audit (https://github.com/cloudflare/security-audit-skill, licence MIT) est
# téléchargé depuis GitHub, figé sur un commit précis. Il faut git et un accès à GitHub. Si le
# téléchargement échoue, maieutik est quand même installé et un avertissement l'indique.
#
# Variables : MAIEUTIK_SECURITY_AUDIT_URL, MAIEUTIK_SECURITY_AUDIT_REF (autre dépôt ou commit),
# MAIEUTIK_SECURITY_AUDIT_SRC (dossier local d'un clone du dépôt, sans téléchargement).
param(
    [ValidateSet("claude", "codex", "all")]
    [string]$Target = "all",
    [switch]$Project,
    [switch]$SansAudit
)

$ErrorActionPreference = "Stop"
$env:GIT_TERMINAL_PROMPT = "0"

$secUrl = if ($env:MAIEUTIK_SECURITY_AUDIT_URL) { $env:MAIEUTIK_SECURITY_AUDIT_URL } else { "https://github.com/cloudflare/security-audit-skill" }
$secRef = if ($env:MAIEUTIK_SECURITY_AUDIT_REF) { $env:MAIEUTIK_SECURITY_AUDIT_REF } else { "c1c8a8c1471069fb0e188eeaff69b8e8db6564a8" }
$secLocal = $env:MAIEUTIK_SECURITY_AUDIT_SRC

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

function Copy-Audit([string]$auditRoot, [string]$dest) {
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item -Recurse -Force (Join-Path $auditRoot "skills\security-audit\*") $dest
    $license = Join-Path $auditRoot "LICENSE"
    if (Test-Path $license) { Copy-Item -Force $license (Join-Path $dest "LICENSE") }
    Write-Host "Installé : $dest (skill security-audit de Cloudflare, licence MIT)"
}

# Télécharge (ou prend en local) le dépôt security-audit, l'installe, et nettoie. Ne lève jamais d'erreur.
function Install-Audit {
    $tmp = $null
    $ok = $false
    try {
        $ErrorActionPreference = "Continue"
        if ($secLocal) {
            $auditRoot = $secLocal
        } else {
            if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git absent" }
            $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("maieutik-audit-" + [guid]::NewGuid())
            New-Item -ItemType Directory -Path $tmp | Out-Null
            foreach ($step in @(
                @("init", "-q"),
                @("remote", "add", "origin", $secUrl),
                @("fetch", "-q", "--depth", "1", "origin", $secRef),
                @("checkout", "-q", "FETCH_HEAD")
            )) {
                & git -C $tmp @step *> $null
                if ($LASTEXITCODE -ne 0) { throw "git $($step[0]) a échoué" }
            }
            $auditRoot = $tmp
        }
        if (-not (Test-Path (Join-Path $auditRoot "skills\security-audit\SKILL.md"))) { throw "dépôt inattendu" }
        if ($Target -in @("claude", "all")) { Copy-Audit $auditRoot (Join-Path $base ".claude\skills\security-audit") }
        if ($Target -in @("codex", "all")) { Copy-Audit $auditRoot (Join-Path $base ".agents\skills\security-audit") }
        $ok = $true
    } catch {
        $ok = $false
    } finally {
        if ($tmp -and (Test-Path $tmp)) { Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue }
    }
    if (-not $ok) {
        Write-Warning ("Le skill security-audit de Cloudflare n'a pas pu être installé (git absent, pas d'accès à GitHub, ou dépôt inattendu). " +
            "Maïeutik fonctionne sans lui, mais sans l'audit de sécurité poussé. Pour l'ajouter plus tard : " +
            "npx skills add https://github.com/cloudflare/security-audit-skill --skill security-audit")
    }
}

if ($Target -in @("claude", "all")) { Install-To (Join-Path $base ".claude\skills\maieutik") }
if ($Target -in @("codex", "all")) { Install-To (Join-Path $base ".agents\skills\maieutik") }

if (-not $SansAudit) { Install-Audit }

Write-Host "Terminé. Redémarrer l'agent ou recharger les skills si nécessaire."
