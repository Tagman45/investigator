# Repository inventory — OpenFlowLM-Next (test fonctionnel du skill `git-ecosystem-investigator`)

Date de collecte : 2026-10-17 (dossier horodaté `git-eco-openflowlm-20261017-1655`, ne remplace aucun dossier précédent).

| Objet | Valeur | Preuve |
|---|---|---|
| Repo local | `E:\trixdna_test\repos_openflowlm_next` | `inspect_repository.py` pass 1 (`repository-inspect.json`) |
| Origin | `https://github.com/Atomic-Germ/OpenFlowLM-Next.git` (fetch/push) | `git remote -v` → preuve `URL-NEXT-001` |
| Fork parent | `Atomic-Germ/OpenFlowLM` (l'équipe OpenFlowLM est passée chez AMD d'après docs/index.md) | extrait docs/index.md:21 → `URL-004` |
| Grands-parents déclarés | `ROCm/FastFlowLM` (README : « A community fork of FastFlowLM ») | README.md → `URL-004b` |
| HEAD local | `7af242eb2c9bf98a57cc998b96913e8c425b8e49` (« fix(open_qwen36): pools_test scopes the Q4nxFile handle before unlink ») | `inspect_repository.json → head` |
| Branche locale | `fix/pools-test-scope` | `git status` du 17/10 (session) |

## Pass 1 — dépôt entier (borné `--max-files 3000`)

- 3000 fichiers parcourus (limite atteinte — le dépôt embarque des milliers d'artefacts de build kernels `open_kernels/**` : `.prj`, `.lock`, `build_*`).
- 24 manifests détectés (`.gitmodules`, `CMakeLists.txt` racine, `Dockerfile`, `flake.lock`, locks nix, locks Cargo des sous-arbres).
- 46 fichiers avec imports/include détectés — la limite `max_files` est tombée avant d'atteindre `src/` : **pas un inventaire exhaustif** (couverture déclarée dans `coverage-report.md`).

## Pass 2 — sous-arbre `src/` (borné `--max-files 2000`)

- 1221 fichiers, 366 avec imports/includes.
- Moteur open : **24 fichiers `src/open_qwen36/*`** (`core.cpp`, `cli.cpp`, `engine.cpp`, `pools.cpp`, `block_host*`, vision `vit.cpp`, …), CMakeLists propres à ce sous-dossier.
- Preuve : `repository-inspect-src.json` → `INSPECT-SRC-001`.

## Sous-modules / historique borné

- `git submodule status` exécuté par le script ( збереж dans `repository-inspect.json`, champs `submodules`, `recent_log` 20 derniers commits iso-strict).

## Seuils et limites de collecte

- Lecture seule, répertoires ignorés par le script : `.git`, `.venv`, `node_modules`, `__pycache__`, `dist`, `build`.
- Aucun accès réseau utilisé pour cet inventaire.
