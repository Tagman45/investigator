# Mission REA — correction D1→D8 (18/10/2026)

Statuts utilisés : `FACT` (vérifié ici, commande + code de sortie), `DERIVED`,
`UNKNOWN` (pas de preuve), `INACCESSIBLE` (outil/environnement absent).

---

## 0. État initial constaté (avant toute modification)

**Écart de base à signaler** : la mission annonçait « dépôt `doc-skill-xdna2`,
commit `86afdf3` ». Vérifié :

| Constat | Preuve |
|---|---|
| `86afdf3` **n'existe pas** dans `doc-skill-xdna2-work` | `git cat-file -t 86afdf3` → `fatal: Not a valid object name` |
| `86afdf3` appartient à `skills-audit-reports`, dont HEAD est `b8dba31` | `git log --oneline -1` dans ce dépôt |
| `doc-skill-xdna2-work` : HEAD `aefd132`, aligné sur `origin/main` (`0 0`) | `git rev-list --left-right --count origin/main...HEAD` |
| `skills-audit-reports` : HEAD `b8dba31`, **2 commits d'avance**, non poussés | idem → `0 2` |

Base réellement utilisée : les deux dépôts, chacun à son HEAD, **sans réécriture
ni reset**. Les défauts D1-D8 vivent dans les skills installés
(`~/.config/opencode/skills`) ; les rapports et les tests dans
`skills-audit-reports`.

---

## 1. Skills obligatoires — registre et pré-vol

| Skill | Lu (hash enregistré) | Appliqué | Preuve |
|---|---|---|---|
| `evidence` | ✅ | D4 + statuts du rapport | `audits/skills-usage/skills_usage.jsonl` |
| `debug-method` | ✅ | reproduction avant conclusion (D1-D8) | idem |
| `search-policy` | ✅ | recherches ciblées, pas de scan récursif E: | idem |
| `xdna2-cross-audit` | ✅ | matrice affirmation→preuve→statut | idem |
| `xdna2-path-explorer` | ✅ | D6 (COST_MODEL + validateur) | idem |
| `git-ecosystem-investigator` | ✅ | référentiel de preuve, tests 135 audités | idem |

```
python tools/skills_preflight.py --task fix-defects
→ OK: fix-defects          (exit 0)

python tools/skills_preflight.py --task remote-publish
→ BLOCKED: remote-publish  (exit 3)
   - SKILL_NOT_READ evidence
   - GIT_AUTHORIZATION_NOT_CHECKED
```

`remote-publish` est **bloquée** : aucune autorisation git n'a été fournie ni
vérifiée. C'est le comportement attendu, pas un échec.

---

## 2. D1 → D8 : avant / après

| # | Avant (preuve du 18/10) | Correction appliquée | Après (test) | Statut |
|---|---|---|---|---|
| **D1** | 0/5 refs depuis l'installation, 5/5 depuis le dépôt | `scripts/check_refs.py` (base `--base`/`OFLM_REPO`/remontée/git toplevel, codes 3/4) + SKILL.md : base explicite, 3 modes d'installation | `test_d1_refs_resolvent_depuis_le_depot` (exit 0, 5/5) ; `test_d1_sans_base_echoue_avec_code_nomme` (exit 3, `REFERENCE_BASE_NOT_FOUND`) | **CORRIGÉ** |
| **D2** | `Bundle max : 0`, exit 0, sans alerte | `inspect_kernel.ps1` : `NOT_MEASURED` + nombre d'instructions non classifiées, couverture partielle signalée, **défaut = exit 2**, `-Lenient` → 0 | 5 tests : sans marqueur (sort 2), avec marqueur (`7`), vide, mixte (PARTIELLE), interface `-Lenient`/absence de `-Strict` | **CORRIGÉ** — `[CORRIGÉ 18/10/2026]` la colonne « `-Strict` → exit 2 » était **fausse** : l'option `-Strict` n'existe pas dans le script (voir §12.1) |
| **D3** | script annoncé « lance la validation A/B », écrit un gabarit | renommé `new_validation_report.ps1`, en-tête « GABARIT MANUEL », exit **3 (UNKNOWN)** après écriture ; SKILL.md corrigé | `test_d3_ancien_nom_supprime_et_doc_corrigee`, `test_d3_script_sort_3_et_ne_fabrique_pas_de_resultat` | **CORRIGÉ** (validation réelle : `INACCESSIBLE` — pas de llama-server/xclbin ici) |
| **D4** | « `evidence.py` peut ne pas exister » | mention corrigée avec preuve datée, historique conservé dans l'audit | `test_d4_mention_perimee_corrigee` | **CORRIGÉ** |
| **D5** | environnements supposés, aucun contrôle ; premier préflight WSL-only ⇒ « 6 manquants » | `preflight_mlir_aie.py` **deux plateformes** (Windows natif puis WSL, 0/3/4) + section Préflight dans les 3 skills noyaux + `docs/setup_mlir_aie_wsl.md` | **2e passe** : `PREREQUIS_OK` sur **Windows** (`mlir_aie`, `aie.iron`, `aiecc --version`, `xclbinutil` XRT 2.21.0, `aiebu-asm`, `xchesscc_wrapper`) ; **WSL** incomplet (5 manquants). `test_d5_preflight_mlir_aie_deux_plateformes`, `test_d5_wsl_force_reste_signale_comme_incomplet` | **MISDIAGNOSTIC CORRIGÉ** — chaîne Windows prête. [CORRIGÉ 18/10/2026] **build smoke exécuté** : `aiecc` → `out.xclbin` (magic `xclbin2`, 6818 octets, exit 0) ; preuve **machine** `evidence/aiecc_smoke/runs/<UTC>/` (artefact + sorties + env + sha256) ; le manifeste manuel du dossier parent est `INFERRED` (voir `ORIGINE_MANIFESTE.md`) ; les builds de kernels réels restent `UNKNOWN` |
| **D6** | `COST_MODEL.json` listé, absent (`CostModelTemplate.json` seul) | SKILL.md : produit par `generate_evidence.py` (schéma v1.0, unités `us`, `DATA_PENDING`) + `scripts/validate_cost_model.py` | `test_d6_le_cost_model_du_generateur_est_valide` (constante réelle → `[]`), + unité invalide, valeur inventée, champ manquant, non numérique, CLI absent (2) / invalide (5) | **CORRIGÉ** |
| **D7** | MAC comptés par ligne (1 au lieu de 4) | comptage par occurrence dans `inspect_kernel.ps1` | `test_d7_mac_comptes_par_occurrence` → `Nombre de MAC : 4` | **CORRIGÉ** |
| **D8** | 4 scripts, 1 documenté | SKILL.md `§4bis` : tableau des 4 scripts (interface vérifiée) + limites (`--index` requis) | `test_d8_chaque_script_oracle_est_documente` (itère sur `scripts/*.py`) | **CORRIGÉ** |

### Preuve « avant » conservée
Les sorties d'origine ne sont pas écrasées : elles restent dans
`audits/skills-contract-20261018/CHECK_LOG.md` et
`evidence/npu_refs/npu_refs_resolution.json`. Les fixtures de reproduction sont
dans `tests/fixtures/aie2p/`.

### Limite honnête sur « rouge avant, vert après »
Le code d'origine n'a pas été versionné (skills hors dépôt git) : la démonstration
« le test échoue sur l'ancienne version » repose sur les sorties d'audit
enregistrées (`Bundle max : 0`, 0/5 refs, MAC=1), pas sur une ré-exécution de
l'ancien binaire. Seul D1 est rejouable en l'état : `check_refs.py` sans base →
exit 3 (comportement « avant » = silence).

---

## 3. Garde-fou d'autorisation git

`tools/git_authorization.py` — une autorisation n'est valide que si :

- `origin == "user_message"` (les origines `agent`, `audit_accept`, `accept`,
  `existing_commit`, `other_agent`, `project_acceptance` sont **refusées**) ;
- dépôt, branche et commit concordent (normalisation URL/chemin) ;
- `request_excerpt` non vide et `user_turn_ref` présent ;
- l'autorisation n'a pas déjà été consommée (`used_for`).

`record` refuse une citation vide ou une référence de tour absente : l'outil ne
peut pas fabriquer l'autorisation.

**Tests : 15** (`tests/test_git_authorization.py`) — absente, affirmation de
l'agent, simple ACCEPT, commit existant, autre dépôt, autre commit, autre
branche, citation vide, autorisation consommée, SHA invalide, JSON illisible,
autorisation explicite vérifiable (seul ALLOW), refus de `record`.

**Pré-vol lié** : `--task remote-publish` sans `--repo/--branch/--commit` →
`GIT_AUTHORIZATION_NOT_CHECKED` ; avec des arguments mais sans autorisation →
`GIT_AUTHORIZATION_ABSENTE` (2 tests).

### Bilan des permissions (exigé par le contrat)

| Élément | État |
|---|---|
| Permission **vérifiée** pour un push | **aucune** |
| Permission **absente** | oui — aucune autorisation utilisateur traçable pour `skills-audit-reports` ni `doc-skill-xdna2` |
| Opération distante **tentée** dans cette mission | **aucune** (`git push` jamais exécuté) |
| Opération distante **réalisée** | **aucune** |
| Incident antérieur (M6) | push déjà exécuté (`doc-skill-xdna2-work` = `aefd132`) sans autorisation traçable ; **aucune réécriture d'historique**, aucune correction distante tentée ; consigné dans `INDEX.md` |

---

## 4. Tests exécutés

| Commande | Résultat | Portée |
|---|---|---|
| `python -m pytest tests -q` (skills-audit-reports) | **51 passed, exit 0** (15,90 s) | garde-fou git (15), pré-vol (10), D1-D8 + addendum (26). [CORRIGÉ 18/10/2026] **52 passed** après ajout du test de build smoke (§10.6) |
| `python -m pytest tests -q -rs` ×3 copies (git-ecosystem-investigator) | **135 passed, 0 skipped, exit 0** | audit `conftest.py` (mission précédente, re-exécuté) |
| `python tools/skills_preflight.py --task fix-defects` | **exit 0** | skills obligatoires lus/appliqués |
| `python tools/skills_preflight.py --task remote-publish` | **exit 3** (bloqué) | tâche protégée |
| `python .../preflight_mlir_aie.py` | **exit 3** | D5 : 6 prérequis manquants |
| `python .../check_refs.py --base <repo>` | **exit 0, 5/5** | D1 |
| `python .../check_refs.py` sans base | **exit 3** | D1 (échec nommé) |
| `python .../validate_cost_model.py` (constante du générateur) | **PASS (`[]`)** | D6 |
| `python .../validate_cost_model.py` fichier absent | **exit 2** | D6 |
| `powershell inspect_kernel.ps1` ×5 fixtures (+ `-Strict`) | exit 0 / 2 attendus | D2, D7 — `[CORRIGÉ 18/10/2026]` la mention `-Strict` était erronée : les exécutions réelles utilisent le **défaut (2)** et `-Lenient` (0), cf. §12.1 |
| `powershell new_validation_report.ps1` | **exit 3** + gabarit | D3 |

## 5. Non exécuté — et pourquoi

| Élément | Statut | Cause |
|---|---|---|
| Builds XCLBIN réels (Qwen3.6, Phi-3, Nanbeige) | `UNKNOWN` | **non lancés** : la chaîne Windows est pourtant complète (`PREREQUIS_OK`), mais aucun build de kernel réel n'a été exécuté (durée, artefacts) ; côté WSL, 5 prérequis manquent. [CORRIGÉ 18/10/2026] un **build smoke** a depuis été exécuté et vérifié : voir §10.6 — la chaîne de compilation est `TESTED` (compilation seule), les kernels réels restent `NOT TESTED` / `UNKNOWN` |
| Build Granite (Windows) | `UNKNOWN` | `xclbinutil.exe`/`aiebu-asm.exe` à la racine de `C:\Xilinx\XRT` et sur le PATH, `mlir_aie`+`aiecc` OK ; `iron_env.ps1`/`VCVARS64` non testés, build non lancé |
| Validation A/B réelle (`new_validation_report.ps1`) | `INACCESSIBLE` | pas de `llama-server` ni de paire de xclbins ; le script sort 3 (UNKNOWN) |
| Tests NPU / latence / débit | `UNKNOWN` | aucune expérience matérielle |
| APK sur device | `INACCESSIBLE` | 0 device attaché |
| `git push` | **non tenté** | aucune autorisation vérifiable |

---

## 6. Fichiers modifiés (non commités)

**Skills installés** (`C:/Users/videl/.config/opencode/skills`) :

- `npu-offload-pipeline/SKILL.md` (+`scripts/check_refs.py`) — D1
- `aie2p-hand-asm-debug/scripts/inspect_kernel.ps1` — D2, D7
- `aie2p-hand-asm-debug/scripts/validate_kernel.ps1` → **renommé** `new_validation_report.ps1` — D3
- `aie2p-hand-asm-debug/SKILL.md` — D3 (+ limite « max 6/bundle » requalifiée `UNKNOWN`)
- `evidence/SKILL.md` — D4
- `open-qwen36-kernels/scripts/preflight_mlir_aie.py` (+SKILL.md) — D5
- `open-phi3-nanbeige-kernels/SKILL.md`, `open-granite-kernels/SKILL.md` — D5
- `xdna2-path-explorer/SKILL.md` + `scripts/validate_cost_model.py` — D6
- `xdna2-evidence-oracle/SKILL.md` — D8

**Copies synchronisées** (`doc-skill-xdna2-work/skills/local`) :
`xdna2-path-explorer` et `xdna2-evidence-oracle` — `diff -rq` **exit 0**.

**Dépôt `skills-audit-reports`** (non commité) :
`AGENTS.md`, `tools/git_authorization.py`, `tools/skills_preflight.py`,
`tools/skills_registry.json`, `tests/` (4 fichiers + fixtures), `audits/skills-usage/`,
ce rapport.

`[AJOUTÉ 18/10/2026]` — outillage et preuves de la requalification :
`tools/aiecc_smoke_evidence.py` (harnais de preuve machine, compilation seule),
`audits/skills-fix-20261018/evidence/aiecc_smoke/runs/<UTC>/` (10 fichiers :
artefact `out.xclbin` conservé, `stdout.txt`, `stderr.txt`, `env.txt`,
`command.txt`, `min.mlir`, `xclbin_info.txt`, `manifest.json` + sorties de build),
`audits/skills-fix-20261018/evidence/aiecc_smoke/ORIGINE_MANIFESTE.md`
(requalifie le manifeste manuel en `INFERRED`, sans l'effacer) ;
`tests/test_skills_fixes.py` : +3 tests (manifeste machine, refus d'artefact
altéré, interface `-Lenient`).

## 7. État git final

| Dépôt | HEAD | Avance | Commits créés ici | Push |
|---|---|---|---|---|
| `skills-audit-reports` | `b8dba31` | 2 | **aucun** (mission : pas de commit sans demande) | **aucun** |
| `doc-skill-xdna2-work` | `aefd132` | 0 | aucun | aucun |

Modifications laissées **dans le working tree**, prêtes à être relues.

## 8. Risques restants

1. **Secrets/artefacts** : aucun secret ajouté ; `tests/fixtures/` ne contient
   que des kernels synthétiques et le JSON de résolution.
2. **D3** : le nom du script a changé — tout appel externe à
   `validate_kernel.ps1` échouera (voulu, mais à annoncer).
3. **D2** : `-Strict` n'est pas activé par défaut ; sans lui, un kernel non
   annoté produit un avertissement mais exit 0.
   `[CORRIGÉ 18/10/2026]` **phrase fausse** : il n'existe pas d'option
   `-Strict`. Le **défaut est déjà 2** sur couverture incomplète et c'est
   `-Lenient` qui rétablit 0. Preuve : `inspect_kernel.ps1:15,158` (0 occurrence
   de `Strict`) ; `-Strict` en ligne de commande → **exit 1** (paramètre
   inexistant). Voir §12.1.
4. **D6** : le schéma est celui du générateur `generate_evidence.py` ; si ce
   dernier change, le validateur doit suivre (aucun test de synchronisation
   croisée automatique).
5. **D5** : aucun build n'a été exécuté ; les skills restent `UNKNOWN` sur cette
   machine jusqu'à préparation de l'environnement. [CORRIGÉ 18/10/2026] côté
   **Windows**, un build smoke a depuis été exécuté et vérifié (§10.6) ; côté
   **WSL**, l'installation reste à faire.
6. **Contrat d'instructions** : ajouté à `AGENTS.md` (dépôt) — un test vérifie sa
   présence, mais **aucun test ne peut prouver qu'un LLM le charge**.

---

## 9. Addendum — second passage de corrections (18/10/2026)

| Élément | Correction | Preuve / test |
|---|---|---|
| Statut lisible (D2/D7) | `inspect_kernel.ps1` termine par une ligne unique `STATUS: OK / PARTIAL / NOT_MEASURED / BUNDLE_LIMIT_EXCEEDED` | `test_statut_unique_par_fixture` (4 fixtures, dont `ok.s`) |
| D6 exemple livrable | `examples/COST_MODEL.example.json` généré depuis la constante réelle du générateur (8 métriques, `value: null`) et validé | `test_d6_exemple_livre_et_valide` (exit 0) |
| D5 procédure reproductible | `open-qwen36-kernels/docs/setup_mlir_aie_wsl.md` : sources officielles mlir-aie, `env_install.sh`/`env_setup.sh`, séparation WSL/Windows, statut `NON EXÉCUTÉE` | `test_d5_procedure_reproductible_documentee` |
| Dette de test | helper mort `run_report()` supprimé dans les **3 copies** de git-ecosystem-investigator (`diff -rq` exit 0) | `test_helper_mort_supprime_dans_les_trois_copies` |
| Ambiguïté de nom | aucun `SKILL.md` ne pointe `scripts/validate_kernel.ps1` ni n'annonce « Lancer la validation A/B » ; la mention historique est conservée | `test_plus_aucune_instruction_vers_le_script_renomme` |

**Non corrigé, et pourquoi** : les **builds** restent `UNKNOWN` — aucun XCLBIN
n'a été compilé. Ce n'est plus un problème de dépendances (voir §10).
[CORRIGÉ 18/10/2026] un XCLBIN **smoke** a depuis été compilé et vérifié
(§10.6) ; les kernels du projet, eux, ne sont toujours pas compilés.

**Suite de tests finale** : **51 passed, exit 0** (15 + 10 + 26) — puis
**52 passed** après §10.6.

Après suppression du helper mort, la suite du skill `git-ecosystem-investigator`
a été **re-exécutée** (le changement touche ses fichiers de test) :
**135 tests collectés, exit 0 sur les 3 copies** (`-q -rs`).

---

## 10. Troisième passe — D5 re-diagnostiqué, safe-by-default, incident M6

### 10.1 D5 : le blocage venait de la méthode, pas des dépendances

Le premier préflight ne testait **que WSL** et concluait « 6 prérequis
manquants ». Vérification directe du 18/10 sur Windows (`FACT`, exit codes) :

| Commande | Résultat |
|---|---|
| `python -c "import mlir_aie, aie.iron"` | exit 0 |
| `aiecc --version` | exit 0 — *mlir-aie declarative driver*, git SHA `af819a802f4` |
| `xclbinutil --version` | exit 0 — **XRT 2.21.0** |
| `command -v aiecc xclbinutil aiebu-asm xchesscc_wrapper` | les 4 présents |
| `wsl -e bash -lc '…'` | `mlir_aie`, `xclbinutil`, `aiebu-asm`, `~/ironenv142`, `~/xrt-tools/bin` **absents** |

`preflight_mlir_aie.py` teste désormais **les deux plateformes** et sort
`PREREQUIS_OK` (exit 0) avec `plateforme_utilisable: ["windows"]` ; forcé sur
WSL (`--platform wsl`), il sort 3 avec la liste exacte des manquants.

**Ce qui change** : les skills Qwen3.6 / Phi-3 / Nanbeige ne sont **pas**
bloqués par des dépendances introuvables ; ils sont bloqués par l'absence de
build exécuté. Le statut reste `UNKNOWN`, mais la cause est désormais exacte.

**Ce qui ne change pas** : aucun XCLBIN n'a été produit ; aucune mesure NPU ;
aucune validation A/B. Un build Windows réussi ne prouverait pas non plus la
latence du runtime. [CORRIGÉ 18/10/2026] un XCLBIN **smoke** (design trivial) a
depuis été produit — §10.6 ; aucun XCLBIN de **kernel du projet** n'existe, et
la conclusion sur la latence reste identique.

### 10.2 `inspect_kernel.ps1` : safe-by-default

Décision appliquée : une couverture incomplète (aucun marqueur `## @`, ou
instructions non classifiées) sort désormais **2 par défaut**. `-Lenient`
rétablit un exit 0 pour l'usage purement informatif. Vérifié sur les fixtures :
`sans_marqueur` → 2, `mixte` → 2, `ok` → 0, `avec_marqueur` → 0,
`sans_marqueur -Lenient` → 0.

### 10.3 D6 : synchronisation générateur ↔ validateur

`test_d6_metriques_generateur_et_validateur_synchronisees` compare, **dans les
deux sens**, `generate_evidence.COST_MODEL["metrics"]` et
`validate_cost_model.REQUIRED_METRIC_KEYS`. Une clé ajoutée d'un seul côté fait
échouer le test ; `schema_version` doit rester `1.0`.

### 10.4 Incident M6

`INCIDENT_PUSH_M6.md` : faits, preuves (`0 0` sur doc-skill-xdna2, `0 2` sur
skills-audit-reports), ce qui a été fait (correction documentaire uniquement),
ce qui n'a **pas** été fait (aucune réécriture, aucun force-push), et trois
options soumises à décision utilisateur. Aucune action distante.

### 10.5 État final de cette passe

- `pytest tests -q` → **51 passed, exit 0** (puis **52** après §10.6, **54** après §12, **55** après §12.1).
- Pré-vol `fix-defects` → OK ; `remote-publish` → BLOCKED (aucune autorisation).
- **0 commit, 0 push** ; modifications dans le working tree.
- Restent `UNKNOWN` : builds de kernels réels, NPU, validation A/B, APK.

### 10.6 D5 exécution : le build smoke a été lancé (plus `UNKNOWN`)

Le §10.1 disait « le statut reste `UNKNOWN` » faute de build. Ce point est
**corrigé avec preuve** : un design MLIR minimal (`aie.device(npu1)`, 1 tile,
`runtime_sequence` vide) a été compilé par `aiecc` sur Windows.

| Preuve | Valeur |
|---|---|
| Commande | `aiecc min.mlir --xclbin-name=out.xclbin --get-xclbin --output-dir=<tmp>/o2` |
| Exit | **0** (30 étapes de pipeline) |
| Artefact | `out.xclbin` — **6818 octets**, magic **`xclbin2`**, sha256 `d823a6b9…6a43` |
| Vérification croisée | `xclbinutil --info` (XRT 2.21.0) : sections MEM_TOPOLOGY, AIE_PARTITION, EMBEDDED_METADATA, IP_LAYOUT, CONNECTIVITY, GROUP_CONNECTIVITY, GROUP_TOPOLOGY |
| Dossier | `audits/skills-fix-20261018/evidence/aiecc_smoke/` (`manifest.json` **manuel — `INFERRED`**, `min.mlir`, `xclbin_info.txt`) + `runs/<UTC>/` **preuve machine** + `ORIGINE_MANIFESTE.md` |
| Automatisation | `test_d5_aiecc_compile_un_design_minimal` — recompile à chaque exécution et **assertionne** exit 0 + présence du fichier + magic `xclbin2` (pas de `skip` silencieux si `aiecc` existe) |

**Portée exacte** : `TESTED` (compilation uniquement) = la chaîne AIE produit
un XCLBIN valide sur Windows. **NOT TESTED** : kernels réels (Qwen3.6 / Phi-3 /
Nanbeige / Granite). **UNKNOWN** : exécution NPU, latence, débit, validation
A/B. **INFERRED** : aucune conclusion de ce paragraphe ne dépasse le build smoke.

#### [CORRIGÉ 18/10/2026] Preuve requalifiée : le premier manifeste était manuel

La phrase « corrigé avec preuve » ci-dessus était **trop forte** au regard de la
règle « une preuve doit être machine et rejouable » : le `manifest.json` de ce
dossier avait été **rédigé à la main** après un build exécuté dans un dossier
temporaire (`…/Temp/aiecc_smoke/o2`). Ni `out.xclbin`, ni `stdout`/`stderr`, ni
la version d'`aiecc` n'avaient été conservés : les valeurs (6818 o, sha256
`d823a6b9…`) n'étaient donc pas revérifiables → statut **`INFERRED`**, pas
`TESTED`. Le manifeste manuel est **conservé tel quel** (historique) et son
origine est documentée dans `evidence/aiecc_smoke/ORIGINE_MANIFESTE.md`.

Preuve **machine** produite depuis par `tools/aiecc_smoke_evidence.py`
(`evidence/aiecc_smoke/runs/20261018T072027Z/`) :

| Élément exigé | Valeur enregistrée |
|---|---|
| Commande exacte | `aiecc min.mlir --xclbin-name=out.xclbin --get-xclbin --output-dir=…/o` (argv complet + `cwd` dans `manifest.json`/`command.txt`) |
| Code de sortie | **0** |
| Sortie utile | `stderr.txt` = 30 étapes de pipeline ; `stdout.txt` = 1 avertissement |
| Environnement | `env.txt` : `aiecc` `af819a802f4` (compiled Aug 28 2026), Python 3.13.13, Windows-11-10.0.26200, AMD64 |
| Artefact | `out.xclbin` **conservé** — 6818 o, magic `xclbin2`, sha256 `6e83a976…7051` |
| Vérification croisée | `xclbin_info.txt` — `xclbinutil --info`, exit 0 |
| Statut écrit | `status: TESTED`, `scope: COMPILATION_ONLY_NO_NPU`, `duration_s: 0.182` |
| Revalidation sans rebuild | `python tools/aiecc_smoke_evidence.py --check-only <run_dir>` → OK (et **INVALIDE** si l'artefact est altéré ou absent) |

**Ce que cette preuve ne dit toujours pas** : aucun kernel du projet n'a été
compilé, rien n'a tourné sur le NPU, aucune performance n'a été mesurée ; aucun
« PASS » au sens d'une exécution matérielle n'est revendiqué.

## 11. Ce qui reste non corrigé — assumé

Ces quatre points ne sont pas des oublis : ils sont **hors de portée** de cette
passe, et documentés comme tels. Aucun n'est présenté comme corrigé.

| # | Point | Statut | Pourquoi il n'est pas corrigé ici |
|---|---|---|---|
| 1 | **D5 exécution côté WSL** (`env_install.sh`, XRT, Peano) | `UNKNOWN` | c'est une **installation système lourde** (paquets Linux, toolchain) non autorisée dans cette passe. Livré : procédure reproductible (`docs/setup_mlir_aie_wsl.md`) + préflight qui **nomme** les 5 manquants (`--platform wsl` → exit 3). Le côté Windows, lui, est `TESTED` en compilation (§10.6) |
| 2 | **Validation A/B réelle** (`new_validation_report.ps1`) | `INACCESSIBLE` | ni `llama-server` ni paire d'XCLBIN comparables sur cette machine. Le script **écrit un gabarit puis sort 3 (UNKNOWN)** : il ne peut pas fabriquer un résultat. Corriger exigerait le matériel, pas du code |
| 3 | **Interface `inspect_kernel.ps1` : défaut strict, `-Lenient` opt-out** (`[CORRIGÉ 18/10/2026]` — l'intitulé « `-Strict` non par défaut » était faux) | **choix assumé** | le **défaut** est **2** sur couverture incomplète ; `-Lenient` rétablit 0. Il n'existe aucune option `-Strict` (la fournir en argument → exit 1). Le défaut strict est voulu : un kernel non annoté ne doit pas sortir 0. Les deux modes sont testés |
| 4 | **Application du contrat par le LLM** (`AGENTS.md`) | `UNKNOWN` (par nature) | un test peut prouver la **présence** et le **contenu** du fichier (c'est fait), jamais qu'un modèle l'a **lu et appliqué**. Aucune assertion ne doit prétendre le contraire |

### 11.1 Trois limites de méthode, également assumées

- **D5 ≠ « build validé »** : la cause du blocage est désormais exacte (méthode
  de diagnostic, pas dépendances), et le smoke build passe ; cela ne valide pas
  les kernels du projet.
- **`inspect_kernel.ps1` sort 2 par défaut** : tout appelant existant qui
  attendait 0 doit passer `-Lenient`. Changement volontaire, annoncé au §8.3.
- **D6** : le validateur suit le schéma du générateur ; le test bidirectionnel
  **détecte** la dérive, il ne la corrige pas automatiquement.

## 12. Registre des statuts (TESTED / NOT TESTED / UNKNOWN / INFERRED)

Ajouté le 18/10/2026 après requalification de la preuve (§10.6). Chaque ligne
porte un statut unique et la preuve ou le blocage correspondant. Aucun `PASS`
matériel n'est revendiqué.

| Affirmation | Statut | Preuve / blocage |
|---|---|---|
| Chaîne de compilation AIE produit un XCLBIN sur Windows | **TESTED** (compilation seule) | `tools/aiecc_smoke_evidence.py` → `evidence/aiecc_smoke/runs/20261018T072027Z/` : exit 0, `stderr.txt` 30 étapes, `out.xclbin` 6818 o magic `xclbin2` sha256 `6e83a976…7051`, `xclbin_info.txt` exit 0, env `aiecc` `af819a802f4` |
| Manifeste manuel du dossier `aiecc_smoke/` (6818 o, sha256 `d823a6b9…`, exit 0) | **INFERRED** | rédigé à la main, artefact et sorties non conservés → non revérifiable ; origine documentée dans `ORIGINE_MANIFESTE.md`, fichier conservé |
| Compilation des kernels réels (Qwen3.6, Phi-3, Nanbeige, Granite) | **NOT TESTED** | aucun build lancé ; durée/artefacts non produits |
| Exécution d'un kernel sur le NPU XDNA2 | **NOT TESTED** | aucune soumission, aucun `xrt-smi` exploité dans cette passe |
| Latence / débit (t/s, µs) | **UNKNOWN** | aucune mesure ; un build réussi ne mesure rien |
| Validation A/B réelle (`new_validation_report.ps1`) | **UNKNOWN** / `INACCESSIBLE` | ni `llama-server` ni paire d'XCLBIN ; le script écrit un gabarit puis sort 3 |
| Environnement WSL (XRT, Peano, `env_install.sh`) | **NOT TESTED** | installation système non autorisée ; préflight `--platform wsl` sort 3 avec 5 manquants |
| Comportement par défaut de `inspect_kernel.ps1` (exit 2 si couverture incomplète) | **TESTED** | `test_d2_couverture_incomplete_sort_2_par_defaut` + `test_d2_interface_lenient_sans_pseudo_strict` ; exécutions directes : défaut **2**, `-Lenient` **0** |
| Existence d'une option `-Strict` | **REFUTED** | 0 occurrence dans `inspect_kernel.ps1` (lignes 15 et 158 = `-Lenient`) ; `-Strict` → **exit 1**. Ancienne affirmation corrigée en §12.1 |
| Application d'`AGENTS.md` par le LLM | **UNKNOWN** (par nature) | un test prouve la présence/contenu, jamais la lecture par le modèle |
| Suite `pytest tests -q` du dépôt | **TESTED** | 51 → 52 → 54 → **55 passed, exit 0** (chaque exécution est datée ci-dessus) |
| Option `-Strict` de `inspect_kernel.ps1` | **REFUTED** | absente du script ; l'invoquer sort **1**. Voir §12.1 |

### 12.1 `[CORRIGÉ 18/10/2026]` L'option `-Strict` n'existe pas (affirmation réfutée)

Le présent rapport (§2 ligne D2, §4, §8.3, §11 ligne 3) affirmait une option
`-Strict` produisant un exit 2. **C'est faux**, et la phrase d'origine est
conservée ci-dessus, annotée.

| Contrôle | Commande | Résultat |
|---|---|---|
| Occurrences de `Strict` dans le script | `grep -c Strict inspect_kernel.ps1` | **0** |
| Interface réelle | `inspect_kernel.ps1:15` | `[switch]$Lenient` (opt-out explicite) |
| Défaut | `inspect_kernel.ps1:158` | `if (-not $Lenient) { exit 2 }` |
| Défaut sur kernel non annoté | `inspect_kernel.ps1 -KernelPath sans_marqueur.s` | **exit 2** |
| `-Lenient` sur le même kernel | `… -Lenient` | **exit 0** |
| `-Strict` (inexistant) | `… -Strict` | **exit 1** (paramètre inconnu) — aucun verdict produit |
| Non-régression | `test_d2_interface_lenient_sans_pseudo_strict` | **passé** (fge l'interface : `[switch]$Lenient` présent, `Strict` absent, `-Strict` → 1) |

Conséquence sur le §11 : le point 3 n'est plus « `-Strict` non par défaut » mais
« **défaut strict assumé, `-Lenient` pour l'usage diagnostique** ». La limite
reste la même côté appelants : tout appelant qui attendait 0 doit passer
`-Lenient`.

### 12.2 Séparation outillage / rapports

- **Outils et tests** modifiés ou ajoutés : `tools/aiecc_smoke_evidence.py`,
  `tests/test_skills_fixes.py` (2 tests de preuve + garde-fou d'altération).
- **Rapports** : aucune ligne supprimée ; les affirmations rectifiées sont
  annotées `[CORRIGÉ 18/10/2026]` et l'ancienne version reste lisible.
- **Aucun commit, aucun push** ; l'état git reste dans le working tree.
