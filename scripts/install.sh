#!/usr/bin/env bash
# Installe le skill maieutik pour Claude Code et/ou Codex, avec le skill security-audit de Cloudflare.
#
# Usage : scripts/install.sh [claude|codex|all] [--project] [--sans-audit]
#   claude        ~/.claude/skills/maieutik   (Claude Code)
#   codex         ~/.agents/skills/maieutik   (Codex)
#   all           les deux (par défaut)
#   --project     installe dans le dossier courant (.claude/skills, .agents/skills)
#   --sans-audit  n'installe pas le skill security-audit de Cloudflare
#
# Le skill security-audit (https://github.com/cloudflare/security-audit-skill, licence MIT) est
# téléchargé depuis GitHub, figé sur un commit précis : le code installé est celui qui a été relu,
# pas la dernière version de la branche. Il faut git et un accès à GitHub. Si le téléchargement
# échoue, maieutik est quand même installé et un avertissement explique comment installer l'audit.
#
# Variables : MAIEUTIK_SECURITY_AUDIT_URL, MAIEUTIK_SECURITY_AUDIT_REF (autre dépôt ou commit),
# MAIEUTIK_SECURITY_AUDIT_SRC (dossier local d'un clone du dépôt, sans téléchargement).
set -euo pipefail
export GIT_TERMINAL_PROMPT=0

SEC_URL="${MAIEUTIK_SECURITY_AUDIT_URL:-https://github.com/cloudflare/security-audit-skill}"
SEC_REF="${MAIEUTIK_SECURITY_AUDIT_REF:-c1c8a8c1471069fb0e188eeaff69b8e8db6564a8}"
SEC_LOCAL="${MAIEUTIK_SECURITY_AUDIT_SRC:-}"

target="all"
base="$HOME"
with_audit=1
for arg in "$@"; do
  case "$arg" in
    claude|codex|all) target="$arg" ;;
    --project) base="$PWD" ;;
    --sans-audit) with_audit=0 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "Argument inconnu : $arg" >&2; exit 1 ;;
  esac
done

src="$(cd "$(dirname "$0")/.." && pwd)/skills/maieutik"
[ -f "$src/SKILL.md" ] || { echo "SKILL.md introuvable dans $src" >&2; exit 1; }

tmp=""
cleanup() { if [ -n "$tmp" ]; then rm -rf "$tmp"; fi; }
trap cleanup EXIT

install_to() {
  local dest="$1"
  rm -rf "$dest"
  mkdir -p "$dest"
  cp -R "$src/." "$dest/"
  find "$dest" -name '__pycache__' -type d -prune -exec rm -rf {} +
  echo "Installé : $dest"
}

# Place le dépôt security-audit dans AUDIT_SRC (clone local ou téléchargement figé sur un commit).
fetch_audit() {
  if [ -n "$SEC_LOCAL" ]; then
    AUDIT_SRC="$SEC_LOCAL"
    return 0
  fi
  command -v git >/dev/null 2>&1 || return 1
  tmp="$(mktemp -d)" || return 1
  ( cd "$tmp" \
    && git init -q . \
    && git remote add origin "$SEC_URL" \
    && git fetch -q --depth 1 origin "$SEC_REF" \
    && git checkout -q FETCH_HEAD ) >/dev/null 2>&1 || return 1
  AUDIT_SRC="$tmp"
}

copy_audit() {
  local dest="$1"
  rm -rf "$dest"
  mkdir -p "$dest"
  cp -R "$AUDIT_SRC/skills/security-audit/." "$dest/"
  if [ -f "$AUDIT_SRC/LICENSE" ]; then
    cp "$AUDIT_SRC/LICENSE" "$dest/LICENSE"
  fi
  echo "Installé : $dest (skill security-audit de Cloudflare, licence MIT)"
}

install_audit() {
  AUDIT_SRC=""
  if ! fetch_audit || [ ! -f "$AUDIT_SRC/skills/security-audit/SKILL.md" ]; then
    {
      echo "Avertissement : le skill security-audit de Cloudflare n'a pas pu être installé"
      echo "(git absent, pas d'accès à GitHub, ou dépôt inattendu). Maïeutik fonctionne sans lui,"
      echo "mais sans l'audit de sécurité poussé. Pour l'ajouter plus tard :"
      echo "  npx skills add https://github.com/cloudflare/security-audit-skill --skill security-audit"
    } >&2
    return 0
  fi
  case "$target" in
    claude|all) copy_audit "$base/.claude/skills/security-audit" ;;
  esac
  case "$target" in
    codex|all) copy_audit "$base/.agents/skills/security-audit" ;;
  esac
}

case "$target" in
  claude|all) install_to "$base/.claude/skills/maieutik" ;;
esac
case "$target" in
  codex|all) install_to "$base/.agents/skills/maieutik" ;;
esac

if [ "$with_audit" -eq 1 ]; then
  install_audit
fi

echo "Terminé. Redémarrer l'agent ou recharger les skills si nécessaire."
