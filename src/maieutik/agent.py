"""Configuration de l'agent Maïeutik avec le Claude Agent SDK.

Deux modes, qu'on change en cours de session :

- ``ensemble`` (défaut) : l'utilisateur demande, l'agent code dans le projet et explique
  chaque modification (ce qui change, pourquoi, ce qu'il faut vérifier).
- ``apprendre`` : l'utilisateur code, l'agent guide. Ses outils d'écriture refusent d'agir :
  la garantie « il ne touche pas à tes fichiers » est technique, pas une simple consigne.

L'agent n'utilise AUCUN outil natif du SDK (Read, Write, Edit, Bash…). Tout passe par des
outils maison confinés au dossier du projet, qui refusent les fichiers de secrets.
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, tool

from . import progress as prog
from . import tools as tl
from .prompts import build_system_prompt

SERVER_NAME = "maieutik"
MODES = ("ensemble", "apprendre")
DEFAULT_MODE = "ensemble"
WRITE_TOOLS = ("write_file", "edit_file")
CUSTOM_TOOLS = (
    "read_file",
    "list_files",
    "search_text",
    "write_file",
    "edit_file",
    "run_tests",
    "run_python",
    "write_challenge",
    "get_progress",
    "record_progress",
    "record_error",
    "update_profile",
    "log_change",
)
FORBIDDEN_BUILTINS = (
    "Read", "Glob", "Grep", "Write", "Edit", "MultiEdit", "NotebookEdit",
    "Bash", "WebFetch", "WebSearch",
)
LEARN_MODE_REFUSAL = (
    "Mode apprendre : je ne modifie pas tes fichiers, c'est à toi de le faire. "
    "Dis /ensemble pour que je code à ta place en t'expliquant chaque changement."
)


@dataclass
class SessionState:
    """État partagé entre la boucle de chat et les outils."""

    mode: str = DEFAULT_MODE

    def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"Mode inconnu « {mode} » : attendu {' ou '.join(MODES)}.")
        self.mode = mode


def _result(text: str, is_error: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        payload["is_error"] = True
    return payload


async def _call(fn: Callable[[], str]) -> dict[str, Any]:
    """Exécute un outil bloquant hors de la boucle asyncio et traduit les erreurs."""
    try:
        return _result(await asyncio.to_thread(fn))
    except (tl.ToolError, prog.ProgressError) as exc:
        return _result(str(exc), is_error=True)
    except (ValueError, TypeError) as exc:
        return _result(f"Paramètre invalide : {exc}", is_error=True)
    except Exception as exc:  # noqa: BLE001 - l'agent doit voir l'erreur plutôt que planter
        return _result(f"Erreur inattendue : {exc}", is_error=True)


def build_tools(workspace: Path, state: SessionState | None = None) -> list[Any]:
    """Construit les outils liés à un dossier de travail et à l'état de la session."""
    state = state or SessionState()
    lock = threading.Lock()

    def edit_progress(change: Callable[[dict[str, Any]], str]) -> str:
        with lock:
            data = prog.load(workspace)
            message = change(data)
            prog.save(workspace, data)
        return message

    def object_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    @tool(
        "read_file",
        "Lit un fichier texte du projet, avec numéros de ligne. start : première ligne (défaut 1), "
        "limit : nombre de lignes (défaut 400). Refuse les fichiers de secrets (.env, clés).",
        object_schema(
            {"path": {"type": "string"}, "start": {"type": "integer"}, "limit": {"type": "integer"}},
            ["path"],
        ),
    )
    async def read_file(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(
            lambda: tl.read_file(
                workspace,
                args.get("path", ""),
                int(args.get("start", 1)),
                int(args.get("limit", tl.DEFAULT_READ_LINES)),
            )
        )

    @tool(
        "list_files",
        "Liste les fichiers du projet (sans .git, node_modules…). Chemin optionnel : un sous-dossier.",
        object_schema({"path": {"type": "string"}}),
    )
    async def list_files(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(lambda: tl.list_files(workspace, args.get("path", ".")))

    @tool(
        "search_text",
        "Cherche une expression régulière dans les fichiers texte du projet. "
        "Renvoie fichier:ligne: texte.",
        object_schema(
            {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "ignore_case": {"type": "boolean"},
            },
            ["pattern"],
        ),
    )
    async def search_text(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(
            lambda: tl.search_text(
                workspace,
                args.get("pattern", ""),
                args.get("path", "."),
                bool(args.get("ignore_case", False)),
            )
        )

    @tool(
        "write_file",
        "Crée un nouveau fichier dans le projet. Ne remplace un fichier existant que si "
        "overwrite vaut true. Refuse les fichiers de secrets : utilise .env.example. "
        "Indisponible en mode apprendre.",
        object_schema(
            {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "overwrite": {"type": "boolean"},
            },
            ["path", "content"],
        ),
    )
    async def write_file(args: dict[str, Any]) -> dict[str, Any]:
        if state.mode != "ensemble":
            return _result(LEARN_MODE_REFUSAL, is_error=True)
        return await _call(
            lambda: tl.write_file(
                workspace,
                args.get("path", ""),
                args.get("content", ""),
                bool(args.get("overwrite", False)),
            )
        )

    @tool(
        "edit_file",
        "Remplace un texte exact (old) par un nouveau texte (new) dans un fichier existant, "
        "et renvoie le diff. old doit être unique, sauf replace_all. Indisponible en mode apprendre.",
        object_schema(
            {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            ["path", "old", "new"],
        ),
    )
    async def edit_file(args: dict[str, Any]) -> dict[str, Any]:
        if state.mode != "ensemble":
            return _result(LEARN_MODE_REFUSAL, is_error=True)
        return await _call(
            lambda: tl.edit_file(
                workspace,
                args.get("path", ""),
                args.get("old", ""),
                args.get("new", ""),
                bool(args.get("replace_all", False)),
            )
        )

    @tool(
        "run_tests",
        "Lance pytest dans le dossier du projet et renvoie le résultat. "
        "Chemin optionnel (fichier ou dossier) relatif au dossier de travail.",
        object_schema({"path": {"type": "string"}}),
    )
    async def run_tests(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(lambda: tl.run_tests(workspace, args.get("path", "")))

    @tool(
        "run_python",
        "Exécute un fichier .py du projet (30 s maximum) et renvoie sa sortie.",
        object_schema({"file": {"type": "string"}}, ["file"]),
    )
    async def run_python(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(lambda: tl.run_python(workspace, args.get("file", "")))

    @tool(
        "write_challenge",
        "Dépose un test pytest dans tests/ : c'est le défi que l'élève doit faire passer. "
        "Nom au format test_<mots_en_minuscules>.py. N'écrase jamais un fichier existant.",
        object_schema({"filename": {"type": "string"}, "content": {"type": "string"}}, ["filename", "content"]),
    )
    async def write_challenge(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(
            lambda: tl.write_challenge(workspace, args.get("filename", ""), args.get("content", ""))
        )

    @tool(
        "get_progress",
        "Renvoie la progression de l'utilisateur : niveau, jalon, concepts et erreurs récurrentes.",
        object_schema({}),
    )
    async def get_progress(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(lambda: prog.summary(prog.load(workspace)))

    @tool(
        "record_progress",
        "Enregistre un concept. outcome : seen (expliqué), solved (réussi) ou stuck (bloqué). "
        "help_level : barreau d'aide le plus haut utilisé (0 à 3), pour solved et stuck.",
        object_schema(
            {
                "concept": {"type": "string"},
                "outcome": {"type": "string", "enum": list(prog.OUTCOMES)},
                "help_level": {"type": "integer", "minimum": 0, "maximum": 3},
                "note": {"type": "string"},
            },
            ["concept", "outcome"],
        ),
    )
    async def record_progress(args: dict[str, Any]) -> dict[str, Any]:
        def change(data: dict[str, Any]) -> str:
            concept = args.get("concept", "")
            status = prog.record_concept(
                data,
                concept,
                args.get("outcome", ""),
                int(args.get("help_level", 0)),
                args.get("note", ""),
            )
            return f"Enregistré : « {concept.strip()} » → {prog.STATUS_LABELS[status]}."

        return await _call(lambda: edit_progress(change))

    @tool(
        "record_error",
        "Note une erreur récurrente de l'utilisateur (par exemple « oublie le return »).",
        object_schema({"description": {"type": "string"}}, ["description"]),
    )
    async def record_error(args: dict[str, Any]) -> dict[str, Any]:
        def change(data: dict[str, Any]) -> str:
            count = prog.record_error(data, args.get("description", ""))
            return f"Erreur notée (vue {count} fois)."

        return await _call(lambda: edit_progress(change))

    @tool(
        "update_profile",
        "Met à jour le niveau estimé de l'utilisateur (non-codeur, débutant, intermédiaire…), "
        "le jalon en cours ou le projet.",
        object_schema(
            {
                "level": {"type": "string"},
                "milestone": {"type": "integer", "minimum": 1},
                "project": {"type": "string"},
            }
        ),
    )
    async def update_profile(args: dict[str, Any]) -> dict[str, Any]:
        def change(data: dict[str, Any]) -> str:
            prog.update_profile(
                data,
                level=args.get("level"),
                milestone=args.get("milestone"),
                project=args.get("project"),
            )
            return "Profil mis à jour."

        return await _call(lambda: edit_progress(change))

    @tool(
        "log_change",
        "Ajoute une entrée au journal des changements du projet (.maieutik/JOURNAL.md) : "
        "la demande, les fichiers touchés, pourquoi ce choix, et ce qui reste à vérifier.",
        object_schema(
            {
                "request": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "why": {"type": "string"},
                "risks": {"type": "string"},
            },
            ["request"],
        ),
    )
    async def log_change(args: dict[str, Any]) -> dict[str, Any]:
        def change() -> str:
            files = args.get("files") or []
            if isinstance(files, str):
                files = [files]
            prog.add_journal_entry(
                workspace, args.get("request", ""), files, args.get("why", ""), args.get("risks", "")
            )
            return f"Journal mis à jour : {prog.PROGRESS_DIR}/{prog.JOURNAL_FILE}"

        return await _call(change)

    return [
        read_file,
        list_files,
        search_text,
        write_file,
        edit_file,
        run_tests,
        run_python,
        write_challenge,
        get_progress,
        record_progress,
        record_error,
        update_profile,
        log_change,
    ]


def build_options(
    workspace: Path | str,
    model: str | None = None,
    state: SessionState | None = None,
) -> ClaudeAgentOptions:
    """Options du SDK : uniquement les outils maison, confinés au dossier du projet."""
    root = Path(workspace).resolve()
    state = state or SessionState()
    server = create_sdk_mcp_server(name=SERVER_NAME, version="0.2.0", tools=build_tools(root, state))
    return ClaudeAgentOptions(
        system_prompt=build_system_prompt(root, mode=state.mode),
        mcp_servers={SERVER_NAME: server},
        tools=[],
        allowed_tools=[f"mcp__{SERVER_NAME}__{name}" for name in CUSTOM_TOOLS],
        disallowed_tools=list(FORBIDDEN_BUILTINS),
        cwd=str(root),
        setting_sources=[],
        model=model or os.environ.get("MAIEUTIK_MODEL") or None,
    )
