# INDEX — reports d'audits (depot dedie, un dossier par mission)

| Mission | Dossier | Objet | Date | Statut |
|---|---|---|---|---|
| M1 | `audits/openflowlm-repo-20261017-1655` | Test fonctionnel du skill sur le repo OpenFlowLM-Next (6 scripts, 14 livrables, graphe 7 aretes) | 2026-10-17 | PASS (EVD-20261017-009, bug regex corrige) |
| M2 | `audits/all-skills-20261017-1800` | Audit de TOUS les skills (212 fiches scannees, 255 refs, 80 URLs, 4 liens morts, 1 derive syncronee corrigee, matrice de specialisation) | 2026-10-17 | PASS (EVD-20261017-010, 4 ameliorations closes + 4 ouvertes) |
| M3 | `audits/investigation-universelle-pilote-20261017-191211` | Pilote moteur universel : 3 domaines (dépôt-git/science/histoire), 8 recherches réelles tracées, 3 bilans VERIFIED, 42/42 tests | 2026-10-17 | ACCEPT (16 réussis, 0 échoués, 1 NV justif., 2 NA justifiés) |
| M4 | `audits/cartographer-20261017-2030` | Mission cartographe : baseline 104/107→110/110, bug multi-repo correlate corrigé, formats/+LIMIT_CODES, docs schéma/vues, exemples mono+écosystème validés, daemon auto-push suspendu, 0 push | 2026-10-17 | DONE (commits locaux, daemon à restaurer) |

Interroger facilement :
- `git log --oneline -- audits/<mission>` (historique par mission)
- `grep -r "MISS-001" audits/` (retrouver une amelioration par evidence_id)
- `INDEX.md` a la racine = point d'entree unique.
