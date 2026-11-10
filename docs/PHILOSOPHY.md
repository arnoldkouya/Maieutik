# Philosophie

Le vibe coding met la création de logiciels à la portée de personnes qui ne codent pas. Le danger est double : on livre un programme qu'on ne comprend pas, et on ne voit pas ses failles. Maïeutik (de la maïeutique de Socrate : faire accoucher l'autre de ses propres réponses) cherche à rendre la compréhension et les risques **visibles**, sans freiner la création.

## Principes

**1. Coder avec, pas à la place sans rien dire.** Par défaut, l'agent code ce que tu demandes sur ton projet, puis explique chaque modification : ce qu'il a fait, pourquoi. Tu gardes la main sur le quoi ; il rend le comment lisible.

**2. Les risques se montrent à chaque changement.** Un bloc « À vérifier » court suit chaque modification, classé en trois niveaux : *à corriger avant de publier*, *à surveiller*, *bonne pratique*. Chaque point est concret (quel fichier, quelle conséquence), pas un avertissement générique.

**3. Langage simple.** Analogies, jargon expliqué, réponses courtes. « Explique plus » ouvre le détail à la demande.

**4. L'honnêteté sur les limites.** L'agent ne dit jamais « sécurisé ». Une IA qui relit son propre code n'est pas un audit indépendant. Pour un audit poussé, Maïeutik délègue au skill `security-audit` de Cloudflare, en demandant confirmation car il est long et coûteux, puis traduit ses résultats.

**5. Une trace des changements.** `.maieutik/JOURNAL.md` garde : la demande, les fichiers touchés, le pourquoi, les points à vérifier. On peut le versionner.

**6. Apprendre, quand on le demande.** Le mode apprendre inverse les rôles : tu codes, l'agent guide par paliers (question ou indice, exemple partiel, solution expliquée), fait produire plutôt que lire, et vérifie en exécutant le code. Le parcours s'appuie sur ton projet ; `todo-api` n'est qu'un repli. La progression (`.maieutik/progress.json`) se déduit des essais : un concept simplement expliqué est « vu », pas « acquis ».

## Garanties et leurs limites

| Garantie | Forme terminal | Forme skill |
|---|---|---|
| Mode apprendre : l'agent ne modifie rien | technique (outils d'écriture refusés) | consigne seulement |
| Accès confiné au projet, secrets refusés | technique | dépend de l'agent hôte |
| Langages | Python seulement (pytest, scripts) | tous |

## Ce que Maïeutik ne fait pas

- Il ne remplace pas un audit, un test d'intrusion ni une relecture humaine.
- Il ne mesure pas la compréhension autrement que par les essais et les questions.
- Il ne planifie pas de révisions espacées.
- Il n'isole pas l'exécution du code : travaille sous git.
