# Audit des 17 skills — limites déclarées vs limites mesurées

Date : 2026-10-18 · Mission : `skills-contract-20261018`
Objet : clore les trois limites restantes de l'inventaire du 18/10 —
(1) lecture intégrale des 17 `SKILL.md`, (2) test réel des chemins relatifs de
`npu-offload-pipeline`, (3) smoke tests des skills métier.

Règle de statut appliquée (`evidence`) : `FACT` = vérifié dans cette session
(commande + code de sortie), `SOURCE_CONFIRMED` = écrit dans le fichier,
`HYPOTHESIS` = plausible non testé, `UNKNOWN` = aucune preuve.

---

## 1. Lecture intégrale — ce que ça change

**FACT** : `wc -l */SKILL.md` → **1 558 lignes** sur 17 fichiers, tous lus en
entier (pas seulement le frontmatter).

Correction de l'affirmation du 18/10 (« 15 skills sans section Limites, limites
déduites ») :

| Constat | Preuve |
|---|---|
| 17/17 skills contiennent au moins **une contrainte écrite** (interdits, « ne jamais », prérequis) | lecture intégrale ; ex. `xdna2-path-explorer` §4 « Sécurité et robustesse », `search-policy` §Garde-fous, `open-qwen36-kernels` §Rules |
| **2/17** seulement ont une section **titrée** « Limites » | `git-ecosystem-investigator` §« Sécurité et limites » ; `xdna2-evidence-oracle` §5 « Limites » |
| Donc « limites déduites » ne veut pas dire « limites absentes du fichier » : ce sont les **prérequis implicites** (emplacement, OS, device, réseau) qui étaient déduits | tableau §4 |

Contraintes nouvellement visibles grâce à la lecture complète, qui n'étaient
pas dans l'inventaire précédent :

- `evidence` écrit que `evidence.py` « peut ne pas exister encore → le
  documenter comme à venir ». **FACT** : `python E:/trixdna_test/evidence.py
  --help` → **exit 0**. L'avertissement est périmé (voir D4).
- `aie2p-hand-asm-debug` déclare un protocole A/B obligatoire, dont dépend
  `scripts/validate_kernel.ps1` — testé, voir D3.
- `npu-offload-pipeline` ne dit nulle part **où** il doit être installé pour
  que ses 5 références résolvent — testé, voir D1.
- `xdna2-path-explorer` liste `COST_MODEL.json` dans ses sorties, mais le
  dossier ne contient que `CostModelTemplate.json` (D6).
- `open-granite-kernels` exige `C:\Xilinx\XRT` (Windows), à l'inverse de
  `open-qwen36-kernels`/`open-phi3-nanbeige-kernels` (WSL) — les deux familles
  ne sont pas exécutables dans le même environnement.

---

## 2. D1 — `npu-offload-pipeline` : 0/5 références résolues à l'installation

**FACT** (`evidence/npu_refs_resolution.json`) :

| Base de résolution | Références résolues |
|---|---|
| `C:\Users\videl\.config\opencode\skills\npu-offload-pipeline` (installation réelle) | **0 / 5** |
| `E:\trixdna_test\repos_openflowlm_next\.agents\skills\npu-offload-pipeline` (emplacement d'origine dans le dépôt) | **5 / 5** |

Références testées : `../npu_offload_pipeline.md`,
`../../../docs/precompiled_replacement_map.md`,
`../../../docs/precompiled_artifacts.json`,
`../../../utilities/binary-inventory/inventory.py`, `../../../REPLACEMENT_PLAN.md`.

Le `SKILL.md` installé et celui du dépôt sont **identiques** (`diff` ne montre
que des fins de ligne CRLF vs LF, exit 1 attendu pour cette seule raison).

**Défaut** : le skill est un routeur vers 5 documents du dépôt OpenFlowLM-Next,
mais sa résolution est **relative à son propre dossier**. Installé sous
`.config/opencode/skills/`, les 5 chemins pointent vers `.config/docs/…` et
n'existent pas. Aucune ligne du `SKILL.md` ne dit « installer sous
`<repo>/.agents/skills/` ». Un agent qui suit le skill à la lettre lit donc
zéro référence et peut improviser.

**Correctif minimal proposé** (non appliqué — modification de skill non
demandée) : remplacer la base relative par une note explicite
« base = racine du dépôt OpenFlowLM-Next » + une vérification
`test -f` au début, ou fournir une variable `OFLM_REPO` avec erreur nommée
si absente — cohérent avec la règle du skill lui-même (« return an explicit
`not implemented` error rather than silently depending on… »).

`utilities/binary-inventory/inventory.py --help` → **exit 0** : l'outil visé
fonctionne quand on l'appelle par son chemin réel.

---

## 3. Smoke tests des scripts métier — résultats réels

Toutes les commandes ci-dessous ont été exécutées ; `exit` = code de sortie
réel (pas de pipeline masquant).

| Skill | Test | Résultat |
|---|---|---|
| `evidence` | `evidence.py --help` | **exit 0** |
| `search-policy` | `search.py --help`, `rgx.py --help` | **exit 0**, **exit 0** |
| `debug-method` | `investigate.py --help`, `graft_investigate.py --help`, `bus.py --help` | **exit 0** ×3 |
| `debug-method` | `autodesign.py --help` | **exit 1** — pas d'argparse : affiche l'usage et sort 1 ; la commande documentée (`benchmark run --cmd … --expect …`) existe bien dans l'usage |
| `oracle-query` | `rag_service.py --help`, `graft` (PATH) | **exit 0** ; `graft` présent |
| `oracle-query` | `cve_lookup.py --help`, `bug_tracker.py --help`, `pre_flight.py --help`, `d2_live_oracle.py --help` (cwd `Desktop/oneplus`) | **exit 0** ×4 |
| `xdna2-evidence-oracle` | 4 scripts présents (`oracle.py`, `check_urls.py`, `generate_evidence.py`, `research.py`) | présents ; `SKILL.md` n'en documente qu'un (écart doc/code mineur) |
| `op15-apk-debug` | `apk-debug.ps1 device` | **exit 0**, sortie `List of devices attached` **vide** → 0 device : les verbes phone (`launch`, `dump`, `root`…) ne sont pas testables ici ; le script, lui, répond |
| `aie2p-hand-asm-debug` | `inspect_kernel.ps1 -KernelPath test_avec_marqueur.s` | **exit 0**, détecte `Bundle 7 instructions` / `Bundle max : 7` (au-dessus de la limite 6) |
| `aie2p-hand-asm-debug` | `inspect_kernel.ps1 -KernelPath test_sans_marqueur.s` | **exit 0**, mais **`Bundle max : 0`** sans aucun avertissement (D2) |
| `aie2p-hand-asm-debug` | `inspect_kernel.ps1 -KernelPath absent.s` | **exit 1** + message « Fichier kernel introuvable » — échec propre |
| `aie2p-hand-asm-debug` | `validate_kernel.ps1` avec xclbins factices | **exit 1** (Resolve-Path), aucun fichier produit — échec propre |
| `1bit-writer` | références projet (`site/benchmarks.json`, `docs/journey.md`, `AGENTS.md`, `docs/guides/launch.md`, `prompts/1bit.md`, `models/catalog/README.md`, `site/index.html`, `CHANGELOG.md`) + `references/content-guide.md`, `blog-template.html`, `key-facts.md` | **11/11 présentes** (`Documents/1bit-systems-main` + dossier du skill) |
| `nitro-writer` | `CARTE_CONNAISSANCES.md`, `CARTE_CHEMINS.md`, `RAPPORT_AUDIT_ANGLES_MORTS.md`, `AGENTS.md` | **4/4 présentes** (`Documents/nitro`) |
| `npu-offload-pipeline` | `inventory.py --help` (chemin réel du dépôt) | **exit 0** |
| `open-qwen36-kernels` | `export_qwen36_kernels.py --help` | **exit 0** (le script s'importe sur Windows) |
| `open-*-kernels` | prérequis d'environnement | voir §5 |

Fichiers de test conservés : `evidence/aie2p_smoke/test_sans_marqueur.s`,
`evidence/aie2p_smoke/test_avec_marqueur.s`.

---

## 4. Défauts découverts (au-delà des 3 limites initiales)

| ID | Défaut | Preuve | Gravité |
|---|---|---|---|
| **D1** | `npu-offload-pipeline` : 0/5 références résolues hors de `<repo>/.agents/skills/`, dépendance d'emplacement non écrite | §2 | **P1** — l'agent lit zéro référence sans le savoir |
| **D2** | `inspect_kernel.ps1` : la détection de bundles ne démarre que sur un marqueur `## @`. Sans ce marqueur, `Bundle max : 0` est affiché **sans avertissement** ; un kernel à 7 instructions paraît sain | `evidence/aie2p_smoke/*.s` + sorties ci-dessus | **P1** — faux négatif silencieux sur la règle « max 6/bundle » |
| **D3** | `validate_kernel.ps1` est un **générateur de rapport à trous**, pas un lanceur A/B : il écrit un markdown avec `[Paste la sortie qdump …]` et n'appelle ni `llama-server` ni qdump | grep du script (`llama-server` uniquement dans le commentaire d'en-tête, lignes 5 et 112-114) | **P2** — le `SKILL.md` dit « Lancer la validation A/B » ; l'automatisation n'existe pas |
| **D4** | `evidence` : « `evidence.py` peut ne pas exister encore » est faux aujourd'hui | `--help` exit 0 | P3 — correction documentaire (preuve + date) |
| **D5** | Prérequis WSL des skills noyaux absents sur cette machine : `~/ironenv142`, `~/xrt-tools/bin` inexistants, `import mlir_aie` échoue dans WSL Ubuntu | `wsl -e bash -lc …` exit ≠ 0 + traceback | **P1** pour l'exécution — les skills Qwen3.6/Phi3/Nanbeige ne sont pas exécutables ici |
| **D6** | `xdna2-path-explorer` : `COST_MODEL.json` listé en sortie, absent du dossier ; seul `CostModelTemplate.json` existe | `ls` 9/10 présents | P3 |
| **D7** | `inspect_kernel.ps1` compte les MAC **par ligne**, pas par instruction : une ligne portant 2 `vmac` est comptée 1 (`test_sans_marqueur.s` : `Nombre de MAC : 1`), contre 4 sur le même code réparti sur plusieurs lignes | sorties ci-dessus | P3 — diagnostic sous-estimé |
| **D8** | `xdna2-evidence-oracle` : 4 scripts livrés, 1 seul documenté (`oracle.py`) | `ls scripts/` | P3 |

Non-défauts vérifiés (pour éviter les fausses alertes) :

- `C:\Xilinx\XRT` **n'a pas** de sous-dossier `bin/` : `xclbinutil.exe` et
  `aiebu-asm.exe` sont **à la racine** de `C:\Xilinx\XRT`. Le `SKILL.md` de
  `open-granite-kernels` dit « from `C:\Xilinx\XRT`, both on PATH after
  `iron_env.ps1` » — donc compatible ; ma première vérification `bin/` était
  une mauvaise hypothèse, corrigée ici.
- `autodesign.py --help` exit 1 : comportement d'usage, pas une panne — la
  sous-commande documentée fonctionne.

---

## 5. Limites déclarées vs mesurées, par skill

Colonnes : **D** = limite écrite dans le fichier (section ou interdit) ·
**M** = testée dans cette session.

| Skill | D | M | Limite mesurée principale |
|---|---|---|---|
| `git-ecosystem-investigator` | ✓ §Sécurité et limites | non (inchangé) | 135 tests M6 sur 3 copies — non re-exécutés, fichiers inchangés |
| `xdna2-evidence-oracle` | ✓ §5 | partiel | scripts présents ; vérif HTTP non lancée |
| `xdna2-path-explorer` | ✓ §4 | partiel | 9/10 templates ; `COST_MODEL.json` absent (D6) ; aucun script à tester |
| `xdna2-cross-audit` | ✓ §Interdits | non | doc-only, aucune commande |
| `evidence` | ✓ §Règles | ✓ | `evidence.py` existe (D4) |
| `debug-method` | ✓ §Garde-fous | ✓ | 4 outils OK ; `autodesign --help` = usage |
| `search-policy` | ✓ §Garde-fous | ✓ | `search.py`, `rgx.py` OK |
| `token-scout` | partiel (contrat de retour) | **non testable** | exige l'outil `Agent`/`device_bash`, absent de cet environnement |
| `oracle-query` | ✓ §Anti-gaspi | ✓ | 5 outils OK ; `nitro_metrics` (device) non testé |
| `npu-offload-pipeline` | ✗ (règles, pas de limites) | ✓ | **D1** 0/5 refs |
| `open-qwen36-kernels` | ✓ §Rules | partiel | script OK ; **build impossible** (D5) |
| `open-granite-kernels` | ✓ §Rules | partiel | XRT Windows présent (layout plat) ; build non lancé |
| `open-phi3-nanbeige-kernels` | ✓ §Traps | partiel | **build impossible** (D5) |
| `aie2p-hand-asm-debug` | ✓ §Discipline | ✓ | **D2**, **D3**, **D7** |
| `1bit-writer` | ✓ §Sécurité & validation | ✓ (réfs) | 11/11 références présentes ; aucune génération rédigée |
| `nitro-writer` | ✓ §Sécurité & validation | ✓ (réfs) | 4/4 références présentes ; aucune génération rédigée |
| `op15-apk-debug` | ✓ §Anti-patterns | ✓ (script) | **0 device** → verbes phone non testables |

**Bilan (compté sur le tableau ci-dessus, pas estimé)** : 17/17 ont des
contraintes écrites ; 2/17 ont une section titrée « Limites » ; **14/17 ont au
moins un élément testé dans cette session** (dont 5 partiellement : oracle,
path-explorer, les deux familles WSL/Granite). **3/17 n'ont aucun test cette
session** : `git-ecosystem-investigator` (135 tests M6 non re-exécutés,
fichiers inchangés), `xdna2-cross-audit` (aucun exécutable — doc-only),
`token-scout` (outil `Agent` absent). « Partiel » n'est pas « validé » : les
builds xclbin, l'APK sur device et les expériences NPU restent `UNKNOWN`/
`INACCESSIBLE`.

---

## 6. Non testé — et pourquoi (pas de verdict déguisé)

| Non testé | Raison | Statut |
|---|---|---|
| Builds xclbin Qwen3.6 / Phi3 / Nanbeige | `~/ironenv142`, `~/xrt-tools/bin` absents, `mlir_aie` non importable en WSL (D5) | `UNKNOWN` |
| Build Granite Windows | `iron_env.ps1` + mlir-aie Windows non vérifiés ; build long (>4 min) non lancé | `UNKNOWN` |
| Inférence NPU (Granite/Qwen) | aucune exécution NPU dans cette mission | `OUT_OF_SCOPE` |
| Génération rédactionnelle (`1bit-writer`, `nitro-writer`) | skills de style, pas d'assertion automatique ; refs vérifiées seulement | `NOT_TESTED` |
| APK build/install/launch (`op15-apk-debug`) | 0 device attaché ; Gradle non lancé | `INACCESSIBLE` |
| `token-scout` | pas d'outil sous-agent dans cet environnement | `NOT_EXECUTABLE` |
| `xdna2-path-explorer` expériences | aucune expérience matérielle demandée ; écritures de résultats non déclenchées | `OUT_OF_SCOPE` |
| Tests `git-ecosystem-investigator` | fichiers inchangés depuis M6 (135 passed, exit 0) | non re-exécutés volontairement |

---

## 7. Livrables et provenance

| Fichier | Contenu |
|---|---|
| `RAPPORT_AUDIT_17_SKILLS.md` | ce rapport |
| `LIMITES_CONTRAT.md` | contrat commun proposé + application aux 17 skills (P1 de la note du 18/10) |
| `evidence/npu_refs_resolution.json` | résolution machine des 5 références, 2 bases |
| `evidence/aie2p_smoke/test_sans_marqueur.s` | kernel synthétique, bundle 7 sans marqueur (D2) |
| `evidence/aie2p_smoke/test_avec_marqueur.s` | même code avec `## @`, contrôle positif |
| `CHECK_LOG.md` | commandes + codes de sortie bruts |

Aucun des 17 `SKILL.md` n'a été modifié par cette mission : les correctifs
D1–D8 sont **documentés avec preuve**, pas appliqués.

## 8. Verdict

**ACCEPT** pour l'audit : les 3 limites annoncées sont levées —
17/17 `SKILL.md` lus intégralement, chemins de `npu-offload-pipeline` testés
sur deux bases (0/5 vs 5/5), scripts métier exécutés avec codes de sortie
réels. **8 défauts** documentés, dont 3 P1 (D1, D2, D5). **14/17 skills** ont
au moins un élément testé (5 partiellement) ; **3/17** n'ont aucun test cette
session et sont marqués comme tels, pas comme validés. Builds xclbin, APK sur
device et expériences NPU restent hors de portée ici.
