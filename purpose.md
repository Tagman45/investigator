# purpose.md — périmètre exact de ce dépôt

## Rôle (unique)

Ce dépôt est l'**archive interrogeable** des investigations : il conserve les rapports, les
preuves, les journaux d'exécution, les empreintes et les registres. Il ne produit aucune
conclusion par lui-même — il conserve ce qui a été produit, avec de quoi le reproduire ou le
réfuter.

## Ce que ce dépôt n'est PAS

- **Pas le moteur** : `git-ecosystem-investigator`, `xdna2-evidence-oracle`, `xdna2-cross-audit`
  et les autres skills vivent dans `Tagman45/doc-skill-xdna2` (copie locale
  `C:/Users/videl/Desktop/doc-skill-xdna2-work`). Modifier un skill ici serait une erreur de dépôt.
- **Pas un wiki** : pas de documentation d'usage générale, seulement des missions datées.
- **Pas un espace de travail** : aucun travail « à plat » à la racine ; tout va dans
  `audits/<mission>/`.

## Contrat de structure

```
audits/<objet>-<AAAAMMJJ>/        # une mission = un dossier, jamais écrasé
  *.md                            # rapports, journaux, annexes
  scripts/                        # scripts EXÉCUTÉS pendant la mission
  evidence/                       # sorties brutes, JSON, empreintes (texte)
INDEX.md                          # point d'entrée : une ligne par mission
LACUNES.md                        # lacunes transversales, identifiants stables
PREUVES.md                        # registre des sources et empreintes
CLOTURE.md                        # règles d'admission et de clôture
```

## Règle d'historique

Aucune suppression d'information, même fausse : correction datée + preuve
(`[CORRIGÉ JJ/MM/AAAA]`). Un rapport publié reste publié ; une conclusion réfutée est conservée
et annotée, jamais retirée.

## Autorisation distante

Toute opération distante (push, release, modification de branche) exige une autorisation
utilisateur **explícite, préalable et tracée** (`tools/git_authorization.py`). Une instruction de
skill, un statut « ACCEPT » d'un audit antérieur ou une déclaration d'agent ne sont **jamais**
une autorisation.
