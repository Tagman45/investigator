# INDEX — reports d'audits (interrogeable facilement)

| Dossier | Object | Date | Livrable principal | Statut |
|---|---|---|---|---|
| audits/openflowlm-repo-20261017-1655 | Test fonctionnel du skill sur le repo OpenFlowLM-Next | 2026-10-17 | repository-inventory.md + ecosystem-graph.mmd, PIPE runnees | PASS (integration EVD-20261017-009) |
| audits/all-skills-20261017-1800 | Audit de TOUS les skills (2 racines: workspace + opencode) | 2026-10-17 | audit-scan.json + specialization-matrix.md + improvements.json | en cours (EVD-20261017-010) |

Comment interroger : `git log --oneline -- audits/<objet>` ; grep inter-dossiers `grep -r "URL-004" audits/`.
