"""Assemblage du prompt système.

La méthode (``references/pedagogie.md``) et les règles de sécurité (``references/securite.md``)
viennent du skill, partagées avec les installations Claude Code et Codex. Seul l'addendum
sur les outils de cette session (``prompts/sdk_tools.md``) est propre à l'agent en terminal.
"""

from __future__ import annotations

from pathlib import Path

from . import progress as prog
from .skill import skill_dir

SDK_TOOLS_FILE = Path(__file__).parent / "prompts" / "sdk_tools.md"
SKILL_REFERENCES = ("pedagogie.md", "securite.md")
MODE_LABELS = {
    "ensemble": "coder ensemble (tu codes à la demande de l'utilisateur et tu expliques)",
    "apprendre": "apprendre (l'utilisateur code, tu le guides, tu ne modifies aucun fichier)",
}


def load_prompt_text() -> str:
    parts = [
        (skill_dir() / "references" / name).read_text(encoding="utf-8").strip()
        for name in SKILL_REFERENCES
    ]
    parts.append(SDK_TOOLS_FILE.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)


def build_system_prompt(workspace: Path | str, mode: str = "ensemble") -> str:
    data = prog.load(workspace)
    return (
        f"{load_prompt_text()}\n\n"
        "# État au début de la session\n\n"
        f"Mode actuel : {MODE_LABELS.get(mode, mode)}\n"
        f"{prog.summary(data)}\n"
    )
