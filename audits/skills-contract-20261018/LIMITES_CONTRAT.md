# Contrat de limites commun aux 17 skills (proposition, 18/10/2026)

But : un format **identique et vérifiable** pour les 17 skills, sans fusionner
leurs fonctions (les frontières restent celles de `specialization-matrix.md`).

## Format (7 champs obligatoires)

| Champ | Valeur attendue |
|---|---|
| Périmètre | ce que le skill prend en charge |
| Exclusions | ce qu'il ne fait pas, et à qui c'est délégué |
| Prérequis | chemins, binaires, OS, device, réseau, variables |
| Modes d'échec connus | comment il échoue **et** comment il le signale |
| Limites **D** / **d** | D = écrite dans le fichier ; d = déduite (prérequis implicite) |
| Tests exécutés | date + commande + code de sortie, ou `NOT_TESTED` |
| Provenance | date de dernière validation + preuve |

Règle : une limite jamais testée s'écrit `NOT_TESTED`, jamais « OK ».
Règle : un échec silencieux (sortie 0 sans avertissement) est un défaut P1.

## Application — état au 2026-10-18

| Skill | Prérequis | Modes d'échec | D / d | Tests 18/10 |
|---|---|---|---|---|
| `git-ecosystem-investigator` | réseau ; `GITHUB_TOKEN` optionnel ; `pypdf` optionnel | codes fermés `ACCESS_DENIED`/`RATE_LIMITED`/`HTTP_404`/`EMPTY_CONTENT`/`PDF_*` ; `--no-network` → `UNVERIFIED` | D ✓ / d : pagination, PDF partiel ; skip réseau possible avec exit 0 (C1) | **135 passed, 0 skipped, exit 0 ×3 copies** (18/10) ; conftest audité |
| `xdna2-evidence-oracle` | rapports locaux ; réseau pour `check-urls` | 403/429/timeout → statut HTTP, jamais « vrai/faux » | D ✓ §5 / d : 4 scripts, 1 documenté | scripts présents ; vérif HTTP `NOT_TESTED` |
| `xdna2-path-explorer` | `E:\trixdna_test` ; templates | pas de script → aucune erreur runtime possible | D ✓ §4 / d : `COST_MODEL.json` absent | 9/10 templates ; expériences `OUT_OF_SCOPE` |
| `xdna2-cross-audit` | oracle + path-explorer + RAG | doc-only : aucune erreur exécutable | D ✓ §Interdits / d : dépend de 3 skills | `NOT_TESTED` (doc) |
| `evidence` | `E:\trixdna_test\bus.py`, `evidence.py` | non conforme si assertion sans preuve | D ✓ §Règles / d : note « evidence.py peut ne pas exister » **périmée** | `evidence.py --help` → 0 (D4) |
| `debug-method` | `investigate.py`, `autodesign.py`, `bus.py` | `autodesign --help` → exit 1 (usage) | D ✓ §Garde-fous / d : pas de reproduction ⇒ `UNKNOWN` | 4 outils → exit 0 ; `autodesign` usage OK |
| `search-policy` | `search.py`, `rgx.py`, sémaphore `opencode_rg_limiter` | rg direct interdit ; pas de scan racine E: | D ✓ §Garde-fous / d : dépend du cache/Graft | `search.py`, `rgx.py` → exit 0 |
| `token-scout` | outil `Agent` (ou `device_bash`) | sans outil sous-agent : rien ne se délègue | partiel / d : perte de nuance au résumé | `NOT_EXECUTABLE` ici |
| `oracle-query` | `graft`, `rag_service.py`, scripts `oneplus/xdna2-forensics` | 1 seule source ; device absent ⇒ métriques indisponibles | D ✓ §Anti-gaspi / d : 5 outils distincts | 5 scripts → exit 0 ; `nitro_metrics` `NOT_TESTED` |
| `npu-offload-pipeline` | **base = racine du dépôt OpenFlowLM-Next** (non écrit) | 0/5 références résolues hors de `<repo>/.agents/skills/` | d seul / **défaut D1** | 0/5 installé, 5/5 dans le dépôt |
| `open-qwen36-kernels` | WSL, `~/ironenv142`, `~/xrt-tools/bin`, `xclbinutil` | import/`export` échoue si env absent | D ✓ §Rules / d : D5 | script `--help` → 0 ; **build `UNKNOWN`** |
| `open-granite-kernels` | Windows, `C:\Xilinx\XRT` (binaires à la racine), `iron_env.ps1`, VS Community 18 | refuse un conteneur non replié (2 refus nommés) | D ✓ §Rules / d : `VCVARS64` obligatoire | XRT présent ; build `NOT_TESTED` |
| `open-phi3-nanbeige-kernels` | WSL, `LD_LIBRARY_PATH=~/xrt-tools/lib` | segfault `oflm serve` si `dynamic_cast` vers l'engine closed | D ✓ §Traps / d : D5 | **build `UNKNOWN`** |
| `aie2p-hand-asm-debug` | MCP `graft`/`rag` ; `.s` annotés `## @` | `Bundle max : 0` **silencieux** sans marqueur (D2) ; `validate_kernel` = gabarit (D3) ; MAC comptés par ligne (D7) | D ✓ §Discipline / d : format d'annotation | 3 scripts testés, exit 0/1 attendus |
| `1bit-writer` | `Documents/1bit-systems-main` + `references/` du skill | chiffre hors `benchmarks.json` = non conforme | D ✓ §Sécurité & validation / d : projet hors `Desktop` | 11/11 réfs ; rédaction `NOT_TESTED` |
| `nitro-writer` | `Documents/nitro` (`CARTE_CONNAISSANCES.md`) | chiffre sans statut = non conforme | D ✓ §Sécurité & validation / d : projet hors `Desktop` | 4/4 réfs ; rédaction `NOT_TESTED` |
| `op15-apk-debug` | adb + device `3B15BK0067A00000` ; Gradle 8.11.1 ; serveur `--pure` | 0 device ⇒ verbes phone inopérants (script sort 0) | D ✓ §Anti-patterns / d : device unique | `device` → exit 0, **0 device** |

## Trois règles à ajouter aux 17 `SKILL.md` (non appliquées ici)

1. **Base de résolution explicite** : tout chemin relatif déclare sa base
   (« relatif à la racine du dépôt X ») et échoue avec un code nommé si absent
   — corrige D1.
2. **Échec silencieux interdit** : un outil qui ne peut pas mesurer (bundle,
   MAC, device) doit le dire ; `0` n'est pas un résultat — corrige D2, D7.
3. **Un script n'est pas son nom** : `validate_kernel.ps1` annonce une
   validation A/B et produit un gabarit ; le `SKILL.md` doit décrire l'action
   réelle — corrige D3.

## Ce que ce contrat ne fait pas

Il ne prouve pas qu'un skill **fonctionne** : il rend seulement son état
d'exécution lisible (testé / non testé / non testable). Les builds WSL (D5),
l'APK (0 device) et les expériences NPU restent hors de portée de cette
machine au 2026-10-18.
