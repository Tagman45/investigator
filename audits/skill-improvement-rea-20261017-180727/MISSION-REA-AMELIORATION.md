# MISSION REA â€” AmÃ©liorer le skill d'audit sans dÃ©grader l'existant

## Contexte
- DÃ©pÃ´t : C:\Users\videl\skills-audit-reports
- Branche : main
- HEAD de dÃ©part : 6c77cf00f65d0b175c416f469bc2d5c7f44fdad1
- SkillPath dÃ©clarÃ©/dÃ©tectÃ© : (Ã  identifier par l'agent dans le dÃ©pÃ´t)
- Manifeste SHA-256 initial : baseline-manifest.json
- Rapport attendu dans ce dossier : C:\Users\videl\skills-audit-reports\audits\skill-improvement-rea-20261017-180727

## Objectif
Auditer le skill et son pipeline, puis proposer et appliquer uniquement les amÃ©liorations dÃ©montrÃ©es par des preuves. PrioritÃ©s : qualitÃ© des rapports, traÃ§abilitÃ© preuveâ†’conclusion, couverture explicite, contradictions, reproductibilitÃ©, tests nÃ©gatifs, validation indÃ©pendante. Le dÃ©pÃ´t d'audits de rÃ©fÃ©rence est https://github.com/Tagman45/investigator ; les rÃ©sultats M1/M2 et les quatre amÃ©liorations ouvertes de EVD-20261017-010 doivent Ãªtre vÃ©rifiÃ©s dans le dÃ©pÃ´t, pas supposÃ©s exacts.

## Contraintes impÃ©ratives
1. Ne jamais pousser, publier, crÃ©er de PR ni faire de commit.
2. Ne jamais supprimer/Ã©craser les rapports historiques ou les artefacts d'origine.
3. Avant toute modification, identifier le skill rÃ©ellement utilisÃ©, ses copies, les scripts, schÃ©mas, tests et consommateurs. Signaler les chemins introuvables au lieu de les inventer.
4. Ã‰tablir l'Ã©tat initial et prÃ©server les changements prÃ©existants. Si l'arbre est sale, ne pas les toucher.
5. SÃ©parer faits vÃ©rifiÃ©s, hypothÃ¨ses, limites et recommandations. Utiliser UNKNOWN si une preuve manque.
6. Ne pas considÃ©rer HTTP 200, prÃ©sence d'un fichier, TODO cochÃ© ou simple exÃ©cution rÃ©ussie comme preuve suffisante.
7. Ne pas ajouter une dÃ©pendance ou un projet tiers sans vÃ©rifier son URL, son code, sa licence, sa maintenance et son adÃ©quation. RÃ©utiliser les composants seulement si le gain est dÃ©montrÃ©.
8. Ne pas modifier le comportement fonctionnel du skill avant d'avoir produit un diagnostic et des tests de rÃ©fÃ©rence.
9. Aucun secret, token, chemin personnel inutile ou donnÃ©e privÃ©e dans les rapports.
10. Les changements doivent Ãªtre minimaux, rÃ©versibles et accompagnÃ©s de tests.

## Phase 1 â€” Inventaire et rÃ©fÃ©rence
- Lire les instructions REA rÃ©ellement installÃ©es et les fichiers du skill.
- Inventorier les copies du skill et comparer les fichiers (chemins, tailles, SHA-256); dÃ©tecter les dÃ©rives de synchronisation.
- Cartographier scripts â†’ entrÃ©es â†’ sorties â†’ schÃ©mas/validateurs â†’ consommateurs.
- Lire INDEX.md, les missions M1/M2 et EVD-20261017-010 si prÃ©sents. Identifier les quatre amÃ©liorations ouvertes par leur ID et leur Ã©tat rÃ©el.
- Capturer versions, commandes, codes de sortie, durÃ©e et artefacts actuels. Ne pas exÃ©cuter de commande destructive.
- Produire une matrice Â« exigence / implÃ©mentation / preuve / test / statut Â».

## Phase 2 â€” Ã‰valuation adversariale
CrÃ©er ou rÃ©utiliser un corpus de tests synthÃ©tiques sans toucher aux donnÃ©es rÃ©elles :
- preuve absente ou sans source ;
- citation avec fichier/ligne inexistant ;
- hash erronÃ© ;
- URL morte, redirection, erreur HTTP et rÃ©ponse 200 non probante ;
- contradiction entre deux sources ;
- rÃ©sultat JSON invalide ou champ requis absent ;
- test dÃ©clarÃ© PASS alors que la commande Ã©choue ;
- zone du dÃ©pÃ´t non inspectÃ©e ;
- conclusion plus forte que les preuves ;
- deuxiÃ¨me exÃ©cution non reproductible ;
- copies du skill divergentes ;
- ancien rapport incomplet ou schema obsolÃ¨te.
Pour chaque cas, prÃ©ciser le rÃ©sultat attendu avant de lancer le test. Mesurer faux positifs, faux nÃ©gatifs et cas UNKNOWN. Ne pas inventer de taux si le corpus est trop petit.

## Phase 3 â€” AmÃ©liorations prioritaires
N'implÃ©menter que les lacunes confirmÃ©es :
P0. TraÃ§abilitÃ© : chaque constat a un ID stable, niveau de gravitÃ©, statut, source exacte, commit/version, chemin+ligne ou URL+date d'accÃ¨s, hash quand pertinent, commande et rÃ©sultat reproductible.
P0. ChaÃ®ne de preuve : constat â†’ preuves â†’ raisonnement explicite â†’ contre-preuve recherchÃ©e â†’ confiance/limites â†’ test de validation.
P0. Ã‰tats contrÃ´lÃ©s : CONFIRMED / SUPPORTED / REFUTED / UNKNOWN, sans transformer une absence de preuve en rÃ©futation.
P1. Couverture : Ã©lÃ©ments inspectÃ©s, non inspectÃ©s, raisons, exclusions et risques rÃ©siduels.
P1. Contradictions : dÃ©tecter les affirmations incompatibles et les laisser ouvertes tant que non rÃ©solues.
P1. ReproductibilitÃ© : environnement, versions, commande, code de sortie, durÃ©e, empreintes des artefacts.
P1. Validation des sorties par schÃ©ma, rÃ©fÃ©rences et liens preuveâ†’conclusion.
P2. Diff entre rapports successifs : nouveaux, rÃ©solus, rÃ©gressions, changements de preuve et changements de confiance.
P2. Priorisation : impact, probabilitÃ©, confiance, coÃ»t de validation et critÃ¨re d'acceptation mesurable.
Ã‰viter de crÃ©er des fichiers redondants si une sortie existante peut Ãªtre Ã©tendue de faÃ§on rÃ©trocompatible.

## Phase 4 â€” VÃ©rification
- ExÃ©cuter la suite existante avant/aprÃ¨s et les tests nÃ©gatifs.
- Comparer les rapports existants et nouveaux : les faits ne doivent pas disparaÃ®tre silencieusement.
- Valider le format, les liens, les hashes, les rÃ©fÃ©rences et les codes de sortie.
- Rejouer au moins deux fois les tests dÃ©terministes et comparer les sorties normalisÃ©es.
- VÃ©rifier le diff final et confirmer qu'aucun rapport historique n'a Ã©tÃ© Ã©crasÃ©.
- Si les tests ne peuvent pas Ãªtre exÃ©cutÃ©s, marquer BLOCKED/UNKNOWN avec la raison prÃ©cise.

## Livrables attendus dans ce dossier
1. ssessment.md â€” diagnostic avant modification, preuves et lacunes confirmÃ©es.
2. coverage-matrix.csv â€” exigences, code, preuve, test, statut.
3. 	est-cases.jsonl â€” cas, rÃ©sultat attendu, rÃ©sultat observÃ©, statut.
4. indings.md â€” constats triÃ©s par prioritÃ©, avec sources exactes.
5. changes.md â€” changements exacts, justification, risques et retour arriÃ¨re.
6. alidation.md â€” commandes, versions, codes de sortie, durÃ©e, rÃ©sultats.
7. esidual-risks.md â€” zones non couvertes et inconnues.
8. inal-manifest.json â€” hashes des livrables et fichiers modifiÃ©s.
9. scorecard.json â€” scores avant/aprÃ¨s seulement si mÃ©triques mesurÃ©es.

## CritÃ¨res d'acceptation
- Aucune modification hors pÃ©rimÃ¨tre ni aucun commit/push.
- Chaque conclusion importante est reliÃ©e Ã  une preuve vÃ©rifiable ou marquÃ©e UNKNOWN.
- Tous les cas nÃ©gatifs ont un rÃ©sultat attendu et un rÃ©sultat observÃ©.
- Les Ã©checs ne sont pas convertis en PASS.
- Les fichiers historiques sont conservÃ©s.
- Le rapport dit explicitement ce qui n'a pas Ã©tÃ© testÃ©.
- Le gain est dÃ©montrÃ© par comparaison avant/aprÃ¨s, pas par une note subjective seule.

## Rapport final Ã  afficher
RÃ©sumÃ© exÃ©cutif, lacunes confirmÃ©es, changements effectuÃ©s (ou aucun), tests exÃ©cutÃ©s et rÃ©sultats, mÃ©triques avant/aprÃ¨s, risques rÃ©siduels, fichiers modifiÃ©s, et dÃ©cision ACCEPT / REVISE / BLOCKED. Ne prÃ©tends pas avoir exÃ©cutÃ© une Ã©tape non exÃ©cutÃ©e.
