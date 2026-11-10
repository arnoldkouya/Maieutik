"""Interface en ligne de commande : maieutik init | chat | progress | projects."""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from . import progress as prog
from .skill import skill_dir

DEFAULT_PROJECT = "todo-api"
START_PROMPT = "[DÉBUT DE SESSION] Applique la procédure de début de session."

CHAT_HELP = """Commandes :
  /indice           demander le barreau d'aide suivant
  /tests            lancer les tests et comprendre les échecs
  /relis            relecture pédagogique de ton code
  /explique [sujet] comprendre le pourquoi d'un choix
  /progres          voir ta progression
  /aide             afficher cette aide
  /quit             quitter"""

SLASH_PROMPTS = {
    "/indice": "[INDICE] Je suis bloqué. Donne-moi l'aide du barreau suivant de l'échelle, pas plus.",
    "/tests": "[TESTS] Lance les tests, puis aide-moi à comprendre les échecs sans me donner la solution.",
    "/relis": "[RELECTURE] Relis mon code actuel comme un mentor.",
}


def projects_dir() -> Path:
    return skill_dir() / "projects"


def list_projects() -> list[str]:
    return sorted(path.name for path in projects_dir().iterdir() if path.is_dir())


def init_workspace(target: Path, project: str = DEFAULT_PROJECT) -> list[Path]:
    """Copie le projet fil rouge dans ``target`` sans jamais écraser un fichier existant."""
    source = projects_dir() / project
    if not source.is_dir():
        raise SystemExit(f"Projet inconnu : {project}. Disponibles : {', '.join(list_projects())}")
    target.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for item in sorted(source.rglob("*")):
        if item.is_dir() or "__pycache__" in item.parts:
            continue
        destination = target / item.relative_to(source)
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        created.append(destination)
    data = prog.load(target)
    if data["project"] is None:
        data["project"] = project
    prog.save(target, data)
    return created


def translate_input(line: str) -> str:
    """Transforme une commande /… en message explicite pour l'agent."""
    stripped = line.strip()
    command = stripped.split()[0] if stripped else ""
    if command == "/explique":
        subject = stripped[len(command) :].strip()
        if subject:
            return f"[MODE EXPLIQUE-MOI] Explique-moi le pourquoi : {subject}"
        return "[MODE EXPLIQUE-MOI] Explique-moi pourquoi on a fait ce dernier choix."
    return SLASH_PROMPTS.get(command, stripped)


async def _show_response(client) -> None:
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    print(f"\n{block.text.strip()}")
                elif isinstance(block, ToolUseBlock):
                    print(f"  · {block.name.removeprefix('mcp__maieutik__')}")
        elif isinstance(message, ResultMessage) and message.is_error:
            print(f"\n[erreur] {message.result or message.subtype}")


async def chat(workspace: Path, model: str | None = None) -> int:
    from claude_agent_sdk import ClaudeSDKClient

    from .agent import build_options

    options = build_options(workspace, model=model)
    print(f"Maïeutik : session dans {workspace}\n{CHAT_HELP}\n")
    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(START_PROMPT)
            await _show_response(client)
            while True:
                try:
                    line = await asyncio.to_thread(input, "\ntoi › ")
                except EOFError:
                    break
                line = line.strip()
                if not line:
                    continue
                if line in ("/quit", "/exit", "/q"):
                    break
                if line == "/aide":
                    print(CHAT_HELP)
                    continue
                if line == "/progres":
                    print(prog.summary(prog.load(workspace)))
                    continue
                await client.query(translate_input(line))
                await _show_response(client)
    except Exception as exc:  # noqa: BLE001 - message d'aide plutôt qu'une trace brute
        print(
            f"\nErreur : {exc}\n"
            "Vérifie que la variable ANTHROPIC_API_KEY est définie "
            "et que le SDK est bien installé (pip install claude-agent-sdk).",
            file=sys.stderr,
        )
        return 1
    print("\nÀ bientôt. Ta progression est enregistrée dans .maieutik/progress.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="maieutik",
        description="Un professeur de code qui t'apprend en codant avec toi.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init_cmd = commands.add_parser("init", help="prépare un dossier avec le projet fil rouge")
    init_cmd.add_argument("directory", nargs="?", default=".")
    init_cmd.add_argument("--project", default=DEFAULT_PROJECT)

    chat_cmd = commands.add_parser("chat", help="lance une session avec le professeur")
    chat_cmd.add_argument("directory", nargs="?", default=".")
    chat_cmd.add_argument("--model", default=None)

    progress_cmd = commands.add_parser("progress", help="affiche ta progression")
    progress_cmd.add_argument("directory", nargs="?", default=".")

    commands.add_parser("projects", help="liste les projets fil rouge disponibles")

    args = parser.parse_args(argv)

    if args.command == "projects":
        print("\n".join(list_projects()))
        return 0

    directory = Path(args.directory).resolve()

    if args.command == "init":
        created = init_workspace(directory, args.project)
        for path in created:
            print(f"créé : {path.relative_to(directory)}")
        print(f"Prêt. Ensuite : cd {directory} && maieutik chat")
        return 0

    if not directory.is_dir():
        print(f"Dossier introuvable : {directory}", file=sys.stderr)
        return 1

    if args.command == "progress":
        print(prog.summary(prog.load(directory)))
        return 0

    try:
        return asyncio.run(chat(directory, model=args.model))
    except KeyboardInterrupt:
        print("\nÀ bientôt.")
        return 0
