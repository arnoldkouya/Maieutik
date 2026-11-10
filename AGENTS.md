# Instructions pour les agents qui modifient ce dépôt

Ce dépôt contient un skill au format Agent Skills (`skills/maieutik/`) et un agent en terminal (`src/maieutik/`) qui partagent la même méthode.

## Règles

- Source de vérité de la méthode et des projets fil rouge : `skills/maieutik/`. L'agent en terminal les lit depuis là (`src/maieutik/skill.py`) et le wheel les embarque (`force-include` dans `pyproject.toml`). Ne pas les dupliquer ailleurs.
- `skills/maieutik/references/pedagogie.md` reste indépendant des outils : aucun nom d'outil de l'agent en terminal (`run_tests`, `record_progress`…). Ces noms vivent dans `src/maieutik/prompts/sdk_tools.md`. Un test le vérifie.
- Source de vérité du suivi de progression : `src/maieutik/progress.py`. `skills/maieutik/scripts/progress.py` en est une **copie générée** : ne pas l'éditer à la main, lancer `python3 scripts/sync_skill.py` après chaque modification. Un test échoue si les deux divergent.
- `progress.py` n'utilise que la bibliothèque standard et reste compatible Python 3.8 (pas de `match`, pas de `str.removeprefix`, pas de `X | Y` hors annotations). Le skill doit rester autonome : installé seul dans `~/.claude/skills` ou `~/.agents/skills`, sans le paquet.
- `SKILL.md` garde un frontmatter avec `name: maieutik` et une `description` de moins de 1024 caractères. Tout chemin cité dans `SKILL.md` doit exister dans le dossier du skill.
- Ne jamais livrer la solution d'un jalon dans `skills/maieutik/projects/` : seuls les tests et l'énoncé y ont leur place.
- Le numéro de version est dans quatre fichiers qui doivent rester identiques : `pyproject.toml`, `src/maieutik/__init__.py`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`.
- L'agent en terminal ne doit jamais recevoir `Write`, `Edit`, `MultiEdit`, `NotebookEdit` ni `Bash` : c'est sa garantie technique (`tests/test_agent.py`).

## Vérifications avant de livrer

```bash
python3 scripts/sync_skill.py
python3 -m pytest
python3 scripts/build_zips.py --out /tmp/maieutik-dist
```
