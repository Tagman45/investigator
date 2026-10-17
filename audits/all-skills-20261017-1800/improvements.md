# Améliorations trouvées par le skill sur le parc skill (2026-10-17)

Scan : 212 fichiers (.md/.py) des deux racines, 255 références extraites, 80 URLs canoniques (43 GitHub), 121 chemins internes testés. Preuves : `evidence/audit-scan.json`, `evidence/missing-paths.json`, `evidence/homonym-skills-diff.json`.

## Corrigées le jour même (dossier fermé sur ces points)
| # | Objet | Amélioration | Preuve |
|---|---|---|---|
| I1 | `xdna2-evidence-oracle` copie opencode **pré-fix** | `oracle.py` 552 vs 587 lignes(fix nettoyage URLs du [CORRIGÉ 15/10]) 
`check_urls.py` 62 vs 81 lignes → **synchronisé workspace→opencode**, `diff -r` exit 0 | mtime 12:46 vs 22:34 (14/10) / 16:57 (15/10) |
| I2 | 4 skills homonymes sans frontière de rôle | **Domaines de spécialisation distincts** écrits dans les 4 `description:` (evidence-oracle = preuve locale, path-explorer = chemins matériels, cross-audit = décision/orchestration, git-eco-investigator = dépôts distants) — copies synchro | `specialization-matrix.md` |
| I3 | Rapports d'audit éparpillés dans le workspace | **Dépôt git dédié créé** `C:/Users/videl/skills-audit-reports` : un dossier par mission (`audits/<mission>/<horodatage>`), `INDEX.md` interrogeable, un commit par mission ; SKILL.md codifie la règle ; pointeurs `RELOCATED_*.md` posés à l'ancien emplacement | commit `c7dcefd` |

## À corriger (pas encore faites — appartenant à d'autres skills)
| # | Objet | Amélioration proposée | Statut |
|---|---|---|---|
| A1 | `aiehlc-cursor/kernelcodegen` : `references/project-layout.md` ET `references/compile-env.md` référencés mais **absents** | créer les 2 références ou retirer les mentions | OPEN (MISS-001/002) |
| A2 | `aiehlc-cursor/routinghwdebug` : `references/validation-rules.md` référencé 2×, **absent** | idem | OPEN (MISS-003) |
| A3 | 43 URLs GitHub citées dans les skills, **aucune sondée réseau** dans ce scan structurel | passer `collect_github_data.py` avec `GITHUB_TOKEN` (rate-limited sans jeton le 17/10, HTTP_403 5/5) | OPEN |
| A4 | `__pycache__` résiduels committés dans certaines copies de skills | purger puis ignorer (`.gitignore`) dans le dépôt dédié | OPEN |

## Coquilles reçues du test du skill lui-même (déjà traitées dans la mission openflowlm)
- Bug regex `inspect_repository.py` (parenthèse manquante) — corrigé localement le 17/10, **toujours présent en amont** `Tagman45/investigator` (arbre vide : impossible d'y contribuer aujourd'hui).
