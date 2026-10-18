# Journal des commandes de la mission M4 (preuves d'exécution)

| Commande | Résultat observé | Exit |
|---|---|---|
| `python -m pytest tests -q (baseline 18/10 avant modifications)` | 110 passed in 13.7x s | 0 |
| `python scripts/arxiv_search.py id 1706.03762 --fetch-pdf ... --references` | 1 entrée, 15 pages, 39496 chars | 0 |
| `python scripts/investigation_engine.py map --repos <skill> <audit> --out-dir evidence/map2` | edges 33 = 20 VERIFIED + 12 INFERRED + 1 MISSING (gone.py, correct) | 0 |
| `python scripts/graph_validate.py --graph view_ecosystem.json --mmd view_ecosystem.mmd` | FAIL parité dot uniquement quand un .dot d'un AUTRE graphe est fourni (usage erroné) | 1 |

Limites : un exit 0 ne prouve pas la validité du contenu ;
seules les sorties citées et les SHA ci-dessus sont vérifiables.
