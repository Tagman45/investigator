# CHECK_LOG — commandes et codes de sortie bruts (18/10/2026)

Toutes les commandes ont été lancées dans bash (Git Bash Windows). `exit` est
le code du processus testé ; quand une sortie était filtrée, `PIPESTATUS[0]`
a été utilisé pour conserver le code de la commande testée.

## Lecture intégrale

```
cd C:/Users/videl/.config/opencode/skills && wc -l */SKILL.md
→ 17 fichiers, 1 558 lignes (total)
for d in */; do [ -f "${d}SKILL.md" ] && echo HAS; done | wc -l
→ 17
for d in */; do [ -f "${d}SKILL.md" ] || echo NO; done
→ (aucune sortie) : aucun dossier sans SKILL.md
```

## D1 — npu-offload-pipeline

```
cd C:/Users/videl/.config/opencode/skills/npu-offload-pipeline
python -c "résolution des 5 refs"
→ MANQUANT ×5 (C:\Users\videl\.config\docs\…, .config\REPLACEMENT_PLAN.md, …)

cd E:/trixdna_test/repos_openflowlm_next/.agents/skills/npu-offload-pipeline
→ OK ×5

diff <repo>/.agents/skills/npu-offload-pipeline/SKILL.md <installé>/SKILL.md
→ exit 1 : seules différences = fins de ligne CRLF vs LF (contenu identique)
```

## D5 — environnements

```
ls C:/Xilinx/XRT/bin/xclbinutil.exe C:/Xilinx/XRT/bin/aiebu-asm.exe
→ No such file (les binaires sont à C:/Xilinx/XRT/xclbinutil.exe et aiebu-asm.exe)
ls C:/Xilinx/XRT
→ aiebu-asm.exe aiebu-dump.exe include lib license nputrace_tool python share xclbinutil.exe …

wsl.exe -l -q                    → Ubuntu (exit 0)
wsl.exe -e bash -lc 'ls -d ~/ironenv142 ~/xrt-tools/bin; which xclbinutil aiebu-asm; python3 -c "import mlir_aie"'
→ aucune sortie pour les deux dossiers, aucun binaire, traceback ImportError
```

## Smoke tests Python (exit codes)

```
E:/trixdna_test/evidence.py --help            → 0
E:/trixdna_test/search.py --help              → 0
E:/trixdna_test/rgx.py --help                 → 0
E:/trixdna_test/investigate.py --help         → 0
E:/trixdna_test/autodesign.py --help          → 1   (affiche l'usage, pas d'argparse)
E:/trixdna_test/autodesign.py                 → 0   (usage affiché)
E:/trixdna_test/rag_service.py --help         → 0
E:/trixdna_test/graft_investigate.py --help   → 0
E:/trixdna_test/bus.py --help                 → 0

Desktop/oneplus/xdna2-forensics:
  cve_lookup.py --help                        → 0
  bug_tracker.py --help                       → 0
  pre_flight.py --help                        → 0
Desktop/oneplus:
  reverse_npu/scripts/d2_live_oracle.py --help → 0

repos_openflowlm_next:
  open_kernels/export_qwen36_kernels.py --help → 0
  utilities/binary-inventory/inventory.py --help → 0

command -v graft                              → présent (PATH)
```

## PowerShell — aie2p-hand-asm-debug (D2, D3, D7)

```
inspect_kernel.ps1 -KernelPath test_avec_marqueur.s
→ exit 0
  Bundle ~L2-L8 : 7 instructions
  Bundle ~L10-L11 : 2 instructions
  Nombre de MAC : 4
  Bundle max : 7 instructions

inspect_kernel.ps1 -KernelPath test_sans_marqueur.s
→ exit 0
  (section « Limites de bundles » vide)
  Nombre de MAC : 1          ← 2 vmac sur une seule ligne comptés 1
  Bundle max : 0 instructions ← aucune alerte

inspect_kernel.ps1 -KernelPath absent.s
→ exit 1  « Fichier kernel introuvable »

validate_kernel.ps1 -BaselineXclbin C:/nope/base.xclbin -FixXclbin C:/nope/fix.xclbin -ModelPath C:/nope/m.gguf
→ exit 1 (Resolve-Path), aucun fichier produit
grep -nE "llama-server|qdump" validate_kernel.ps1
→ llama-server uniquement lignes 5 (commentaire) ; qdump dans le gabarit texte (112/114)
```

## op15-apk-debug (D8/limite device)

```
powershell -NoProfile -ExecutionPolicy Bypass -File apk-debug.ps1 device
→ exit 0
  List of devices attached
  (aucun device listé)
```

## Références documentaires des writers

```
Documents/1bit-systems-main : site/benchmarks.json, docs/journey.md, AGENTS.md,
  docs/guides/launch.md, prompts/1bit.md, models/catalog/README.md,
  site/index.html, CHANGELOG.md → 8/8 OK
skills/1bit-writer/references : content-guide.md, blog-template.html, key-facts.md → 3/3 OK

Documents/nitro : CARTE_CONNAISSANCES.md, CARTE_CHEMINS.md,
  RAPPORT_AUDIT_ANGLES_MORTS.md, AGENTS.md → 4/4 OK
```

## Templates xdna2-path-explorer

```
MCDM_MAP.md EXP_PLANNER.md DMA_PROTO.md SRAM_MAP.md FORMAT_MATRIX.md
GPU_NPU_INTEROP.md MOE_EXPERT_PLACEMENT.md GraphCandidatesTemplate.json
EvidenceLedgerTemplate.jsonl → 9/9 OK
COST_MODEL.json → MANQUANT (D6)
```
