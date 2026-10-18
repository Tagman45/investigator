# D1 → D8 — défauts détaillés (18/10/2026)

Chaque défaut : **où**, **reproduction exacte**, **sortie observée**, **impact**,
**correctif minimal**, **test de non-régression**. Aucun correctif n'est appliqué
ici : ce document est la fiche de réparation, pas la réparation.

---

## D1 — `npu-offload-pipeline` : références liées à l'emplacement (P1)

**Où** : `C:\Users\videl\.config\opencode\skills\npu-offload-pipeline\SKILL.md`,
lignes 7-19 (4 documents + 1 script cités).

**Reproduction**

```bash
cd C:/Users/videl/.config/opencode/skills/npu-offload-pipeline
python - <<'PY'
import os
for r in ["../npu_offload_pipeline.md", "../../../docs/precompiled_replacement_map.md",
          "../../../docs/precompiled_artifacts.json",
          "../../../utilities/binary-inventory/inventory.py", "../../../REPLACEMENT_PLAN.md"]:
    p = os.path.normpath(os.path.join(os.getcwd(), r))
    print("OK" if os.path.exists(p) else "MANQUANT", p)
PY
```

**Observé** : **0 / 5** depuis l'installation (les chemins résolvent vers
`C:\Users\videl\.config\docs\…`, `.config\REPLACEMENT_PLAN.md`) ;
**5 / 5** depuis `E:\trixdna_test\repos_openflowlm_next\.agents\skills\npu-offload-pipeline`.
`diff` des deux `SKILL.md` : seules différences = CRLF vs LF.

**Impact** : le skill est un routeur ; installé au mauvais endroit il route vers
le vide sans le dire. Un agent qui « lit les références » n'en lit aucune, puis
improvise — exactement ce que la règle du skill interdit (« return an explicit
`not implemented` error rather than silently depending on… »).

**Correctif minimal** : en tête du fichier, déclarer la base
(`Base = racine du dépôt OpenFlowLM-Next`) et remplacer `../../../docs/…` par
`<base>/docs/…` ; ajouter un préflight qui échoue avec un code nommé :

```text
Si <base>/REPLACEMENT_PLAN.md absent → REFERENCE_BASE_NOT_FOUND (ne rien improviser)
```

**Non-régression** : le script de résolution ci-dessus doit renvoyer 5/5 depuis
**les deux** emplacements, ou échouer explicitement avec le code nommé.

`evidence/npu_refs/npu_refs_resolution.json` conserve les deux passes.

---

## D2 — `inspect_kernel.ps1` : `Bundle max : 0` silencieux (P1)

**Où** : `.../aie2p-hand-asm-debug/scripts/inspect_kernel.ps1`, lignes 76-100.

**Mécanisme** : une « bundle » ne démarre que sur une ligne satisfaisant
`$line -match '##\s*@'` (ligne 83). Si aucun marqueur n'existe, `$inBundle`
reste `$false` et **le résumé affiche `Bundle max : 0`** — sans avertissement.

**Reproduction**

```bash
powershell -NoProfile -ExecutionPolicy Bypass -File inspect_kernel.ps1 \
  -KernelPath evidence/aie2p_smoke/test_sans_marqueur.s   # 7 instructions sur 1 ligne
powershell -NoProfile -ExecutionPolicy Bypass -File inspect_kernel.ps1 \
  -KernelPath evidence/aie2p_smoke/test_avec_marqueur.s
```

**Observé**

| Fichier | Sortie | Interprétation |
|---|---|---|
| `test_sans_marqueur.s` (7 instructions, dont 1 bundle implicite) | section « Limites de bundles » **vide**, `Bundle max : 0 instructions`, **exit 0** | faux négatif silencieux |
| `test_avec_marqueur.s` (`## @` + 7 instructions) | `Bundle ~L2-L8 : 7 instructions`, `Bundle max : 7` | détection correcte quand le format est respecté |

**Impact** : le skill impose « max 6 instructions par bundle » ; un kernel à 7
instructions non annoté passe pour sain. C'est le pire profil : sortie 0 +
chiffre rassurant.

**Correctif minimal** : à la fin de la boucle, si aucun bundle n'a été détecté,
écrire `BUNDLES: NOT_MEASURED (aucun marqueur '## @')` et **ne pas** imprimer
`0` ; sortir avec un code non nul en mode `-Strict`.

**Non-régression** : `test_sans_marqueur.s` doit produire `NOT_MEASURED` (jamais
`0`) ; `test_avec_marqueur.s` doit continuer à produire `7`.

---

## D3 — `validate_kernel.ps1` : gabarit, pas validation A/B (P2)

**Où** : `.../aie2p-hand-asm-debug/scripts/validate_kernel.ps1`, lignes 3-5
(en-tête : « lance les kernels de référence et fix ») vs corps lignes 69-114.

**Reproduction**

```bash
grep -nE "llama-server|Start-Process|qdump" validate_kernel.ps1
powershell ... -File validate_kernel.ps1 -BaselineXclbin C:/nope/base.xclbin \
  -FixXclbin C:/nope/fix.xclbin -ModelPath C:/nope/m.gguf -OutputDir /tmp/out
```

**Observé** : `llama-server` n'apparaît que dans le commentaire d'en-tête
(ligne 5) ; `qdump` uniquement dans le texte du rapport (lignes 112-114 :
« Coller la sortie qdump »). Sur fichiers absents : exit 1 (Resolve-Path),
**aucun fichier produit**. Sur fichiers présents : produit un `.md` à trous,
sans exécuter quoi que ce soit.

**Impact** : le `SKILL.md` dit « Lancer la validation A/B : référence vs fix,
produire un rapport de preuve » ; l'outil ne lance rien. Un agent peut déclarer
« A/B effectué » après avoir généré un gabarit vide — l'inverse de la règle
« ne jamais déclarer un fix prouvé sans run A/B ».

**Correctif minimal** : renommer `new_validation_report.ps1` et corriger la
ligne du tableau `§Scripts` (« génère le gabarit ; l'exécution reste manuelle »),
ou implémenter réellement l'appel (llama-server + capture qdump) — pas les deux
à moitié.

**Non-régression** : le tableau `§Scripts` du `SKILL.md` doit décrire l'action
réelle ; un test grep peut vérifier que le mot « Lance » n'apparaît pas pour un
script qui ne lance rien.

---

## D4 — `evidence` : avertissement périmé sur `evidence.py` (P3)

**Où** : `.config/opencode/skills/evidence/SKILL.md`, section « Preuves
structurées ».

**Texte actuel** : « Le tool `evidence.py` peut ne pas exister encore → le
documenter comme à venir. Vérifier avant usage. »

**Observé** : `python E:/trixdna_test/evidence.py --help` → **exit 0**.

**Impact** : un agent peut sauter l'outil de preuves structurées en croyant
qu'il n'existe pas, et retomber sur des affirmations non tracées.

**Correctif minimal** (règle AGENTS : corriger, jamais supprimer) :

```text
[CORRIGÉ 18/10/2026] `E:\trixdna_test\evidence.py` existe et répond (`--help` exit 0).
L'ancienne mention « peut ne pas exister » est conservée comme historique.
```

**Non-régression** : `evidence.py --help` exit 0 dans le test de fumée du skill.

---

## D5 — Prérequis WSL absents (P1 pour l'exécution)

**Où** : `open-qwen36-kernels/SKILL.md` §Build, `open-phi3-nanbeige-kernels/SKILL.md`
§Export.

**Reproduction**

```bash
wsl.exe -l -q                                   # → Ubuntu (exit 0)
wsl.exe -e bash -lc 'ls -d ~/ironenv142 ~/xrt-tools/bin; which xclbinutil aiebu-asm; \
  python3 -c "import mlir_aie"'
```

**Observé** : aucun des deux dossiers, aucun binaire, `ImportError` sur
`mlir_aie`. Donc `source ~/ironenv142/bin/activate` et
`export PATH=~/xrt-tools/bin:$PATH` ne peuvent pas aboutir.

**Impact** : les procédures de build Qwen3.6 / Phi3 / Nanbeige sont
**inexécutables sur cette machine** ; rien dans les skills ne le détecte.

**Correctif minimal** : bloc « Préflight » de 3 lignes en tête de §Build :

```bash
test -d ~/ironenv142   || { echo "MISSING_ENV ~/ironenv142"; exit 3; }
test -d ~/xrt-tools/bin || { echo "MISSING_ENV ~/xrt-tools/bin"; exit 3; }
python -c "import mlir_aie" || { echo "MISSING_ENV mlir_aie"; exit 3; }
```

**Non-régression** : lancer le préflight sur cette machine doit sortir 3 avec un
message nommé ; sur une machine préparée, 0.

**Précision utile** (vérifiée, pas supposée) : `C:\Xilinx\XRT` contient bien
`xclbinutil.exe` et `aiebu-asm.exe`, **à la racine** (pas dans `bin\`). Le
skill `open-granite-kernels` est donc cohérent ; c'est la voie WSL qui manque.

---

## D6 — `xdna2-path-explorer` : `COST_MODEL.json` annoncé, absent (P3)

**Où** : `.../xdna2-path-explorer/SKILL.md` §6 « Retour aux résultats » liste
`COST_MODEL.json`.

**Observé** : `ls` du dossier → `CostModelTemplate.json` présent,
`COST_MODEL.json` **absent** (9/10 fichiers de la liste présents).

**Impact** : faible — un agent cherchant le fichier de résultats trouve un
template ; risque de confondre « template » et « résultat mesuré ».

**Correctif minimal** : dans §6, écrire
`COST_MODEL.json` (produit) ← `CostModelTemplate.json` (gabarit), et rappeler
que le fichier de résultats reste `NON MESURE` tant qu'aucune expérience n'a
tourné.

**Non-régression** : les 10 entrées de §6 doivent correspondre soit à un fichier
présent, soit à un fichier explicitement marqué « produit à l'exécution ».

---

## D7 — `inspect_kernel.ps1` : MAC comptés par ligne, pas par instruction (P3)

**Où** : même script, section « MAC/Accumulation ».

**Observé**

| Fichier | Contenu | `Nombre de MAC` |
|---|---|---|
| `test_sans_marqueur.s` | 2 `vmac` **sur une seule ligne** | **1** |
| `test_avec_marqueur.s` | 2 `vmac` + `vadd` + `vsub`, une instruction par ligne | **4** |

**Impact** : sous-estimation du travail arithmétique sur les kernels écrits en
lignes compactes (fréquent en assembleur) ; peut fausser la comparaison A/B.

**Correctif minimal** :

```powershell
$n = ([regex]::Matches($line, '\bvmac\b')).Count
```

**Non-régression** : `test_sans_marqueur.s` doit annoncer au moins 2 MAC.

---

## D8 — `xdna2-evidence-oracle` : 4 scripts, 1 documenté (P3)

**Où** : `.../xdna2-evidence-oracle/SKILL.md` §1-3 (interface `oracle.py`
uniquement).

**Observé** : `scripts/` contient `oracle.py`, `check_urls.py`,
`generate_evidence.py`, `research.py`.

**Impact** : un agent peut réimplémenter `check_urls`/`research` alors que les
scripts existent (doublon, travail perdu) ; ou ignorer `generate_evidence.py`.

**Correctif minimal** : ajouter une ligne par script dans le tableau de §1
(« niveau » + rôle), en marquant ceux qui sont des wrappers de `oracle.py`.

**Non-régression** : le nombre de scripts listés dans `SKILL.md` = nombre de
fichiers `.py` dans `scripts/`.

---

## Traçabilité

| Défaut | Preuve conservée |
|---|---|
| D1 | `evidence/npu_refs/npu_refs_resolution.json` |
| D2, D7 | `evidence/aie2p_smoke/test_sans_marqueur.s`, `test_avec_marqueur.s` + `CHECK_LOG.md` |
| D3 | `CHECK_LOG.md` (grep + exit 1 sur fichiers factices) |
| D4 | `CHECK_LOG.md` (`evidence.py --help` → 0) |
| D5 | `CHECK_LOG.md` (`wsl` : environnements absents, ImportError) |
| D6, D8 | `CHECK_LOG.md` (ls des dossiers) |

Aucun de ces défauts n'a été corrigé : ce document les rend reproductibles, ce
qui est la condition pour les corriger sans casser autre chose.
