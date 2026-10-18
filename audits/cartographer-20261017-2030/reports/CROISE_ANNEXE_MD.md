# ANNEXE — croisement(des) R2 du dossier cartographe (17/10/2026)

## A. Croisement dépôt → URL → ressource corroborée

| Dépôt local | Remote déclaré | Accès HTTP (`curl`) | Ressource corroborée | Statut |
|---|---|---|---|---|
| `doc-skill-xdna2-work` | `https://github.com/Tagman45/doc-skill-xdna2` | **404 en anonyme**, **200 authentifié** (`gh api repos/Tagman45/doc-skill-xdna2`, `private: true`, `pushed_at 2026-10-17T18:17:33Z`) | `doc-skill-xdna2` **PRIVÉ** (id 1418598790, branche `main` = `546b2a3`) | ✅ distant existant — 404 expliqué par la visibilité, **CORRIGÉ 18/10/2026** |
| `skills-audit-reports` | `https://github.com/Tagman45/investigator` | **200** OK | `Tagman45/investigator` public (ID 1423448824) | ✅ accessible |
| `repos_openflowlm_next` (fork ouvert dans l'audit) | `repos_openflowlm_next` | (étranger) | Interdit de push par la règle 17/10/2026 | ⛔ refusé |

**Conclusion de la croix** : la source *déboguée* du skill (le paquet local
`skills/local/git-ecosystem-investigator/`) est bien synchronisée sur le
dépôt `investigator` (public, 200). Le dépôt `doc-skill-xdna2` **existe** :
il est **privé**, ce qui produit un 404 pour tout client non authentifié.

> **[CORRIGÉ 18/10/2026 — PREUVE]** L'affirmation antérieure « l'URL
> distante est invalide / le repo n'existe pas sur GitHub (404) » était
> FAUSSE. Preuves (jeton `gh` du compte Tagman45, scopes `repo`) :
> `gh api repos/Tagman45/doc-skill-xdna2` → `private: true`,
> `visibility: private`, `size: 9532`, `created_at 2026-10-14T08:29:25Z`,
> `pushed_at 2026-10-17T18:17:33Z`, `permissions.push: true` ;
> `git ls-remote origin` depuis le dépôt local →
> `546b2a3… refs/heads/main` (fetch OK). Le 404 est donc un artefact de
> visibilité, **pas** une absence de dépôt et **pas** une synchronisation
> perdue. État réel de synchro au 18/10/2026 : `doc-skill-xdna2` local
> `7e1a887` = **1 commit d'avance** sur `origin/main` (`546b2a3`) ;
> `investigator` local `3ddc089` = **2 commits d'avance** sur `origin/main`
> (`0fda41b`).

## B. R2 — état des miroirs / backups (non exécuté, état identifié)

| Objet | État | Vérification | Bilan |
|---|---|---|---|
| `team.db` / `bus` / `rag_index.json` | inchangés (aucun déplacement) | pas de mise à jour forcée | pas de double | registre local | 2026-09-01 |
| Base de preuves (EVD JSONL) | dans `doc-skill-xdna2-work/evidence/` | pas de déplacement, pas de recopie | pas de double | registre local | 2026-10-17 |
| Rapports d'EVD | dans `audits/<mission>/` | / | / | registre git-dédié | 2026-10-17 |
| 37 dépôts clones E:\trixdna_test\ | dont 18 récents `repos_*` + forks Atassis | **contenus non vérifiés** (SHA256) | **37 repos sans empreinte** | pas de miroir prouvé | 2026-09-01 |
| `repos_openflowlm_next` = fork interdite | `repos_openflowlm_next` | / | / | pas de push partout | 2026-10-17 |

**R2 conclut** : la migration E:\(HDD USB 5MB/s) vers C:\(NVMe) reste non
effectuée (aucune action déclenchée par la mission). Les miroirs *réels* sont
les **deux** dépôts distants : `investigator` (public) et `doc-skill-xdna2`
(**privé**) — ce dernier a été vérifié authentifié le 18/10/2026.
**[CORRIGÉ 18/10/2026]** La « cause du 404 à déterminer » est levée :
visibilité privée du dépôt (voir tableau A). Reste ouvert, non traité ici :
l'avance locale non poussée (1 commit sur `doc-skill-xdna2`, 2 sur
`investigator`), faute d'autorisation de push dans cette session.

## C. States / registres de preuves (matrice d'attribution)

| Règle | Qui la respecte | Comment le vérifier |
|---|---|---|
| Aucun push sans autorisation expresse | Skill universal, team-daemon, tools/auto_commit_push.py | `git log origin/main --since` (pas de nouveau commit) |
| Mission cartographe : 0 push | commits 7e1a887 / 3ddc089 locaux | `git status --short --branch` |
| DAP : l'agent ne supprime pas la source | tests test_cartographer.py | 110/110 |
| MOINS : ne pas confondre dépôt local et dépôt remote | LIMITS.md section B | table ci-dessus |

## D. Preuves croisées consultées (références)

- `RAPPORT_REA_CARTOGRAPHE_2026-10-17.md` (M4, bornes)
- `LIMITS.md` (R1 / R2 de cette annex)
- `CROISE_ANNEXE_MD.md` (cette page)
- `INDEX.md` (mission M5 pour l'ouverture)
- `audits/cartographer-20261017-2030/audit/AUDIT.md` (page 1 : historique
  des commits 86/86 + spécialisations)
- `audits/cartographer-20261017-2030/audit/GAP_MATRIX.md` (plusieurs items)
- `audits/cartographer-20261017-2030/audit/PLAN.md` (étapes 1-10)

## État de l'environnement (17/10/2026)

- Windows 10/11, amd64, PowerShell 5.1 + bash. `python3` = miniconda3 (3.13).
- Kernel : amd64, RAM libre ~2.8 Go. Aucun service réseau pour l'EVD.
