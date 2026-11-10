#!/usr/bin/env python3
"""Construit l'archive du skill pour l'import dans Claude (claude.ai, Desktop).

dist/maieutik-skill.zip contient le dossier maieutik/ à la racine de l'archive.
Option : --out DOSSIER pour écrire ailleurs que dans dist/.
"""

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "maieutik"


def add_tree(archive: zipfile.ZipFile, source: Path, arcroot: str) -> None:
    for path in sorted(source.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        archive.write(path, f"{arcroot}/{path.relative_to(source).as_posix()}")


def build(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    skill_zip = out / "maieutik-skill.zip"
    with zipfile.ZipFile(skill_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        add_tree(archive, SKILL, "maieutik")
    return skill_zip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    path = build(args.out)
    print(f"{path}  ({path.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
