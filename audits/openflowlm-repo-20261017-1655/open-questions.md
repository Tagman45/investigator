# Open questions — renvoyées à la prochaine investigation (état négatif explicite)

| # | Question | État | Méthode nécessaire |
|---|---|---|---|
| Q1 | Les PR #206/#211/#169/#205 ont-elles bien un équivalent issue fermé ? (Corrélation issue/PR demandée par le skill) | NOT_FOUND_IN_SEARCHED_SCOPE | API authentifiée (GITHUB_TOKEN) ou export HTML paginé |
| Q2 | Le release MSI `oflm-setup.msi` correspond-il à la version du runtime scellé localement ? (aucun runtime FLM officiel versionné n'est comparé dans ce dossier) | NOT_YET_INSPECTED | télécharger le release et hasher (hors périmètre de la lecture seule de ce test) |
| Q3 | Le fork parent `OpenFlowLM` vs `OpenFlowLM-Next` : quel delta de contenu ? (aucune utilisation de `git remote` fetch ni de diff du clone) | NOT_YET_INSPECTED | `git fetch` + `git diff` réseau (autorisé, HTTPS) |
| Q4 | CNAME/domain (docs/ CNAME) : quel domaine de publication survit aux repos forkés ? | UNKNOWN | lookup DNS + fetch |
| Q5 | La limite `max_files` du skill rend l'inventaire partiel dans les repos à gros artefacts dee kernels (`open_kernels/**`) — est-ce couvert par une option d'abstraction prj/lock ? | UNKNOWN | patch/suggestion upstream du skill |
| Q6 | DeepWiki / GitDiagram : ce test les a-t-il intégrés à une investigation de Midjourney ? (non intégrés : aucun connecteur MCP déjà disponible) | INACCESSIBLE | à vérifier au fil des intégrations du plateau |
