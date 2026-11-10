# Philosophie pédagogique

Maïeutik part d'un constat : un outil qui écrit le code à ta place te laisse avec un programme que tu ne comprends pas. Le nom vient de la maïeutique de Socrate : faire accoucher l'élève de ses propres réponses.

## Principes

**1. L'élève code, le professeur guide.** L'agent lit le projet, lance les tests, relit. Dans l'agent en terminal, il n'a aucun outil pour modifier les fichiers de l'élève : ce n'est pas une consigne que le modèle pourrait oublier, c'est une limite technique (voir `src/maieutik/agent.py`). Dans le skill, l'agent hôte garde ses outils d'écriture : la règle repose sur la consigne, ce qui est plus fragile et c'est dit dans le README.

**2. L'aide se mérite par paliers.** Question ou indice, puis exemple partiel, puis solution expliquée. L'échelle est décrite dans `skills/maieutik/references/pedagogie.md`. Rien n'est refusé définitivement : un élève qui a vraiment essayé finit par obtenir la solution, avec l'explication. Elle s'affiche dans la conversation, l'élève la tape lui-même.

**3. Produire plutôt que lire.** Comprendre une explication donne l'illusion de savoir. L'agent fait produire : un test à faire passer, une sortie à prédire, un exercice à refaire dans un autre contexte.

**4. Le code décide, pas le modèle.** L'agent exécute le code et les tests avant d'affirmer quoi que ce soit. Un professeur qui se trompe fait plus de mal que pas de professeur.

**5. La progression a une mémoire.** Le fichier `.maieutik/progress.json` retient les concepts vus, leur statut et les erreurs récurrentes. Le statut d'un concept se déduit des essais, pas de l'impression de l'agent :

| Statut | Règle |
| --- | --- |
| acquis | les deux derniers essais réussis avec au plus un indice |
| fragile | dernier essai bloqué, ou réussi seulement avec la solution |
| en cours | tout le reste |

**6. Court et interactif.** Huit lignes au plus, une seule question à la fois. Le rythme compte autant que le contenu.

## Ce que l'agent ne fait pas (encore)

- Il ne mesure pas la compréhension autrement que par les essais et les questions de vérification.
- Il ne planifie pas de révisions espacées : un concept fragile est signalé, mais pas reprogrammé automatiquement.
- Il ne sait pas s'il a « trop » aidé : le barreau d'aide est déclaré par l'agent lui-même.
