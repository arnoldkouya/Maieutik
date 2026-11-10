# Maïeutik

Un professeur de code qui t'apprend à coder **en codant avec toi**, sans coder à ta place.

Tu construis un vrai projet. Maïeutik lit ton code, lance tes tests, te pose les bonnes questions et ne te donne la solution qu'en dernier recours. Il retient ce que tu maîtrises et ce qui reste fragile.

Il existe sous deux formes qui partagent la même méthode :

| Forme | Pour qui | Garantie « il ne code pas à ma place » |
|---|---|---|
| **Skill** (Claude Code, Codex, claude.ai, Desktop) | tu utilises déjà un agent de code et tu veux qu'il devienne ton prof | une consigne : l'agent s'engage à ne pas écrire ton code, mais il en a techniquement les moyens |
| **Agent en terminal** (`maieutik chat`) | tu veux un prof dédié | une limite technique : l'agent n'a ni `Write`, ni `Edit`, ni `Bash` |

> État : MVP. Skill en français, agent en terminal en Python.

## Installer le skill

Le skill suit le format ouvert Agent Skills : un dossier avec un fichier `SKILL.md`. Il est dans [`skills/maieutik/`](skills/maieutik/).

```bash
git clone https://github.com/arnoldkouya/maieutik.git
cd maieutik
```

| Plateforme | Méthode |
|---|---|
| Claude Code | Plugin ou script (voir ci-dessous) |
| Claude (claude.ai, Desktop) | Importer `dist/maieutik-skill.zip` dans les réglages des skills |
| Codex | Script d'installation ou copie dans `~/.agents/skills/maieutik` |
| Autre agent compatible Agent Skills | Copier `skills/maieutik/` dans le dossier de skills de l'agent |

### Claude Code

Par le plugin :

```text
/plugin marketplace add arnoldkouya/maieutik
/plugin install maieutik@maieutik
```

Ou par le script, qui copie le skill dans `~/.claude/skills/maieutik` :

```bash
scripts/install.sh claude            # pour tous vos projets
scripts/install.sh claude --project  # pour le projet courant (.claude/skills)
```

### Claude (claude.ai, Desktop)

```bash
python3 scripts/build_zips.py
```

Puis, dans les réglages de Claude, section des capacités ou des skills, importer `dist/maieutik-skill.zip` (le dossier `maieutik/` est à la racine de l'archive). L'intitulé exact du menu varie selon la version de l'application.

### Codex

```bash
scripts/install.sh codex            # ~/.agents/skills/maieutik
scripts/install.sh codex --project  # .agents/skills du projet courant
```

Sous Windows, utiliser `scripts\install.ps1 -Target codex` (ou `claude`, `all`, avec `-Project` pour le projet courant). Dans Codex, le skill s'active seul selon sa description, ou en le nommant : `$maieutik`.

### Utiliser le skill

Dans ton dossier de projet, dis par exemple :

- « Apprends-moi à écrire une API, guide-moi sans me donner la réponse. »
- « Sois mon prof : je veux comprendre pourquoi ce test échoue. »
- « Relis mon code comme un mentor. »

L'agent reste en mode professeur jusqu'à ce que tu dises « stop » ou « mode normal ». Sa progression est notée dans `.maieutik/progress.json`, dans ton dossier de projet.

## Utiliser l'agent en terminal

Python 3.10 ou plus, et une clé API Anthropic.

```bash
pip install -e .
export ANTHROPIC_API_KEY=...
maieutik init mon-projet     # prépare le projet fil rouge
cd mon-projet
maieutik chat                # lance une session avec le professeur
```

Dans la session :

| Commande | Effet |
|---|---|
| `/indice` | demande le barreau d'aide suivant |
| `/tests` | lance les tests et t'aide à comprendre les échecs |
| `/relis` | relecture pédagogique de ton code |
| `/explique [sujet]` | explique le pourquoi d'un choix |
| `/progres` | affiche ta progression |
| `/quit` | quitte |

Autres commandes : `maieutik progress [dossier]` affiche ta progression, `maieutik projects` liste les projets disponibles. Pour choisir un modèle : `maieutik chat --model <nom>` ou la variable `MAIEUTIK_MODEL`.

## La méthode

**L'échelle d'aide.** Quand tu bloques : 1) une question ou un indice, 2) un exemple partiel dans un autre contexte, 3) la solution expliquée, suivie d'un exercice de transfert. Si tu as vraiment essayé deux fois et que tu insistes, tu y accèdes sans attendre. Même là, la solution s'affiche dans la conversation : c'est toi qui la tapes.

**Il vérifie avant d'affirmer.** Il exécute le code et les tests plutôt que de deviner.

**Il se souvient.** `.maieutik/progress.json` (ignoré par git) contient ton niveau estimé, le jalon en cours, le statut de chaque concept (nouveau, en cours, fragile, acquis) et tes erreurs récurrentes. Les deux formes lisent et écrivent le même fichier : tu peux passer de l'une à l'autre.

**Un projet fil rouge.** [`todo-api`](skills/maieutik/projects/todo-api/PROJECT.md) : une mini API de tâches en six jalons, avec les tests du jalon 1.

La méthode complète est dans [`skills/maieutik/references/pedagogie.md`](skills/maieutik/references/pedagogie.md). Les principes derrière : [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md).

## Suivre la progression sans agent

Le script du skill fonctionne seul (Python 3.8 ou plus, aucune dépendance) :

```bash
python3 skills/maieutik/scripts/progress.py show
python3 skills/maieutik/scripts/progress.py record "boucles for" solved --barreau 1
python3 skills/maieutik/scripts/progress.py error "oublie le return"
python3 skills/maieutik/scripts/progress.py profile --level débutant --milestone 2
```

## Structure du dépôt

```text
skills/maieutik/
├── SKILL.md                     # le skill
├── references/pedagogie.md      # la méthode, partagée par les deux formes
├── scripts/progress.py          # suivi de progression (copie de src/maieutik/progress.py)
└── projects/todo-api/           # projet fil rouge : PROJECT.md et tests du jalon 1
src/maieutik/
├── cli.py                       # commandes init, chat, progress, projects
├── agent.py                     # options du SDK et outils de l'agent en terminal
├── progress.py                  # suivi de progression, sans dépendance
├── tools.py                     # exécution de code et de tests, dépôt d'un défi
├── prompts.py, prompts/         # prompt système = méthode du skill + outils du terminal
└── skill.py                     # localise le dossier du skill
.claude-plugin/                  # manifestes du plugin Claude Code
scripts/                         # install.sh, install.ps1, build_zips.py, sync_skill.py
tests/                           # tests du dépôt
docs/PHILOSOPHY.md
AGENTS.md                        # consignes pour les agents qui modifient ce dépôt
```

## Développement

```bash
pip install -e .
python3 -m pytest                  # tests
python3 scripts/sync_skill.py      # après toute modification de src/maieutik/progress.py
python3 scripts/build_zips.py      # archive dans dist/
```

## Limites

- Dans la forme skill, la règle « ne pas coder à ta place » repose sur la consigne donnée à l'agent. Pour une garantie technique, utilise `maieutik chat`.
- Dans l'agent en terminal, `Read`, `Glob` et `Grep` ne sont pas confinés à ton dossier : il peut lire d'autres fichiers de ta machine. Seuls l'exécution de code et le dépôt de défis le sont.
- Le code de l'élève s'exécute sur ta machine, sans isolation. Utilise-le pour ton propre code.
- Les tests couvrent le skill, les outils, la progression, le CLI, les installateurs et la configuration de l'agent, pas les réponses du modèle ni l'activation du skill dans chaque application.

## Pistes pour la suite

- Autres projets fil rouge et autres langages.
- Révisions espacées des concepts fragiles.
- Interface web.
