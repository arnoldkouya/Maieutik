# Projet fil rouge : une mini API de tâches

Tu vas construire pas à pas une petite application de gestion de tâches : d'abord en Python pur, puis exposée en API HTTP. Python 3.10 ou plus.

Tu écris le code, Maïeutik te guide. Lance `maieutik chat` dans ce dossier pour travailler avec lui.

## Jalon 1 : le modèle

Concepts : fonctions, listes, dictionnaires.

Crée `todo.py` avec trois fonctions. Une tâche est un dictionnaire avec les clés `id`, `title` et `done`.

- `add_task(tasks, title)` ajoute une tâche à la liste et la renvoie.
- `complete_task(tasks, task_id)` marque la tâche comme faite.
- `list_tasks(tasks, only_open=False)` renvoie les tâches, ou seulement celles qui ne sont pas faites.

Validé quand `tests/test_step1_tasks.py` passe.

## Jalon 2 : la persistance

Concepts : fichiers, JSON, exceptions.

Sauvegarder et recharger les tâches depuis un fichier JSON, en gérant le fichier absent ou corrompu.

## Jalon 3 : tes propres tests

Concepts : pytest, cas limites.

C'est à toi d'écrire les tests des cas limites (titre vide, identifiant inconnu, fichier abîmé). Maïeutik relit.

## Jalon 4 : l'API HTTP

Concepts : FastAPI, routes, codes HTTP.

Exposer les fonctions en routes : créer, lister, terminer une tâche.

## Jalon 5 : erreurs et validation

Concepts : Pydantic, 404, 422.

Rejeter proprement les données invalides et répondre avec les bons codes.

## Jalon 6 : le refactor

Concepts : séparation des responsabilités, nommage, dépendances.

Relire l'ensemble, séparer le stockage de l'API, et expliquer chaque choix.
