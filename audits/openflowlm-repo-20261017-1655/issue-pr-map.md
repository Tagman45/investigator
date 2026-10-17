# Issue / PR map — OpenFlowLM-Next

## État de la collecte
- **API GitHub : `INACCESSIBLE`** — `collect_github_data.py` non authentifié, 5/5 endpoints `HTTP_403` (rate limit). `GITHUB_TOKEN` non configuré sur cette machine ; la politique du skill interdit de l'imprimer et de le demander en ligne de commande. Aucune donnée issues/PR récupérée : **not_found_in_searched_scope**.
- Sources locales de remplacement consignées (sans invention) :
  - Historique git local : `--bench`, `#206`, `#211`, `#169`, `#205` apparaissent dans les 5 derniers sujets de commit (preuves dans `repository-inspect.json → recent_log`). Ce sont des **références gévariées** dans un clone local — leur vérification côté serveur aurait besoin de l'API.
  - Le repo `open_kernels/` porte des docs internes citant des PR/issues locales (ex. `#148` dans `open_kernels/recipes/qwen35.py` = commentaire, `PR #206/#211` en messages de commit merge-style).

## PR vues via les sujets de commit (clone local, HEAD 7af242e)
| Ref | Objet (sujet de commit local) | Certainty |
|---|---|---|
| #206 | « Update volume mounts with SELinux context for docker/podman build » | CONFIRMED_STATIC (message de commit local, format squash/merge) |
| #211 | « Move agent skills from .opencode/skill to .agents/skills » | CONFIRMED_STATIC (même base) |
| #169 | « spec-decode: plan, and rolling the DeltaNet state back… » | CONFIRMED_STATIC |
| #205 | « feat: speed up linux and docker builds with mold and ccache » | CONFIRMED_STATIC |

- Issues ouvertes/fermées, reviews, fichiers modifiés par PR : **non mesurés** (API fermée). Ne pas écrire « exhaustif ».
