"""Localise le dossier du skill, source unique de la méthode et des projets.

- installé depuis un wheel : copie embarquée dans ``maieutik/_skill``
- depuis le dépôt (installation éditable) : ``skills/maieutik`` à la racine
"""

from __future__ import annotations

from pathlib import Path

SKILL_NAME = "maieutik"


def skill_dir() -> Path:
    packaged = Path(__file__).parent / "_skill"
    if (packaged / "SKILL.md").is_file():
        return packaged
    source_tree = Path(__file__).resolve().parents[2] / "skills" / SKILL_NAME
    if (source_tree / "SKILL.md").is_file():
        return source_tree
    raise FileNotFoundError(
        "Dossier du skill introuvable : réinstalle le paquet (pip install -e .) "
        "depuis un clone complet du dépôt."
    )
