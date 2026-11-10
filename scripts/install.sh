#!/usr/bin/env bash
# Installe le skill maieutik pour Claude Code et/ou Codex.
#
# Usage : scripts/install.sh [claude|codex|all] [--project]
#   claude    ~/.claude/skills/maieutik   (Claude Code)
#   codex     ~/.agents/skills/maieutik   (Codex)
#   all       les deux (par défaut)
#   --project installe dans le dossier courant (.claude/skills, .agents/skills)
set -euo pipefail

target="all"
base="$HOME"
for arg in "$@"; do
  case "$arg" in
    claude|codex|all) target="$arg" ;;
    --project) base="$PWD" ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Argument inconnu : $arg" >&2; exit 1 ;;
  esac
done

src="$(cd "$(dirname "$0")/.." && pwd)/skills/maieutik"
[ -f "$src/SKILL.md" ] || { echo "SKILL.md introuvable dans $src" >&2; exit 1; }

install_to() {
  local dest="$1"
  rm -rf "$dest"
  mkdir -p "$dest"
  cp -R "$src/." "$dest/"
  find "$dest" -name '__pycache__' -type d -prune -exec rm -rf {} +
  echo "Installé : $dest"
}

case "$target" in
  claude|all) install_to "$base/.claude/skills/maieutik" ;;
esac
case "$target" in
  codex|all) install_to "$base/.agents/skills/maieutik" ;;
esac

echo "Terminé. Redémarrer l'agent ou recharger les skills si nécessaire."
