# Sécurité

Ce document sert deux choses : écrire du code qui ne crée pas de faille évidente, et dire à l'utilisateur ce qu'il doit surveiller. L'utilisateur ne sait souvent pas coder : un risque non signalé, il ne le verra jamais.

## Le bloc « À vérifier »

Après chaque modification de code, donne les risques **de cette modification**, pas une liste générique. Parmi ces familles, ne retiens que celles qui s'appliquent :

- **Secrets** : clé d'API, mot de passe de base de données, jeton. Jamais dans le code ni dans git. On les met dans un fichier `.env` ignoré par git, avec un `.env.example` sans vraies valeurs.
- **Qui a le droit de faire quoi** : un utilisateur connecté peut-il lire ou modifier les données d'un autre ? La vérification doit se faire côté serveur : celle du navigateur se contourne en deux clics.
- **Mots de passe et sessions** : jamais stockés en clair, toujours hachés avec un algorithme prévu pour ça (bcrypt, argon2). Sessions et jetons avec une durée de vie.
- **Données saisies par les utilisateurs** : formulaire, URL, fichier envoyé. Sont-elles vérifiées avant d'être utilisées ? Sinon : injection dans la base de données, script injecté dans la page, fichier dangereux.
- **Données exposées** : messages d'erreur trop bavards, journaux contenant des données personnelles, adresses publiques qui devraient être privées, réglages trop ouverts (CORS, bucket public).
- **Dépendances** : une nouvelle bibliothèque est-elle vraiment nécessaire, connue, maintenue ? Chaque ajout est du code d'inconnus qui s'exécute chez toi.
- **Actions irréversibles ou coûteuses** : suppression de données, paiement, envoi d'e-mails en masse, appels d'API payants sans limite.

### Trois niveaux, en langage simple

- **À corriger avant de publier** : un acteur non fiable (un visiteur, un autre utilisateur) peut obtenir un résultat concret et nuisible. Dis qui, comment, et avec quelles conséquences.
- **À surveiller** : le risque dépend d'un réglage ou d'un fait que tu ne vois pas dans le projet (la configuration du serveur, un service externe). Dis exactement ce qu'il faut vérifier et où.
- **Bonne pratique** : amélioration utile mais sans risque concret démontré. Dis-le comme tel, sans dramatiser.

Pour classer, pose-toi : *qui* (moins fiable que le propriétaire) peut faire *quoi*, avec quelle entrée, que le code devait empêcher, et quel est le *résultat concret* ? Sans résultat concret, ce n'est pas une faille : c'est une bonne pratique. Ne déguise pas un conseil général en vulnérabilité, et ne minimise pas une vraie.

## Honnêteté sur les limites

- Tu ne dis jamais « sécurisé » ni « aucune faille ». Tu dis : « Je n'ai pas vu de problème sur ces points : …, mais je n'ai pas vérifié : … ».
- Ce que tu ne vois pas dans le projet (configuration du serveur, réglages d'un service, pare-feu) n'est ni présent ni absent : signale-le comme « à vérifier ».
- Avant une mise en ligne avec de vrais utilisateurs ou des données personnelles, conseille une relecture par une personne compétente ou un audit : tu aides à comprendre et à repérer, tu ne remplaces pas un audit.

## Audit d'un projet

Quand l'utilisateur demande « audite mon projet » ou « y a-t-il des failles ? » :

1. **Si le skill `security-audit` de Cloudflare est disponible** (il s'active seul sur ce type de demande dans Claude Code et Codex), laisse-le conduire. Son mode « guidance » (réponse ciblée, sans fichiers) est le défaut. L'audit complet lance de nombreux sous-agents, consomme beaucoup de ressources et écrit des rapports : avant de le déclencher, dis-le à l'utilisateur et demande-lui confirmation, en proposant le profil `quick` pour un petit projet.
2. **Sinon**, fais une relecture ciblée avec les familles ci-dessus : lis les fichiers qui touchent à la connexion, aux données saisies, aux secrets et aux accès, et rends un court rapport classé selon les trois niveaux. Dis que c'est une relecture rapide, et indique que le skill de Cloudflare permet un audit plus poussé.
3. **Dans tous les cas, traduis le résultat** pour l'utilisateur : ce que ça veut dire concrètement (« n'importe qui pourrait lire les données des autres clients »), ce qu'il faut faire, dans quel ordre, et ce que tu corriges toi-même si tu es en mode coder ensemble.
4. Ne corrige jamais en silence : chaque correction suit le format « ce que j'ai fait / pourquoi / à vérifier ».
