"""Suivi de progression de l'élève.

Les données vivent dans ``<dossier de travail>/.maieutik/progress.json``.
Ce module ne dépend pas du SDK : il est testable seul.

Barreaux d'aide (voir prompts/help_ladder.md) :
    0 aucune aide, 1 question ou indice, 2 exemple partiel, 3 solution expliquée.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROGRESS_DIR = ".maieutik"
PROGRESS_FILE = "progress.json"
MAX_HISTORY = 5
MAX_ERRORS = 20
OUTCOMES = ("solved", "stuck")
HELP_LEVELS = (0, 1, 2, 3)
STATUS_LABELS = {
    "new": "nouveau",
    "learning": "en cours",
    "shaky": "fragile",
    "mastered": "acquis",
}


class ProgressError(ValueError):
    """Valeur invalide passée au suivi de progression."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_progress() -> dict[str, Any]:
    return {
        "version": 1,
        "level": "inconnu",
        "project": None,
        "milestone": 1,
        "concepts": {},
        "errors": [],
        "updated_at": None,
    }


def progress_path(workspace: Path | str) -> Path:
    return Path(workspace) / PROGRESS_DIR / PROGRESS_FILE


def load(workspace: Path | str) -> dict[str, Any]:
    """Charge la progression. Un fichier absent donne une progression vide.

    Un fichier illisible est mis de côté en ``.bak`` plutôt qu'écrasé en silence.
    """
    path = progress_path(workspace)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return empty_progress()
    except (json.JSONDecodeError, UnicodeDecodeError):
        path.replace(path.with_name(path.name + ".bak"))
        return empty_progress()
    if not isinstance(data, dict):
        path.replace(path.with_name(path.name + ".bak"))
        return empty_progress()
    merged = empty_progress()
    merged.update(data)
    return merged


def save(workspace: Path | str, data: dict[str, Any]) -> None:
    """Écrit la progression de façon atomique."""
    path = progress_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".progress-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def concept_status(history: list[dict[str, Any]]) -> str:
    """Déduit le statut d'un concept de ses derniers essais.

    - acquis : les deux derniers essais réussis avec au plus un indice
    - fragile : dernier essai bloqué, ou réussi seulement avec la solution
    - en cours : le reste
    """
    if not history:
        return "new"
    last = history[-1]
    if last["outcome"] == "stuck" or last["help_level"] >= 3:
        return "shaky"
    recent = history[-2:]
    if len(recent) == 2 and all(
        item["outcome"] == "solved" and item["help_level"] <= 1 for item in recent
    ):
        return "mastered"
    return "learning"


def _find_key(mapping: dict[str, Any], name: str) -> str | None:
    wanted = name.casefold()
    for key in mapping:
        if key.casefold() == wanted:
            return key
    return None


def record_concept(
    data: dict[str, Any],
    concept: str,
    outcome: str,
    help_level: int = 0,
    note: str = "",
) -> str:
    """Enregistre un essai sur un concept et renvoie son nouveau statut."""
    concept = (concept or "").strip()
    if not concept:
        raise ProgressError("Le nom du concept est vide.")
    if outcome not in OUTCOMES:
        raise ProgressError(f"Résultat invalide « {outcome} » : attendu {' ou '.join(OUTCOMES)}.")
    if help_level not in HELP_LEVELS:
        raise ProgressError(f"Barreau d'aide invalide « {help_level} » : attendu 0, 1, 2 ou 3.")

    concepts = data.setdefault("concepts", {})
    key = _find_key(concepts, concept) or concept
    entry = concepts.setdefault(key, {"history": [], "status": "new"})
    entry["history"].append({"outcome": outcome, "help_level": help_level, "at": _now()})
    entry["history"] = entry["history"][-MAX_HISTORY:]
    if note and note.strip():
        entry["note"] = note.strip()
    entry["status"] = concept_status(entry["history"])
    return entry["status"]


def record_error(data: dict[str, Any], description: str) -> int:
    """Note une erreur récurrente et renvoie le nombre d'occurrences."""
    description = (description or "").strip()
    if not description:
        raise ProgressError("La description de l'erreur est vide.")
    errors = data.setdefault("errors", [])
    for item in errors:
        if item["text"].casefold() == description.casefold():
            item["count"] += 1
            item["last_seen"] = _now()
            return item["count"]
    errors.append({"text": description, "count": 1, "last_seen": _now()})
    if len(errors) > MAX_ERRORS:
        errors.sort(key=lambda item: (item["count"], item["last_seen"]))
        del errors[0]
    return 1


def update_profile(
    data: dict[str, Any],
    level: str | None = None,
    milestone: int | None = None,
    project: str | None = None,
) -> None:
    if level is not None:
        if not level.strip():
            raise ProgressError("Le niveau est vide.")
        data["level"] = level.strip()
    if milestone is not None:
        if milestone < 1:
            raise ProgressError("Le jalon doit être supérieur ou égal à 1.")
        data["milestone"] = milestone
    if project is not None:
        data["project"] = project.strip() or None


def summary(data: dict[str, Any]) -> str:
    """Résumé lisible (en français) pour l'élève et pour l'agent."""
    lines = [
        f"Niveau estimé : {data.get('level') or 'inconnu'}",
        f"Projet : {data.get('project') or 'aucun (mode libre)'}",
        f"Jalon en cours : {data.get('milestone', 1)}",
    ]
    concepts = data.get("concepts") or {}
    if concepts:
        lines.append("Concepts :")
        for name, entry in sorted(concepts.items()):
            label = STATUS_LABELS.get(entry.get("status", "new"), "nouveau")
            history = entry.get("history") or []
            extra = f" (dernière aide : barreau {history[-1]['help_level']})" if history else ""
            lines.append(f"- {name} : {label}{extra}")
    else:
        lines.append("Concepts : aucun suivi pour l'instant (première session).")
    errors = sorted(data.get("errors") or [], key=lambda item: -item.get("count", 1))[:5]
    if errors:
        lines.append("Erreurs récurrentes :")
        for item in errors:
            lines.append(f"- {item['text']} (x{item['count']})")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="progress.py",
        description="Suivi de progression Maïeutik (.maieutik/progress.json).",
    )
    parser.add_argument(
        "--dir", default=".", help="dossier de travail de l'élève (défaut : dossier courant)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("show", help="affiche la progression")

    record = commands.add_parser("record", help="enregistre un essai sur un concept")
    record.add_argument("concept")
    record.add_argument("outcome", choices=OUTCOMES)
    record.add_argument(
        "--barreau", type=int, default=0, help="barreau d'aide le plus haut utilisé (0 à 3)"
    )
    record.add_argument("--note", default="")

    error = commands.add_parser("error", help="note une erreur récurrente")
    error.add_argument("description")

    profile = commands.add_parser("profile", help="met à jour le niveau, le jalon ou le projet")
    profile.add_argument("--level")
    profile.add_argument("--milestone", type=int)
    profile.add_argument("--project")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Interface en ligne de commande, utilisée par le skill sans le SDK."""
    args = _build_parser().parse_args(argv)
    workspace = Path(args.dir)
    if not workspace.is_dir():
        print(f"Erreur : dossier introuvable : {workspace}", file=sys.stderr)
        return 1
    try:
        data = load(workspace)
        if args.command == "show":
            print(summary(data))
            return 0
        if args.command == "record":
            status = record_concept(data, args.concept, args.outcome, args.barreau, args.note)
            message = f"Enregistré : « {args.concept.strip()} » → {STATUS_LABELS[status]}."
        elif args.command == "error":
            message = f"Erreur notée (vue {record_error(data, args.description)} fois)."
        else:
            if args.level is None and args.milestone is None and args.project is None:
                raise ProgressError("Rien à mettre à jour : précise --level, --milestone ou --project.")
            update_profile(data, args.level, args.milestone, args.project)
            message = "Profil mis à jour."
        save(workspace, data)
    except ProgressError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
