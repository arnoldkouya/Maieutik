"""Assemblage du prompt système."""

from __future__ import annotations

from pathlib import Path

from . import progress as prog

PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPT_FILES = ("system.md", "help_ladder.md")


def load_prompt_text() -> str:
    parts = [(PROMPTS_DIR / name).read_text(encoding="utf-8").strip() for name in PROMPT_FILES]
    return "\n\n".join(parts)


def build_system_prompt(workspace: Path | str) -> str:
    data = prog.load(workspace)
    return (
        f"{load_prompt_text()}\n\n"
        "# État de l'élève au début de la session\n\n"
        f"{prog.summary(data)}\n"
    )
