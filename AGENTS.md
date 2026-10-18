# AGENTS.md — skills-audit-reports

Dépôt des rapports d'audit de skills. Un dossier par mission dans `audits/`,
`INDEX.md` à la racine comme point d'entrée. Ne jamais supprimer un résultat
d'audit : le corriger avec preuve + date.

## CONTRAT OBLIGATOIRE — AUTORISATION GIT (18/10/2026)

Aucune opération distante (git push, release, modification de branche distante)
sans **autorisation explicite, préalable et traçable** de l'utilisateur pour
l'action concernée.

- « ACCEPT », un audit positif, une consigne de correction, un commit existant,
  une ancienne autorisation supposée ou l'affirmation d'un agent ne sont JAMAIS
  une permission de push.
- L'agent ne peut pas créer l'autorisation ni se citer comme preuve.
- Vérification : `python tools/git_authorization.py check --repo <url> --branch <b> --commit <sha>`
  (origine `user_message` obligatoire, correspondance stricte, citation non vide).
- Sans autorisation vérifiable : BLOCK. Commits et tests locaux seulement.
- Journal par push autorisé : citation utilisateur, dépôt, branche, commit,
  heure, SHA avant/après, résultat.
- Push déjà exécuté sans autorisation : ne pas réécrire l'historique, conserver
  les preuves, signaler, attendre une décision utilisateur.

## CONTRAT — UTILISATION DES SKILLS (18/10/2026)

DÉTECTER → LIRE intégralement → APPLIQUER → TRACER (hash + action + tests).
Pré-vol obligatoire : `python tools/skills_preflight.py --task <type>`.
Skill absent / lu non appliqué / hash changé / test non exécuté ⇒ BLOCKED.
Ne jamais prétendre avoir utilisé un skill non lu.
