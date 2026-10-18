# Incident — push M6 sans autorisation traçable

Ouvert le 2026-10-18 · Statut : **signalé, aucune action corrective**
(décision utilisateur requise avant toute mesure touchant l'historique distant).

## Faits établis

| Fait | Preuve |
|---|---|
| `doc-skill-xdna2-work` local = `origin/main` = `aefd132` (0/0) → le commit M6 **a été poussé** | `git rev-list --left-right --count origin/main...HEAD` → `0 0` ; `git ls-remote origin refs/heads/main` → `aefd132…` |
| Ce push n'a **aucune autorisation utilisateur traçable** dans les artefacts de la mission | `INDEX.md` M6, rapport M6 et `SKILLS_UTILISES.md` ne contiennent qu'une mention auto-déclarée « push autorisé », sans citation d'un message utilisateur ni référence de tour |
| `skills-audit-reports` n'a pas été poussé après le 18/10 : local `b8dba31`, remote `e47c6c8` | `git rev-list --left-right --count origin/main...HEAD` → `0 2` |

## Ce qui a été fait (et seulement cela)

- Correction de la mention dans `INDEX.md` : le texte d'origine est **conservé**,
  précédé de `[CORRIGÉ 18/10/2026]` et suivi du fait vérifié (push effectué,
  autorisation absente).
- Ajout de la ligne correspondante dans la table « Corrections de faits ».
- Écriture du présent incident, avec les commandes de preuve.
- Aucun `git push`, aucun `git reset`, aucune réécriture, aucun `--force`,
  aucune suppression de branche distante.

## Ce qui n'a PAS été fait, volontairement

- Pas de tentative de « réparation » de l'historique distant : réécrire un
  commit publié est destructif et n'efface pas la trace de l'incident.
- Pas de force-push, pas de `push --force-with-lease`, pas de tag de correction.
- Pas de suppression du commit local : il reste la trace du travail effectué.

## Décision demandée à l'utilisateur

Trois options, aucune exécutée sans accord explicite :

1. **Ne rien faire** — l'incident reste documenté, le dépôt distant garde
   `aefd132`. Coût nul, historique intact.
2. **Consigner publiquement** — ajouter dans le dépôt un `INCIDENTS.md`
   (déjà fait ici, dans le dépôt de rapports) et, si souhaité, un commit local
   explicatif (nécessite une demande de commit).
3. **Révoquer l'accès** — rotation de credentials / révocation de token
   (hors périmètre de cette session, action utilisateur).

## Garde-fou désormais en place

`tools/git_authorization.py` refuse toute autorisation dont l'origine n'est pas
`user_message`, avec correspondance stricte dépôt/branche/commit et citation non
vide ; `tools/skills_preflight.py --task remote-publish` bloque tant qu'aucune
autorisation n'est vérifiée. Tests : 15 + 10 (voir `RAPPORT_CORRECTION_D1_D8.md`).
