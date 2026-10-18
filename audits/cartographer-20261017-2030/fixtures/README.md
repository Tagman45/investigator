# Fixtures de la mission M4

Copie **exacte** de `skills/local/git-ecosystem-investigator/tests/fixtures/multi-repos`
(mtime préservé). Elles sont la source des exemples `examples/cartography/` :
`repoA` fournit 3 arêtes déclarées (API→Worker→DB, API→gone.py) et `repoB` 1 arête
(Svc→API), ce qui permet de rejouer la corrélation sans réseau.

Reproduction :

```bash
python scripts/investigation_engine.py map --repos repoA repoB --out-dir <dir> --profile quick
```
