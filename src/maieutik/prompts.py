"""Assemblage du prompt système.

La méthode pédagogique est celle du skill (``skills/maieutik/references/pedagogie.md``),
partagée avec les installations Claude Code et Codex. Seul l'addendum sur les outils
de cette session (``prompts/sdk_tools.md``) est propre à l'agent en terminal.
"""

from __future__ import annotations

from pathlib import Path

from . import progress as prog
from .skill import skill_dir

SDK_TOOLS_FILE = Path(__file__).parent / "prompts" / "sdk_tools.md"


def load_prompt_text() -> str:
    method = (skill_dir() / "references" / "pedagogie.md").read_text(encoding="utf-8")
    tools = SDK_TOOLS_FILE.read_text(encoding="utf-8")
    return f"{method.strip()}\n\n{tools.strip()}"


def build_system_prompt(workspace: Path | str) -> str:
    data = prog.load(workspace)
    return (
        f"{load_prompt_text()}\n\n"
        "# État de l'élève au début de la session\n\n"
        f"{prog.summary(data)}\n"
    )
