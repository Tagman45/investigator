# Origine du `manifest.json` présent à ce niveau

**Statut : `INFERRED` / non-machine.** Ce `manifest.json` a été **rédigé à la
main** par l'assistant le 18/10/2026, après un build smoke exécuté dans un
dossier temporaire (`C:/Users/videl/AppData/Local/Temp/aiecc_smoke/o2`).

Il **n'est pas** une preuve machine : l'`out.xclbin` n'a pas été conservé et la
sortie du build (`stdout`/`stderr`) n'a pas été enregistrée. Les valeurs qui y
figurent (exit 0, 6818 octets, magic `xclbin2`, sha256 `d823a6b9…`) ont été
reportées à la main et ne peuvent donc pas être revérifiées.

## Preuve qui fait foi

`runs/<UTC>/` — produit par `tools/aiecc_smoke_evidence.py`, qui conserve :

| Élément | Fichier |
|---|---|
| Commande exacte (argv complet + cwd) | `command.txt` |
| Code de sortie, durée | `manifest.json` (`exit`, `duration_s`) |
| Sortie utile complète | `stdout.txt`, `stderr.txt` (30 étapes de pipeline) |
| Environnement | `env.txt` (`aiecc --version`, compte de git, python, OS) |
| Artefact | `out.xclbin` conservé + `size`, `sha256`, `magic` |
| Vérification croisée | `xclbin_info.txt` (`xclbinutil --info`, exit 0) |
| Portée | `manifest.json` → `scope: COMPILATION_ONLY_NO_NPU`, `status: TESTED` |

Revalidation sans rebuild :

```
python tools/aiecc_smoke_evidence.py --check-only audits/skills-fix-20261018/evidence/aiecc_smoke/runs/<UTC>
```

## Limites conservées

- **Compilation uniquement** : aucune exécution NPU, aucune latence, aucun débit.
- Design **smoke trivial** (1 tile, `runtime_sequence` vide) : ne valide **aucun**
  kernel du projet (Qwen3.6, Phi-3, Nanbeige, Granite).

Ce fichier **ne modifie aucun rapport** ; il documente l'origine du manifeste
manuel sans l'effacer (l'historique reste lisible).
