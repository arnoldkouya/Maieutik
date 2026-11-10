# Maïeutik

Un agent professeur qui t'apprend à coder **en codant avec toi**, sans coder à ta place.

Tu construis un vrai projet. Maïeutik lit ton code, lance tes tests, te pose les bonnes questions et ne te donne la solution qu'en dernier recours. Il retient ce que tu maîtrises et ce qui reste fragile.

> État : MVP, terminal uniquement, Python.

## Installation

Python 3.10 ou plus, et une clé API Anthropic.

```bash
git clone https://github.com/arnoldkouya/maieutik
cd maieutik
pip install -e .
export ANTHROPIC_API_KEY=...
```

## Utilisation

```bash
maieutik init mon-projet     # prépare le projet fil rouge
cd mon-projet
maieutik chat                # lance une session avec le professeur
```

Dans la session :

| Commande | Effet |
| --- | --- |
| `/indice` | demande le barreau d'aide suivant |
| `/tests` | lance les tests et t'aide à comprendre les échecs |
| `/relis` | relecture pédagogique de ton code |
| `/explique [sujet]` | explique le pourquoi d'un choix |
| `/progres` | affiche ta progression |
| `/quit` | quitte |

Autres commandes : `maieutik progress [dossier]` affiche ta progression, `maieutik projects` liste les projets disponibles.

## Comment ça marche

**L'échelle d'aide.** Quand tu bloques : 1) une question ou un indice, 2) un exemple partiel dans un autre contexte, 3) la solution expliquée, suivie d'un exercice de transfert. Si tu as vraiment essayé deux fois et que tu insistes, tu y accèdes sans attendre.

**Il ne touche pas à tes fichiers.** L'agent peut lire ton projet (`Read`, `Glob`, `Grep`), exécuter ton code et tes tests, déposer un défi sous forme de test dans `tests/`, et mettre à jour ta progression. Il n'a ni `Write`, ni `Edit`, ni `Bash` : c'est une limite technique, pas une simple consigne.

**Il vérifie avant d'affirmer.** Il exécute le code (30 s maximum) et les tests (60 s maximum) plutôt que de deviner.

**Il se souvient.** `.maieutik/progress.json` (ignoré par git) contient ton niveau estimé, le jalon en cours, le statut de chaque concept et tes erreurs récurrentes. Il est rechargé à chaque session.

Plus de détails : [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md).

## Structure

```
src/maieutik/
  cli.py          commandes init, chat, progress, projects
  agent.py        options du SDK et outils de l'agent
  progress.py     suivi de progression (sans dépendance au SDK)
  tools.py        exécution de code et de tests, dépôt d'un défi
  prompts.py      assemblage du prompt système
  prompts/        system.md et help_ladder.md
  projects/       projets fil rouge (todo-api)
tests/            tests du projet lui-même
docs/             philosophie pédagogique
```

## Développement

```bash
pip install -e .
python -m pytest
```

Pour choisir un modèle : `maieutik chat --model <nom>` ou la variable `MAIEUTIK_MODEL`.

## Limites connues

- L'agent peut lire des fichiers hors du dossier de l'élève : `Read`, `Glob` et `Grep` ne sont pas confinés. Seuls l'exécution et le dépôt de défis le sont.
- Le code de l'élève s'exécute sur ta machine, sans isolation. Utilise-le pour ton propre code.
- La boucle de conversation avec le SDK n'a pas de test automatisé : les tests couvrent les outils, la progression, le CLI et la configuration de l'agent, pas les réponses du modèle.

## Pistes pour la suite

- Autres projets fil rouge et autres langages.
- Révisions espacées des concepts fragiles.
- Interface web.
