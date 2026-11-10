#!/usr/bin/env python3
"""Copie src/maieutik/progress.py dans le skill.

Le skill doit rester autonome (installé seul dans ~/.claude/skills ou ~/.agents/skills,
sans le paquet Python). Son script de suivi est donc une copie conforme du module du
paquet, qui reste la source. Lancer ce script après toute modification de progress.py ;
tests/test_skill.py échoue si les deux fichiers divergent.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "maieutik" / "progress.py"
COPY = ROOT / "skills" / "maieutik" / "scripts" / "progress.py"


def main() -> None:
    COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, COPY)
    print(f"copié : {COPY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
