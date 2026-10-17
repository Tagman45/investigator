# RAPPORT M3 — Mission REA d'amélioration du skill `git-ecosystem-investigator`

Date : 17/10/2026 · Dossier mission : `audits/skill-improvement-rea-20261017-180727`
Dépôt cible : `C:\Users\videl\Desktop\doc-skill-xdna2-work`
Copies du skill : copie de référence (`skills/local/git-ecosystem-investigator`) + copie insight (`~/.config/opencode/skills/git-ecosystem-investigator`)

---

## 1. Findings (démontrés, pas déclarés)

### F1 — P0 : crash FileNotFoundError sur ledger absent [RÉPARÉ]
- **Preuve AVANT** (reproduction sauvegardée en baseline de mission) : `python coverage_report.py --ledger absent.jsonl` → traceback `FileNotFoundError`, **exit 1**.
- **Effet** : l'absence de preuve plantait l'outil, court-circuitant le principe REA « absence de preuve ≠ réfutation ».
- **Preuve APRÈS** : même invocation → JSON de rapport, statut `UNKNOWN` explicite, raison `FILE_ABSENT` tracée, **exit 0**.

### F2 — P1 : JSON invalide → crash non tracé [RÉPARÉ]
- **AVANT** : lignes JSONL corrompues → exception `json.JSONDecodeError` non gérée, crash.
- **APRÈS** : raison `INVALID_JSON` consignée dans `inputs.absents` + finding dédié, statut `UNKNOWN`, exit 0. Erreur `READ_ERROR` aussi gérée (permissions, Unicode).

### F3 — P1 : métrique `unique_destinations` trompeuse [RÉPARÉ]
- **AVANT** : le champ était calculé `len({canonical_url or url})` → sur le registre réel `experiments/EVIDENCE_LEDGER.jsonl` (93 lignes, clés `source`/`proof`/`evidence`, **aucun** champ URL), le script annonçait `unique_destinations = 1` — un artefact qui laissait croire un registre à destination unique.
- **Preuve** : détection de clés URL par analyse des 93 lignes réelles → `statement` contient des URLs dans 2 lignes seulement ; registre expérimental, pas registre web.
- **APRÈS** : extraction depuis un jeu de clés plausibles (`canonical_url`, `url`, `target_url`, `link`, `proof_url`) ; si aucune → `unique_destinations: null` + finding de diagnostic explicite ("registre sans champ URL, chaque ligne est une preuve expérimentale").

### F4 — invariant structurel sain [CONFIRMÉ]
- Les 2 copies du skill étaient identiques SHA-256 avant mission (divergence copie/insight = zéro) → la correction s'applique depuis la copie de référence et est **diffusée** vers l'insight, jamais en sens inverse.

---

## 2. Changes (minimaux, jamais d'écrasement)

| Fichier | Change | Contrôle |
|---|---|---|
| `scripts/coverage_report.py` | P0 : absence de preuve → statut `UNKNOWN` + raison tracée, exit 0 (au lieu du crash `FileNotFoundError`). P1 : JSONL invalide → `INVALID_JSON` tracé, pas de crash. P1 : `unique_destinations` clés plausibles, `null` + finding si aucune clé URL (au lieu de compter 1). | Contrat de sortie inchangé (`coverage-report.md` avec bloc ```json```). |
| `tests/test_negative.py` (NOUVEAU) | 4 cas négatifs REA : (1) ledger absent → `UNKNOWN` + `FILE_ABSENT` + exit 0, (2) JSON invalide → `INVALID_JSON`, (3) non-régression du chemin valide → `MEASURED`, (4) `--collection` absent → pas de crash. | `pytest tests/ -q` : **7 passed** (4 nouveaux + 3 existants). |
| Copie insight | Diffusion depuis la copie de référence, après archivage de sa version pré-diffusion. | SHA-256 identiques sur les deux copies. |

Ordre de diffusion : copie de **référence** corrigée d'abord, **diffusion** one-way vers insight, jamais l'inverse (règle imposée par la mission).

---

## 3. Validation

| run | résultat |
|---|---|
| Reproduction AVANT (baseline) | exit 1, traceback `FileNotFoundError` → consigné comme preuve de travail |
| `pytest tests/` copie de référence | **7/7 passed**, exit 0 |
| `pytest tests/` copie insight | **7/7 passed** après synchronisation des tests depuis la copie de référence |
| `coverage_report.py` sur ledger réel (93 lignes) | exit 0, `MEASURED`, `rows: 93 | unique: null | unresolved: 0` |
| `coverage_report.py` sur ledger corrigé (63 lignes) | exit 0, `MEASURED`, `rows: 63 | unique: null` |
| SHA avant/après diffusions | 87df6fc9… → 7b97d2be… *(ALL copies identiques post-diffusion)* |
| Livrables historiques intacts | ✔ — le registre `experiments/EVIDENCE_LEDGER.jsonl` n'a **jamais été touché**, seuls les artefacts de mission écrits sous `audits/skill-improvement-rea-…` ; pas de réécriture de statuts |
| Daemon auto-commit | **SUSPENDU** conformément à REA — aucun commit/push pendant ou après la mission sans ton « go » explicite |

---

## 4. Risques résiduels

1. Les tests `UNRESOLVED` ne gouvernent que les statuts `INCONCLUSIVE` ; les statuts expérimentaux (`REFUTED`, `FAIL`) **ne déclenchent pas** `unresolved_rows`. Extension possible : `reprobe` devant profil différent au registre de vérification d'URLs.
2. La mission a validé un seul type de registre (`EVIDENCE_LEDGER.jsonl`). Le chemin « collections » (`--collection`) a son test négatif mais n'a pas été exercé sur une collection réelle de grande taille.
3. Exit code : le crash n'est plus utilisé comme signal. Le script **résume** maintenant tout dans le JSON de rapport — un consommateur qui ne lit que l'exit code perdra certains échecs partiels. Documenté dans le script.

---

## 5. Note du skill (diagnostics de la mission)

- Discipline REA **appliquée sur le réel** : chaque finding est qualifié par un run AVANT/APRÈS, jamais par intuition.
- La mission s'est tenue **sans auto-push** — la contrainte REA (pas de commit/push sans autorisation) a été respectée de bout en bout ; le daemon reprend sur ton « go ».
- Vérification : la boucle test→réparation→re-test (7 tests) est entièrement locale, sans réseau.

---

## 6. Artefacts mission

```
audits/skill-improvement-rea-20261017-180727/
├── MISSION-REA-AMELIORATION.md
├── README-EXECUTION.md
├── baseline-manifest.json
├── baseline/            ← preuves AVANT + versions pré-diffusion archivées
├── after/               ← preuves APRÈS (cov_real.md, cov_real_corrected.md)
└── evidence/            ← captures de runs
```

Fichiers produit par la mission (hors artefacts de mission) :
- `skills/local/git-ecosystem-investigator/scripts/coverage_report.py` (réécrit)
- `skills/local/git-ecosystem-investigator/tests/test_negative.py` (créé)
- `~/.config/opencode/skills/git-ecosystem-investigator/scripts/coverage_report.py` (diffusé depuis référence)
