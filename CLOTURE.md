# CLOTURE.md — règle de clôture

## 1. Ce qu'une clôture exige

Une lacune ne passe à `CORRIGÉE` que si **les trois** sont présents :

1. **La correction** — le fichier modifié est dans ce dépôt (ou dans `doc-skill-xdna2` pour un
   skill), avec son chemin et sa ligne.
2. **La validation** — la commande exécutée, son code de sortie et sa sortie brute, conservés
   dans `audits/<mission>/evidence/`. Le test doit exercer le **comportement demandé**, pas
   seulement importer le module.
3. **La traçabilité** — entrée `PREUVES.md` : source, SHA-256 si applicable, versions, limites.

Un test vert ne suffit jamais à lui seul : il peut passer sans exercer le comportement
(`ex. 12/12 tests du garde-fou ne prouvent pas qu'une taille acceptée est sûre`).

## 2. Statuts autorisés

| Statut | Sens |
|---|---|
| `OUVERTE` | aucun correctif prouvé |
| `EN COURS` | correctif partiel, validation incomplète |
| `CORRIGÉE (preuve)` | les trois éléments ci-dessus présents |
| `REFUSÉE (justif.)` | décision explicite de ne pas corriger, raison consignée |
| `À REVÉRIFIER` | statut hérité d'un rapport antérieur, non re-vérifié dans la mission courante |

Un statut `À REVÉRIFIER` n'est **jamais** présenté comme corrigé.

## 3. Interdits

- Écrire « corrigé » sur la base d'un raisonnement, d'une revue de code ou d'un ACCEPT d'audit.
- Retirer une lacune close : elle reste dans le registre avec sa preuve de clôture.
- Marquer un test `skip`/`xfail` pour faire passer la clôture ; toute exception doit être
  documentée comme lacune ouverte.
- Publier (push) sans autorisation utilisateur tracée.

## 4. Séquence de publication (une mission)

```bash
cd C:/Users/videl/skills-audit-reports
git add -A
git commit -m "<mission>: <objet>"                     # local, toujours permis
python tools/git_authorization.py record \
    --repo https://github.com/Tagman45/investigator --branch main --commit <sha> \
    --request-excerpt "<citation exacte du message utilisateur>" \
    --user-turn-ref "<référence du tour>"
python tools/git_authorization.py check \
    --repo https://github.com/Tagman45/investigator --branch main --commit <sha>   # 0 = ALLOW
git push origin main
git rev-list --left-right --count origin/main...HEAD   # doit afficher "0 0"
```

Si `check` renvoie BLOCK (3) : le commit reste **local**, et le rapport doit l'écrire
explicitement (« non poussé : aucune autorisation traçable »). Jamais de push silencieux.

## 5. Vérification finale d'une mission

- `INDEX.md` : une ligne, statut cohérent avec le rapport.
- `LACUNES.md` : toute lacune touchée a un statut à jour et son test de clôture.
- `PREUVES.md` : au moins une entrée par campagne, avec code de sortie.
- `git status` : propre (hors artefacts ignorés) ; `git rev-list` : `0 0` après push autorisé.
