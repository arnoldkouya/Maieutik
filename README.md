# Maïeutik

Un agent qui **code avec toi et t'explique chaque modification**, en rendant visibles les risques de sécurité.

Le vibe coding permet à des non-codeurs de construire de vrais produits avec une IA. Le risque : livrer du code qu'on ne comprend pas, avec des failles qu'on ne voit pas. Maïeutik travaille sur **ton projet** : tu demandes (« ajoute la connexion utilisateur »), il code, puis il dit en langage simple ce qu'il a fait, pourquoi, et ce qu'il faut vérifier côté sécurité.

Après chaque changement :

- **Ce que j'ai fait** et **Pourquoi** : court, avec des analogies, sans jargon non expliqué (« explique plus » pour creuser) ;
- **À vérifier** : les risques classés *à corriger avant de publier*, *à surveiller*, *bonne pratique* ;
- une ligne dans le **journal des changements** (`.maieutik/JOURNAL.md`).

Deux modes :

| Mode | Principe |
|---|---|
| **Coder ensemble** (défaut) | tu demandes, l'agent code et explique chaque modification |
| **Apprendre** (sur demande) | tu codes, l'agent te guide avec une échelle d'aide (indice, exemple partiel, solution) et ne touche à rien |

> État : version 0.2. Skill en français, agent en terminal en Python.

## Ce que Maïeutik n'est pas

Un outil qui explique son propre code n'est **pas un audit**. L'agent peut se tromper ou passer à côté d'une faille. Il ne dit jamais « c'est sécurisé ». Avant de publier quelque chose de sensible (paiements, données personnelles), fais relire par une personne compétente.

## Formes disponibles

| Forme | Pour qui | Mode apprendre : « il ne touche à rien » |
|---|---|---|
| **Skill** (Claude Code, Codex, claude.ai, Desktop) | tu as déjà un agent de code | une consigne : l'agent s'engage, mais garde ses outils d'écriture |
| **Agent en terminal** (`maieutik chat`) | tu veux un agent dédié | une limite technique : en mode apprendre, les outils d'écriture refusent |

## Installer le skill

Le skill suit le format ouvert Agent Skills. Il est dans [`skills/maieutik/`](skills/maieutik/).

```bash
git clone https://github.com/arnoldkouya/maieutik.git
cd maieutik
```

| Plateforme | Méthode |
|---|---|
| Claude Code | Plugin ou script |
| Codex | Script, ou copie dans `~/.agents/skills/maieutik` |
| Claude (claude.ai, Desktop) | Importer `dist/maieutik-skill.zip` |
| Autre agent compatible | Copier `skills/maieutik/` dans son dossier de skills |

### Claude Code

```text
/plugin marketplace add arnoldkouya/maieutik
/plugin install maieutik@maieutik
```

Ou par le script :

```bash
scripts/install.sh claude            # pour tous tes projets
scripts/install.sh claude --project  # pour le projet courant
```

### Codex

```bash
scripts/install.sh codex            # ~/.agents/skills
scripts/install.sh codex --project  # .agents/skills du projet courant
```

Windows : `scripts\install.ps1 -Target codex` (ou `claude`, `all`; `-Project`, `-SansAudit`). Le script PowerShell n'a pas été testé sur Windows.

### Claude (claude.ai, Desktop)

```bash
python3 scripts/build_zips.py
```

Importer ensuite `dist/maieutik-skill.zip` dans les réglages des skills. Le skill d'audit de Cloudflare (ci-dessous) est à importer séparément.

### Le skill d'audit de sécurité de Cloudflare

Les scripts d'installation ajoutent aussi le skill [`security-audit`](https://github.com/cloudflare/security-audit-skill) de Cloudflare (licence MIT), à côté de Maïeutik. Maïeutik lui délègue la commande « audite mon projet » et traduit ses résultats en langage simple.

- Il est **téléchargé à l'installation, figé sur un commit précis** (pas la dernière version de la branche) : le code installé est celui qui a été relu. Il n'est pas copié dans ce dépôt.
- Il faut `git` et un accès à GitHub. En cas d'échec, Maïeutik s'installe quand même et un avertissement indique la commande pour l'ajouter plus tard.
- Un audit complet est **long et coûteux** (nombreux sous-agents) : Maïeutik demande confirmation et propose le profil `quick`.
- `--sans-audit` (`-SansAudit` sous Windows) ne l'installe pas.

### Utiliser le skill

Dans ton projet, dis par exemple :

- « Ajoute la connexion utilisateur et explique-moi ce que tu fais. »
- « Audite mon projet. »
- « Passe en mode apprendre : je veux écrire cette fonction moi-même. »

Le suivi est dans `.maieutik/` : `progress.json` (progression, personnel) et `JOURNAL.md` (journal des changements, que tu peux versionner). Pense à ajouter `.maieutik/progress.json` à ton `.gitignore`.

## Utiliser l'agent en terminal

Python 3.10 ou plus, clé API Anthropic. Dans le dossier de ton projet :

```bash
pip install -e .   # depuis le dépôt Maïeutik
export ANTHROPIC_API_KEY=...
cd mon-projet
maieutik chat
```

Pour un projet d'exercice vierge : `maieutik init mon-projet`.

| Commande | Effet |
|---|---|
| `/audit` | relecture de sécurité de ton projet |
| `/explique [sujet]` | explique le pourquoi d'un choix |
| `/tests` | lance les tests et aide à comprendre les échecs |
| `/apprendre` / `/ensemble` | change de mode |
| `/indice`, `/relis` | (mode apprendre) aide suivante, relecture pédagogique |
| `/progres`, `/journal` | progression, journal des changements |
| `/aide`, `/quit` | aide, quitter |

Autres commandes : `maieutik progress [dossier]`, `maieutik journal [dossier]`, `maieutik projects`. Modèle : `--model <nom>` ou `MAIEUTIK_MODEL`.

L'agent n'utilise que ses propres outils, confinés à ton dossier : lire, lister, chercher, écrire, modifier (avec le diff), lancer pytest ou un script Python. Les fichiers de secrets (`.env`, `*.pem`, `*.key`, clés SSH…) lui sont refusés, sauf les modèles comme `.env.example`. Les outils d'écriture n'existent qu'en mode coder ensemble.

## La méthode

La méthode complète est dans [`skills/maieutik/references/pedagogie.md`](skills/maieutik/references/pedagogie.md), les règles de sécurité dans [`references/securite.md`](skills/maieutik/references/securite.md). Principes : [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md).

## Suivre la progression sans agent

Script autonome (Python 3.8+, aucune dépendance) :

```bash
python3 skills/maieutik/scripts/progress.py show
python3 skills/maieutik/scripts/progress.py record "authentification" seen
python3 skills/maieutik/scripts/progress.py journal "Ajout de la connexion" --fichiers auth.py --pourquoi "hachage" --risque "clé dans .env"
```

## Structure du dépôt

```text
skills/maieutik/
├── SKILL.md                     # le skill
├── references/pedagogie.md      # modes, format d'explication, échelle d'aide
├── references/securite.md       # « À vérifier », niveaux de risque, audit
├── scripts/progress.py          # copie générée de src/maieutik/progress.py
└── projects/todo-api/           # projet d'exercice (repli)
src/maieutik/                    # agent en terminal (cli, agent, tools, prompts, progress, skill)
.claude-plugin/                  # manifestes du plugin Claude Code
scripts/                         # install.sh, install.ps1, build_zips.py, sync_skill.py
tests/  docs/PHILOSOPHY.md  AGENTS.md
```

## Développement

```bash
pip install -e .
python3 -m pytest
python3 scripts/sync_skill.py      # après toute modification de src/maieutik/progress.py
python3 scripts/build_zips.py      # archive dans dist/
```

## Limites

- Ce n'est pas un audit (voir plus haut). L'IA explique son propre code : elle peut se tromper.
- Dans la forme skill, le mode apprendre repose sur une consigne. Pour une garantie technique, utilise `maieutik chat`.
- L'agent en terminal exécute seulement du Python (pytest, scripts `.py`). Pour d'autres langages, utilise le skill dans ton agent habituel.
- Il peut écrire et exécuter du code dans ton dossier, sans isolation : travaille sous git pour pouvoir annuler.
- Les tests couvrent le skill, les outils, la progression, le CLI, les installateurs et la configuration de l'agent, pas les réponses du modèle, l'activation du skill dans chaque application ni le script PowerShell.
