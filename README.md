# investigator

Dépôt d'archives des **missions d'investigation** : rapports d'audit, preuves brutes,
journaux d'exécution, registres de lacunes et d'évidences. Un dossier par mission dans
`audits/`, `INDEX.md` à la racine comme point d'entrée unique.

Ce dépôt **ne contient pas le code du moteur** : le moteur et ses skills vivent dans
`Tagman45/doc-skill-xdna2` (copie de travail locale : `C:/Users/videl/Desktop/doc-skill-xdna2-work`).

## Ce que contient ce dépôt

| Élément | Rôle |
|---|---|
| `INDEX.md` | index des missions : objet, date, statut, livrables, lacunes ouvertes |
| `audits/<mission>/` | un dossier par mission, jamais à plat ; preuves dans `evidence/` |
| `LACUNES.md` | registre central des lacunes transversales (identifiants stables) |
| `PREUVES.md` | registre des preuves : sources, SHA-256, commandes, versions, limites |
| `CLOTURE.md` | règle de clôture : ce qui autorise à écrire « corrigé » |
| `tools/` | scripts de vérification (pré-vol skills, garde-fou git, smoke aiecc) |
| `tests/` | tests de ces scripts (pytest) |

## Démarrage rapide

```bash
cd C:/Users/videl/skills-audit-reports
python -m pytest tests -q                      # tests des outils du dépôt
python tools/git_authorization.py check --repo https://github.com/Tagman45/investigator \
    --branch main --commit <sha>               # 0 = ALLOW, 3 = BLOCK
git log --oneline -- audits/<mission>          # historique d'une mission
grep -rn "L-P0-03" .                           # retrouver une lacune partout
```

Nouvelle mission :

```bash
mkdir -p audits/<objet>-<AAAAMMJJ>/evidence
# écrire les livrables, puis :
# 1. mettre à jour INDEX.md (une ligne par mission)
# 2. mettre à jour LACUNES.md et PREUVES.md
# 3. git add -A && git commit -m "<mission>: <objet>"
# 4. autorisation traçable puis push (voir CLOTURE.md)
```

## Contrat de preuve (résumé)

- Chaque affirmation porte un statut : `CONFIRMÉ` / `RÉFUTÉ` / `HYPOTHÈSE` / `INCONCLUSIF` /
  `NON TESTÉ`, avec sa preuve localisable (fichier:ligne, sortie de commande, code de sortie).
- `HTTP 200` ne prouve pas le contenu ; une arête statique ne prouve pas l'exécution ; une
  absence de résultat de recherche ne prouve pas l'inexistence.
- Ne jamais supprimer une information : la corriger avec preuve + date (`[CORRIGÉ JJ/MM/AAAA]`).

## Limites connues

- Le registre `LACUNES.md` est **jeune** : les statuts non revérifiés sont marqués `À REVÉRIFIER`.
- Les preuves lourdes (binaires) restent hors dépôt ; seules les empreintes et sorties texte sont versionnées.
- Aucun push n'est effectué sans autorisation utilisateur tracée (`tools/git_authorization.py`).
