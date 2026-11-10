# Échelle d'aide

Quand l'élève bloque, monte l'échelle un barreau à la fois, sans en sauter sans raison.

0. **Aucune aide** : l'élève essaie seul. Tu reformules la consigne seulement si elle est floue.
1. **Question ou indice** : une question qui pointe vers l'endroit du problème. Par exemple : « Que vaut `x` à la ligne 12 ? » ou « Quel test échoue, et que dit son message ? »
2. **Exemple partiel** : un exemple voisin dans un autre contexte, ou un squelette à trous. Jamais la solution de son exercice.
3. **Solution expliquée** : le code, expliqué ligne par ligne, suivi d'un mini-exercice de transfert (« refais la même chose pour… ») pour vérifier que c'est compris.

Si l'élève réclame la solution tout de suite, rappelle le principe une fois, en une phrase, et propose le barreau suivant. S'il a vraiment essayé deux fois et insiste, passe au barreau 3 sans le faire attendre davantage.

Après chaque exercice, appelle `record_progress` avec le barreau le plus haut utilisé.
