# External references — destinations canoniques (2026-10-17)

Générée depuis `url-discovery-ledger.jsonl` (provenance : `extract_references.py` sur `README.md`, `docs/index.md`, `docs/models.md` du repo local ; normalisation par `normalize_git_urls.py`).

| Evidence | Destination canonique | Type | Statut | Justification |
|---|---|---|---|---|
| URL-001 | github.com/user-attachments/assets/36d563a8… | github_object | DECLARED | asset image du README, non inspecté |
| URL-002 | img.shields.io/badge/NPU-Optimized-red | external | DECLARED | badge, hors périmètre |
| URL-003 | github.com/Atomic-Germ/OpenFlowLM/releases/latest/download/oflm-setup.msi | release | DECLARED | lien téléchargement officiel, présenté par les docs, binaire non téléchargé dans ce test |
| URL-004 | github.com/Atomic-Germ/OpenFlowLM | repository | CONFIRMED_STATIC | org du release MSI + docs |
| URL-005 | discord.com/invite/jtWZdMJ8ee | external | OUT_OF_SCOPE | média |
| URL-006…010 | youtu.be/TT7WZO…, sZt1Wy…, BLd2j9…, 0t8ij…, mPrr9… | external | OUT_OF_SCOPE | vidéos démo |
| URL-011 | github.com/Atomic-Germ/OpenFlowLM/releases | release | CONFIRMED_STATIC (cible org connue) | releases upstream |

## Manquements déclarés
- Aucune URL suivie en HTTP (à part la sonde API tombée en 403) : l'expansion externe profonde est **hors budget de ce test** (règle skill : arrêter quand ça n'ajoute rien pour la question = tester les scripts, pas archaeologie complète).
- Les liens relatifs `/docs/models/` du site docs ne sont pas résolus vers un domaine de publication (CNAME `CNAME` présent dans `docs/` — à tracer lors d'une vraie investigation).
