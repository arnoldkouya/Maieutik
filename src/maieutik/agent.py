"""Configuration de l'agent Maïeutik avec le Claude Agent SDK.

Principe : l'agent peut LIRE le projet de l'élève, exécuter son code et ses tests,
déposer un défi (un test) et tenir à jour la progression. Il ne peut PAS modifier
les fichiers de l'élève : c'est l'élève qui code.
"""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, tool

from . import progress as prog
from . import tools as tl
from .prompts import build_system_prompt

SERVER_NAME = "maieutik"
CUSTOM_TOOLS = (
    "run_tests",
    "run_python",
    "write_challenge",
    "get_progress",
    "record_progress",
    "record_error",
    "update_profile",
)
READ_ONLY_BUILTINS = ("Read", "Glob", "Grep")
FORBIDDEN_BUILTINS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash")


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


def build_tools(workspace: Path) -> list[Any]:
    """Construit les outils liés à un dossier de travail."""
    lock = threading.Lock()

    def edit_progress(change: Callable[[dict[str, Any]], str]) -> str:
        with lock:
            data = prog.load(workspace)
            message = change(data)
            prog.save(workspace, data)
        return message

    @tool(
        "run_tests",
        "Lance pytest dans le dossier de l'élève et renvoie le résultat. "
        "Chemin optionnel (fichier ou dossier) relatif au dossier de travail.",
        {"type": "object", "properties": {"path": {"type": "string"}}},
    )
    async def run_tests(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(lambda: tl.run_tests(workspace, args.get("path", "")))

    @tool(
        "run_python",
        "Exécute un fichier .py du dossier de l'élève (30 s maximum) et renvoie sa sortie.",
        {
            "type": "object",
            "properties": {"file": {"type": "string"}},
            "required": ["file"],
        },
    )
    async def run_python(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(lambda: tl.run_python(workspace, args.get("file", "")))

    @tool(
        "write_challenge",
        "Dépose un test pytest dans tests/ : c'est le défi que l'élève doit faire passer. "
        "Nom au format test_<mots_en_minuscules>.py. N'écrase jamais un fichier existant.",
        {
            "type": "object",
            "properties": {"filename": {"type": "string"}, "content": {"type": "string"}},
            "required": ["filename", "content"],
        },
    )
    async def write_challenge(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(
            lambda: tl.write_challenge(workspace, args.get("filename", ""), args.get("content", ""))
        )

    @tool(
        "get_progress",
        "Renvoie la progression de l'élève : niveau, jalon, concepts et erreurs récurrentes.",
        {"type": "object", "properties": {}},
    )
    async def get_progress(args: dict[str, Any]) -> dict[str, Any]:
        return await _call(lambda: prog.summary(prog.load(workspace)))

    @tool(
        "record_progress",
        "Enregistre un essai de l'élève sur un concept. outcome : solved ou stuck. "
        "help_level : barreau d'aide le plus haut utilisé (0 à 3).",
        {
            "type": "object",
            "properties": {
                "concept": {"type": "string"},
                "outcome": {"type": "string", "enum": list(prog.OUTCOMES)},
                "help_level": {"type": "integer", "minimum": 0, "maximum": 3},
                "note": {"type": "string"},
            },
            "required": ["concept", "outcome"],
        },
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
        "Note une erreur récurrente de l'élève (par exemple « oublie le return »).",
        {
            "type": "object",
            "properties": {"description": {"type": "string"}},
            "required": ["description"],
        },
    )
    async def record_error(args: dict[str, Any]) -> dict[str, Any]:
        def change(data: dict[str, Any]) -> str:
            count = prog.record_error(data, args.get("description", ""))
            return f"Erreur notée (vue {count} fois)."

        return await _call(lambda: edit_progress(change))

    @tool(
        "update_profile",
        "Met à jour le niveau estimé de l'élève, le jalon en cours ou le projet.",
        {
            "type": "object",
            "properties": {
                "level": {"type": "string"},
                "milestone": {"type": "integer", "minimum": 1},
                "project": {"type": "string"},
            },
        },
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

    return [
        run_tests,
        run_python,
        write_challenge,
        get_progress,
        record_progress,
        record_error,
        update_profile,
    ]


def build_options(workspace: Path | str, model: str | None = None) -> ClaudeAgentOptions:
    """Options du SDK : outils en lecture seule + outils Maïeutik, dans le dossier de l'élève."""
    root = Path(workspace).resolve()
    server = create_sdk_mcp_server(name=SERVER_NAME, version="0.1.0", tools=build_tools(root))
    return ClaudeAgentOptions(
        system_prompt=build_system_prompt(root),
        mcp_servers={SERVER_NAME: server},
        tools=list(READ_ONLY_BUILTINS),
        allowed_tools=[
            *READ_ONLY_BUILTINS,
            *(f"mcp__{SERVER_NAME}__{name}" for name in CUSTOM_TOOLS),
        ],
        disallowed_tools=list(FORBIDDEN_BUILTINS),
        cwd=str(root),
        setting_sources=[],
        model=model or os.environ.get("MAIEUTIK_MODEL") or None,
    )
