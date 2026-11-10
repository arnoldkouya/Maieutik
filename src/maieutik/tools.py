"""Outils locaux de l'agent : exécuter du code, lancer les tests, déposer un défi.

Ces fonctions ne dépendent pas du SDK, elles sont donc testables seules.
Tout chemin est confiné au dossier de travail de l'élève.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

OUTPUT_LIMIT = 4000
TESTS_TIMEOUT = 60
RUN_TIMEOUT = 30
CHALLENGE_NAME = re.compile(r"test_[a-z0-9_]+\.py")


class ToolError(Exception):
    """Erreur attendue d'un outil, dont le message est lisible par l'agent."""


def resolve_in_workspace(workspace: Path | str, relative: str) -> Path:
    """Résout un chemin et refuse tout ce qui sort du dossier de travail."""
    base = Path(workspace).resolve()
    target = (base / relative).resolve()
    if target != base and base not in target.parents:
        raise ToolError(f"Chemin refusé : « {relative} » sort du dossier de travail.")
    return target


def truncate(text: str, limit: int = OUTPUT_LIMIT) -> str:
    """Garde le début et la fin : les résumés de tests sont à la fin."""
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n[... sortie tronquée ...]\n{text[-half:]}"


def _run(workspace: Path, argv: list[str], timeout: int) -> tuple[int | None, str]:
    python_path = os.pathsep.join(filter(None, [str(workspace), os.environ.get("PYTHONPATH")]))
    env = {**os.environ, "PYTHONPATH": python_path, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = subprocess.run(
            argv,
            cwd=workspace,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return None, (
            f"Temps dépassé ({timeout} s) : le programme tourne encore. "
            "Boucle infinie, ou attente d'une saisie ?"
        )
    output = (proc.stdout + proc.stderr).strip() or "(aucune sortie)"
    return proc.returncode, truncate(output)


def _format(code: int | None, output: str) -> str:
    if code is None:
        return output
    return f"code de sortie : {code}\n{output}"


def run_tests(workspace: Path | str, path: str = "", timeout: int = TESTS_TIMEOUT) -> str:
    """Lance pytest sur le dossier de travail (ou sur un sous-chemin)."""
    base = Path(workspace).resolve()
    target = resolve_in_workspace(base, path or ".")
    if not target.exists():
        raise ToolError(f"Introuvable : {path}")
    argv = [sys.executable, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider", str(target)]
    code, output = _run(base, argv, timeout)
    if code == 5:
        output += "\nAucun test collecté : y a-t-il des fichiers test_*.py à cet endroit ?"
    return _format(code, output)


def run_python(workspace: Path | str, file: str, timeout: int = RUN_TIMEOUT) -> str:
    """Exécute un fichier .py du dossier de travail et renvoie sa sortie."""
    base = Path(workspace).resolve()
    target = resolve_in_workspace(base, file)
    if target.suffix != ".py":
        raise ToolError("Seuls les fichiers .py peuvent être exécutés.")
    if not target.is_file():
        raise ToolError(f"Fichier introuvable : {file}")
    return _format(*_run(base, [sys.executable, str(target)], timeout))


def write_challenge(workspace: Path | str, filename: str, content: str) -> str:
    """Dépose un test (le défi) dans tests/. N'écrase jamais un fichier existant."""
    if not CHALLENGE_NAME.fullmatch(filename or ""):
        raise ToolError("Nom invalide : utilise test_<mots_en_minuscules>.py")
    if not (content or "").strip():
        raise ToolError("Le contenu du défi est vide.")
    target = resolve_in_workspace(workspace, f"tests/{filename}")
    if target.exists():
        raise ToolError(f"tests/{filename} existe déjà : choisis un autre nom, je n'écrase rien.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    return f"Défi écrit dans tests/{filename}."
