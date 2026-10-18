# Audit de `conftest.py` et des « 135 passed » (18/10/2026)

Fichier audité :
`C:\Users\videl\Desktop\doc-skill-xdna2-work\skills\local\git-ecosystem-investigator\tests\conftest.py`
(**12 lignes**, identique dans les 3 copies — `diff` exit 0 sur `.config/opencode`
et `skills_backup/opencode`).

## 1. Contenu réel et ce qu'il fait

```python
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "network: test faisant un appel réseau réel (sauté si injoignable)")
```

C'est **tout**. Conséquences vérifiables :

| Point d'audit | Constat |
|---|---|
| Fixtures qui fabriquent un succès (`autouse`, `monkeypatch` global) | **aucune** — le fichier ne définit aucune fixture |
| Mock global de production | **aucun** |
| `pytest_collection_modifyitems` qui désélectionne en masse | **absent** |
| Variable d'environnement qui éteint les tests | **absente** |
| Déclaration du marker `network` | présente, avec la règle « sauté si injoignable » |

Donc le `conftest.py` ne peut pas, à lui seul, produire un faux PASS. Le risque
est ailleurs (voir §3).

## 2. Ce que les 135 tests ont réellement fait

Exécution du 18/10, `python -m pytest tests -q -rs`, sur les **3 copies** :

| Copie | Résultat | Skips | Durée | Exit |
|---|---|---|---|---|
| `doc-skill-xdna2-work/skills/local/…` | **135 passed** | **0** | 18,24 s | **0** |
| `doc-skill-xdna2-work/skills_backup/opencode/…` | **135 passed** | **0** | 18,07 s | **0** |
| `.config/opencode/skills/…` | **135 passed** | **0** | 17,15 s | **0** |

`-rs` n'affiche **aucune ligne `SKIPPED`** : les 2 tests marqués `network` ont
donc réellement tourné (arXiv joignable), ils n'ont pas été contournés.

Fixture Atom vérifiée comme **réelle**, pas écrite à la main :
`tests/fixtures/arxiv/atom_1706.03762.xml` (2 965 octets) contient l'ID de
requête `https://arxiv.org/api/zUwBFJ+vAUSpXAR7QFveSY/bZos` et
`<updated>2026-10-18T05:15:40Z</updated>` — c'est une réponse d'API datée.

## 3. Faiblesses réelles de la suite (ce que « 135 passed » ne garantit pas)

| # | Faiblesse | Preuve | Effet |
|---|---|---|---|
| C1 | Un run **hors ligne** donnerait `133 passed, 2 skipped` avec **exit 0** | `tests/test_web_science.py:302-303`, `:316-318` : `if not rows: pytest.skip(...)` | Le compte « 135 » n'est reproductible qu'avec réseau ; un chiffre de PASS seul ne distingue pas « 135 exécutés » de « 133 exécutés + 2 sautés » |
| C2 | `pytest.importorskip("pypdf")` saute silencieusement si `pypdf` manque | `tests/test_web_science.py:198` | Sur une machine sans `pypdf`, la couverture PDF chute sans échec |
| C3 | Mocks présents (4) mais **explicitement étiquetés SIMULÉ** | `test_all_functions.py:85,98` ; `test_web_science.py:247-256` (« SIMULÉ explicitement ») | Ils testent la **classification** d'erreur, pas la vérité réseau — usage correct, à ne pas lire comme preuve d'accès réel |
| C4 | Code mort : `run_report()` défini et jamais utilisé | `tests/test_negative.py:11-16` | Cosmétique ; peut laisser croire à un helper partagé |
| C5 | Aucun test ne couvre `validate_kernel.ps1` ni les scripts PowerShell | `tests/` = Python uniquement | Les défauts D2/D3/D7 ne sont pas détectés par la suite |

Tests examinés pour faux positifs, et verdict :

- `test_get_sans_reseau` (port fermé `127.0.0.1:9`) : vérifie bien une erreur, pas un succès simulé — **OK**.
- `test_get_http_error_simulee` : patch `urlopen` → asserte `HTTP_403` — **OK**, test de mapping.
- `test_arxiv_filtre_reduit_les_faux_positifs_reel` : asserte
  `dropped >= 1` **et** `len(filt) < len(brut)` — non trivial, ne peut pas
  passer si le filtre ne retire rien — **OK**.
- `test_partiellement_confirme_*` : asserte des statuts précis et un
  `returncode == 1` sur le garde-fou — **OK**.

## 4. Portée exacte du résultat

Les 135 tests prouvent : le comportement **Python** des scripts du skill
(parsing, résilience, statuts, garde-fous, génération/corrélation de graphes)
sur cette machine, avec réseau, le 18/10/2026.

Ils **ne prouvent pas** : le bon fonctionnement sur NPU (aucun test matériel),
les scripts PowerShell (C5), le build WSL (D5), l'APK (0 device), ni la qualité
rédactionnelle des writers.

## 5. Recommandations de test (minimales)

1. **Rendre le compte stable** : lancer la CI avec
   `-m "not network"` (déterministe) **et** un job réseau séparé, ou faire
   échouer le job si `-rs` contient `SKIPPED` quand le réseau est supposé
   disponible. Sinon, écrire dans le rapport « 135 passed, 0 skipped » et
   jamais « 135 tests » seul.
2. **Rendre `pypdf` explicite** : remplacer `importorskip` par un test marqué
   `optional` et un compteur de skips affiché.
3. **Ajouter 3 tests PowerShell** (Pester ou appels directs) couvrant D2
   (`NOT_MEASURED`), D7 (MAC ≥ 2) et D3 (aucune exécution revendiquée).
4. Supprimer ou utiliser `run_report()` (C4).

## 6. Verdict

`conftest.py` est **sain** : il ne peut pas fabriquer de succès. Les
« 135 passed » sont **réels et reproductibles réseau allumé**, avec 0 skip sur
les 3 copies. La limite est dans la **forme de la preuve** (un compte de PASS
cache un skip) et dans la **couverture** (aucun test PowerShell, aucun test
matériel) — pas dans une triche de fixtures.
