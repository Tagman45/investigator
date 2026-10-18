# LIMITS — limitation (R1) + miroirs/backup (R2)

## 1. Limitation (R1) — ouvre trait à des questions non maîtrisées, pas à un
plancher de jugement

| R1 ouverte | Pourquoi elle n'est pas résolue ici | Délai / condition |
|---|---|---|
| Coverage réseau de la base de preuves | La commande `map` locale couvre `external_search=0` (repos déjà présents) ; une collecte distante (GitHub REST, gitlogs, DOIs) est une étape `external_search` à part entière → nécessite un jeton, un périmètre et une carte de frais, et ne peut pas être facturée sans une mission séparée | À ouvrir sur demande avec `--no-network` pour conserver le plancher UNVERIFIED honnête |
| Preuves runtime | `correlated.json` ne rend pas CONFIRMED_RUNTIME : le graphe de diagrammes statiques ne peut pas prouver l'exécution (chaque arête est VALUE/INFERRED/STAKE/MISSING). Une sourcing dynamique (logs d'exécution, MM2S/TCT, hook DeviceIoControl) est une mission dédiée | Séparer, ne pas confondre avec la cartographie statique |
| Périmètre statique vs dynamique | Tout ce qui touche au runtime (tests de dispatch, benchs, dissasm) hante déjà la session 30/07 du dossier `rapports/…_2026-08-07` et ne relève pas du graphe de provenance | Garder distinct — validation croisée en aval |

Règle de clôture : aucune affirmation essentielle ne peut être privée de
CONFIRMED sur base de l'absence ; on ne prétend pas `INEXISTANT`, on le
marque `NOT_FOUND_IN_SEARCHED_SCOPE` (le périmètre est le dépôt local +
données git accessibles + référentiels publics listés).

## 2. Miroirs et backups (R2) — règle de la session

R2 est une contrainte **opérationnelle** : les artefacts critiques
(`team.db`, `bus`, `rag_index.json`, la base de preuves, les rapports) sont
des candidats à la migration vers C: (NVMe), car E: est un HDD USB ~5 MB/s.
La migration n'est pas encore faite (01/09 : le dossier git-dédié est
identifié, mais le contenu n'a pas été replacé). R2 s'applique donc à
l'acte de **frontière** : un changement à la surface de l'environnement
(déplacement, recopie, migration, réplication) doit être documenté, SHA
vérifié, et nul part ne doit être caché.

Voici ce qui a été vérifié pour cette mission cartographe et ce qui reste
sur ce sujet (pas d'action créée par la mission) :

| Objet | État | Vérification |
|---|---|---|
| Toutes les fichiers d'EVD locaux (workspace, skill, tests, outputs) | dans `doc-skill-xdna2-work/` et `skills-audit-reports/`, aucun dossier supplémentaire créé à plat | `git status --short --branch` = 2 avances locales, working tree propre |
| Rapports (livrables 1-3, exemple, REA, LIMITS) | dans `audits/cartographer-20261017-2030/` | `ls` + `git ls-files` dans le dépôt git-dédié |
| SHA256 des artefacts ressenti | non besoin de report : ce n'est pas un artefact critique du périmètre de la mission (contenu code+docs, pas de base de données) | — |

**Au bout du compte** : la mission n'a pas créé de doublon, n'a pas
modifié les links distants, et les seuls poubles "miroirs" non identifiés
sont 2 dépôts distants déclarés (`origin main` : `doc-skill-xdna2` et
`investigator`), côté sauvegarde côté authentifiant. La verification
précédente (01/09) donne 37 repos sur disque, mais **ni leur contenu ni
leur empreintes ne sont verifiés** — ce n'est pas un miroir, c'est la
copie de travail du projet.

**Le seul point bloquant R2 reste** : l'avance locale non poussée des deux
dépôts git-dédiés, alors que les deux origins **existent et répondent**.

> **[CORRIGÉ 18/10/2026 — PREUVE]** L'énoncé antérieur « l'origin n'a jamais
> été vérifiée, donc le miroir distant n'existe pas encore » était FAUX.
> Vérification authentifiée (jeton `gh` compte Tagman45, scope `repo`) :
> `git ls-remote origin` répond sur les deux dépôts ;
> `gh repo list Tagman45` → `Tagman45/doc-skill-xdna2 private` (créé
> 2026-10-14, `pushed_at 2026-10-17T18:17:33Z`) et
> `Tagman45/investigator public` (`pushed_at 2026-10-17T18:17:26Z`).
> État de synchro : `doc-skill-xdna2` local `7e1a887` **1 commit d'avance**
> sur `origin/main` `546b2a3` ; `skills-audit-reports` local `3ddc089`
> **2 commits d'avance** sur `origin/main` `0fda41b`. Le 404 observé en
> anonyme sur `doc-skill-xdna2` s'explique par la visibilité **privée** du
> dépôt, pas par une absence de miroir. Aucun push n'a été exécuté ici
> (règle : pas de push sans autorisation expresse).
