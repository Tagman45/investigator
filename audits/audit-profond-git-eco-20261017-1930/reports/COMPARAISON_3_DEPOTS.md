# Démonstration — le skill fait seul, en local, l'équivalent GitDiagram ×3 + comparaison

**Demande** : `gitdiagram.com/{gat45/op15-adaptive-harness, tagman45/adaptive-xdna-runtime, tagman45/doc-skill-xdna2}` — « il doit être capable de faire ça seul en local et de les comparer ».

**Réponse démontrée** : oui — sans appeler gitdiagram.com. Clone superficiel read-only (`--depth 1`), inspection locale (`inspect_repository.py`), diagrammes générés localement (`diagram_local.py`), comparaison (`compare_repos.py`). Les clones temporaires ont été supprimés après usage ; seuls les artefacts JSON/Markdown/Mermaid restent dans `out/`.

## Diagrammes générés (arêtes INFERRED — imports statiques, jamais preuve d'exécution)

| Dépôt | Nœuds | Relations | Fichier |
|---|---|---|---|
| HARNESS (`gat45/op15-adaptive-harness` @ `f08ce62e`) | 17 | 13 | `out/diagram_HARNESS.{mmd,json}` |
| RUNTIME (`tagman45/adaptive-xdna-runtime` @ `324e15a4`) | 136 | 144 | `out/diagram_RUNTIME.{mmd,json}` |
| DOCSKILL (`tagman45/doc-skill-xdna2` @ `f9a739d2`) | 38 | 36 | `out/diagram_DOCSKILL.{mmd,json}` |

## Comparaison (`out/compare3.{json,md}`)

- Fichiers communs aux 3 : **2** (`.gitignore`, `README.md`-like — recouvrement nominal).
- Jaccard structurel : HARNESS<>RUNTIME **0.003**, HARNESS<>DOCSKILL **0.001**, RUNTIME<>DOCSKILL **0.001** — trois architectures disjointes (attendu : harnais applicatif vs runtime NPU vs workspace documentaire).
- Manifests, langages, tests/CI, imports communs et candidats déplacés : voir `out/compare3.md`.

## Bug trouvé et corrigé pendant la démo (cause, pas contournement)

`inspect_repository.py` écrivait son JSON en `ensure_ascii=False` : les sorties git en cp1252 (byte `0xC9`) rendaient le fichier illisible (`UnicodeDecodeError`) pour `diagram_local.py`/`compare_repos.py` sur DOCSKILL. **Fix** : `ensure_ascii=True` + lecture explicite `encoding='utf-8'` dans `inspect_repository.py`, lectures `errors="replace"` dans les deux consommateurs. Les 86 tests restent verts.

## Limites honnêtes

- Clone `--depth 1` : l'historique profond (drift, renommages git) n'est pas analysé ici — c'est le rôle de `diff_repos.py` (mission Cartographe, à implémenter).
- Diagrammes = structure statique (dossiers, manifests, entry points, imports résolus) ; aucun flux runtime prouvé — les arêtes sont INFERRED par construction.
- Les SHAs cités sont ceux du jour du clone superficiel (17/10/2026).
