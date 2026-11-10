"""Outils locaux de l'agent : exécuter du code, lancer les tests, déposer un défi.

Ces fonctions ne dépendent pas du SDK, elles sont donc testables seules.
Tout chemin est confiné au dossier de travail de l'élève.
"""

from __future__ import annotations

import difflib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OUTPUT_LIMIT = 4000
DIFF_LIMIT = 3000
TESTS_TIMEOUT = 60
RUN_TIMEOUT = 30
CHALLENGE_NAME = re.compile(r"test_[a-z0-9_]+\.py")

MAX_FILE_BYTES = 2_000_000
MAX_WRITE_BYTES = 500_000
DEFAULT_READ_LINES = 400
MAX_READ_LINES = 2000
MAX_LINE_CHARS = 400
LIST_LIMIT = 200
SEARCH_LIMIT = 50
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", ".maieutik",
}
PROTECTED_DIRS = {".git", ".maieutik"}
ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template", ".env.dist"}
SECRET_NAMES = {"id_rsa", "id_ed25519", "id_ecdsa", "id_dsa", ".netrc", ".npmrc", ".pypirc", "credentials"}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


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


# --- lecture confinée ----------------------------------------------------------


def is_sensitive(path: Path | str) -> bool:
    """Fichiers qui contiennent typiquement des secrets : l'agent ne les lit ni ne les écrit."""
    name = Path(path).name.lower()
    if name.startswith(".env"):
        return name not in ENV_TEMPLATES
    return name in SECRET_NAMES or name.endswith(SECRET_SUFFIXES)


def _refuse_sensitive(relative: str) -> ToolError:
    return ToolError(
        f"« {relative} » peut contenir des secrets (clés, mots de passe) : je ne le lis pas "
        "et je ne l'écris pas. Utilise un fichier modèle comme .env.example, sans vraies valeurs."
    )


def _is_binary(path: Path) -> bool:
    with path.open("rb") as handle:
        return b"\0" in handle.read(8192)


def _read_text_file(workspace: Path | str, relative: str) -> tuple[Path, str]:
    target = resolve_in_workspace(workspace, relative)
    if is_sensitive(target):
        raise _refuse_sensitive(relative)
    if not target.is_file():
        raise ToolError(f"Fichier introuvable : {relative}")
    if target.stat().st_size > MAX_FILE_BYTES:
        raise ToolError(f"« {relative} » est trop gros ({target.stat().st_size // 1024} Ko).")
    if _is_binary(target):
        raise ToolError(f"« {relative} » est un fichier binaire.")
    return target, target.read_bytes().decode("utf-8", errors="replace")


def read_file(
    workspace: Path | str, path: str, start: int = 1, limit: int = DEFAULT_READ_LINES
) -> str:
    """Lit un fichier texte du projet, avec numéros de ligne."""
    if start < 1 or not 1 <= limit <= MAX_READ_LINES:
        raise ToolError(f"start doit valoir au moins 1 et limit être entre 1 et {MAX_READ_LINES}.")
    _, text = _read_text_file(workspace, path)
    lines = text.splitlines()
    if not lines:
        return "(fichier vide)"
    if start > len(lines):
        raise ToolError(f"Le fichier n'a que {len(lines)} lignes.")
    chunk = lines[start - 1 : start - 1 + limit]
    out = []
    for number, line in enumerate(chunk, start):
        shown = line if len(line) <= MAX_LINE_CHARS else line[:MAX_LINE_CHARS] + "…"
        out.append(f"{number:>5}\t{shown}")
    remaining = len(lines) - (start - 1 + len(chunk))
    if remaining > 0:
        out.append(f"[... {remaining} lignes de plus : relis avec start={start + len(chunk)}]")
    return "\n".join(out)


def _walk_files(base: Path, start: Path):
    """Fichiers sous ``start``, sans les dossiers techniques, dans un ordre stable."""
    if start.is_file():
        yield start
        return
    for root, dirs, files in os.walk(start):
        dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
        for name in sorted(files):
            yield Path(root) / name


def list_files(workspace: Path | str, path: str = ".") -> str:
    """Liste les fichiers du projet (sans .git, node_modules, etc.)."""
    base = Path(workspace).resolve()
    start = resolve_in_workspace(base, path or ".")
    if not start.exists():
        raise ToolError(f"Introuvable : {path}")
    names = []
    for file in _walk_files(base, start):
        label = file.relative_to(base).as_posix()
        names.append(label + ("  (non lisible : secrets)" if is_sensitive(file) else ""))
    if not names:
        return "(aucun fichier)"
    shown = names[:LIST_LIMIT]
    if len(names) > LIST_LIMIT:
        shown.append(f"[... {len(names) - LIST_LIMIT} fichiers de plus : précise un sous-dossier]")
    return "\n".join(shown)


def search_text(
    workspace: Path | str, pattern: str, path: str = ".", ignore_case: bool = False
) -> str:
    """Cherche une expression régulière dans les fichiers texte du projet."""
    try:
        regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    except re.error as exc:
        raise ToolError(f"Expression régulière invalide : {exc}") from exc
    base = Path(workspace).resolve()
    start = resolve_in_workspace(base, path or ".")
    if not start.exists():
        raise ToolError(f"Introuvable : {path}")
    hits: list[str] = []
    total = 0
    for file in _walk_files(base, start):
        try:
            resolved = file.resolve()
            if (
                is_sensitive(file)
                or (resolved != base and base not in resolved.parents)
                or not file.is_file()
                or file.stat().st_size > MAX_FILE_BYTES
                or _is_binary(file)
            ):
                continue
            text = file.read_bytes().decode("utf-8", errors="replace")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if regex.search(line[:MAX_LINE_CHARS]):
                total += 1
                if len(hits) < SEARCH_LIMIT:
                    shown = line.strip()[:200]
                    hits.append(f"{file.relative_to(base).as_posix()}:{number}: {shown}")
    if not hits:
        return "Aucun résultat."
    if total > len(hits):
        hits.append(f"[... {total - len(hits)} résultats de plus : affine la recherche]")
    return "\n".join(hits)


# --- écriture confinée ---------------------------------------------------------


def _diff(relative: str, before: str, after: str) -> tuple[str, int, int]:
    lines = list(
        difflib.unified_diff(
            before.splitlines(), after.splitlines(),
            fromfile=f"a/{relative}", tofile=f"b/{relative}", n=2, lineterm="",
        )
    )
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    return truncate("\n".join(lines), DIFF_LIMIT), added, removed


def _writable_target(workspace: Path | str, relative: str) -> Path:
    if not (relative or "").strip():
        raise ToolError("Chemin vide.")
    base = Path(workspace).resolve()
    target = resolve_in_workspace(base, relative)
    if target == base or target.is_dir():
        raise ToolError(f"« {relative} » est un dossier, pas un fichier.")
    parts = target.relative_to(base).parts
    if any(part in PROTECTED_DIRS for part in parts):
        raise ToolError(
            f"Écriture refusée dans {parts[0]}/ : ce dossier est géré à part "
            "(le journal et la progression passent par leurs propres outils)."
        )
    if is_sensitive(target):
        raise _refuse_sensitive(relative)
    return target


def _atomic_write(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".maieutik-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        if target.exists():
            shutil.copymode(target, tmp_name)
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def write_file(
    workspace: Path | str, path: str, content: str, overwrite: bool = False
) -> str:
    """Crée un fichier. Ne remplace un fichier existant que si ``overwrite`` est vrai."""
    target = _writable_target(workspace, path)
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        raise ToolError(f"Contenu trop gros (plus de {MAX_WRITE_BYTES // 1000} Ko) : découpe en plusieurs fichiers.")
    if content and not content.endswith("\n"):
        content += "\n"
    if target.exists():
        if not overwrite:
            raise ToolError(
                f"« {path} » existe déjà : modifie-le avec edit_file, "
                "ou demande overwrite=true pour le remplacer en entier."
            )
        before = target.read_bytes().decode("utf-8", errors="replace")
        diff, added, removed = _diff(path, before, content)
        _atomic_write(target, content.encode("utf-8"))
        return f"Remplacé : {path} (+{added} −{removed})\n{diff}"
    _atomic_write(target, content.encode("utf-8"))
    return f"Créé : {path} ({len(content.splitlines())} lignes)"


def edit_file(
    workspace: Path | str, path: str, old: str, new: str, replace_all: bool = False
) -> str:
    """Remplace un texte exact dans un fichier existant et renvoie le diff."""
    target = _writable_target(workspace, path)
    if not target.is_file():
        raise ToolError(f"Fichier introuvable : {path} (pour en créer un, utilise write_file).")
    if not old:
        raise ToolError("Le texte à remplacer est vide.")
    if old == new:
        raise ToolError("Le nouveau texte est identique à l'ancien : rien à changer.")
    try:
        before = target.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ToolError(f"« {path} » n'est pas un fichier texte UTF-8.") from exc
    count = before.count(old)
    if count == 0:
        raise ToolError("Texte introuvable : vérifie l'orthographe et l'indentation exactes.")
    if count > 1 and not replace_all:
        raise ToolError(
            f"Ce texte apparaît {count} fois : ajoute du contexte autour pour le rendre unique, "
            "ou demande replace_all=true."
        )
    after = before.replace(old, new)
    if len(after.encode("utf-8")) > MAX_WRITE_BYTES:
        raise ToolError("Le fichier deviendrait trop gros.")
    _atomic_write(target, after.encode("utf-8"))
    diff, added, removed = _diff(path, before, after)
    return f"Modifié : {path} (+{added} −{removed})\n{diff}"
