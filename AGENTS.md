# Instructions pour les agents qui modifient ce dépôt

Ce dépôt contient un skill au format Agent Skills (`skills/maieutik/`) et un agent en terminal (`src/maieutik/`) qui partagent la même méthode.

## Règles

- Source de vérité de la méthode, des règles de sécurité et des projets : `skills/maieutik/`. L'agent en terminal les lit depuis là (`src/maieutik/skill.py`) et le wheel les embarque (`force-include` dans `pyproject.toml`). Ne pas les dupliquer.
- `references/pedagogie.md` et `references/securite.md` restent indépendants des outils : aucun nom d'outil de l'agent en terminal. Ces noms vivent dans `src/maieutik/prompts/sdk_tools.md`. Un test le vérifie.
- Source de vérité du suivi : `src/maieutik/progress.py`. `skills/maieutik/scripts/progress.py` est une **copie générée** : lancer `python3 scripts/sync_skill.py` après chaque modification. Un test échoue si elles divergent.
- `progress.py` : bibliothèque standard seule, compatible Python 3.8. Le skill doit rester autonome une fois installé seul.
- `SKILL.md` : frontmatter `name: maieutik`, `description` de moins de 1024 caractères, et tout chemin cité doit exister dans le dossier du skill.
- Ne jamais livrer la solution d'un jalon dans `skills/maieutik/projects/`.
- La version est dans quatre fichiers identiques : `pyproject.toml`, `src/maieutik/__init__.py`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`.

## Agent en terminal

- Tous les outils natifs du SDK sont désactivés (`tools=[]`, `FORBIDDEN_BUILTINS` : Read, Glob, Grep, Write, Edit, MultiEdit, NotebookEdit, Bash, WebFetch, WebSearch). Seuls les outils personnalisés de `src/maieutik/agent.py` existent, tous confinés au dossier du projet.
- Les outils d'écriture (`write_file`, `edit_file`, `write_challenge`) ne fonctionnent qu'en mode `ensemble` ; en mode `apprendre` ils refusent. C'est la garantie technique du mode apprendre (`tests/test_agent.py`).
- Les fichiers de secrets sont refusés en lecture et en écriture (`is_sensitive` dans `tools.py`).

## Skill tiers : security-audit (Cloudflare)

- Source : https://github.com/cloudflare/security-audit-skill (MIT). **Ne pas le copier dans ce dépôt** : il est téléchargé à l'installation par `scripts/install.sh` et `scripts/install.ps1`, figé sur un SHA complet (`MAIEUTIK_SECURITY_AUDIT_REF`). Les deux scripts doivent garder le même SHA (un test le vérifie).
- Échec du téléchargement : avertissement, installation de Maïeutik non bloquée.
- Mise à jour : relire les changements du dépôt amont, puis changer le SHA dans les deux scripts, relancer les tests et mentionner le changement dans le commit.

## Vérifications avant de livrer

```bash
python3 scripts/sync_skill.py
python3 -m pytest
python3 scripts/build_zips.py --out /tmp/maieutik-dist
```
