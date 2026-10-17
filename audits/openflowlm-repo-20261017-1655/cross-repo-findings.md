# Cross-repo findings (preuves locales, 2026-10-17)

## Faits corrélatables avec le reste du workspace
1. **OpenFlowLM-Next est le fork ouvert de la plateforme FastFlowLM** (README + docs, CONFIRMED_STATIC côté org : `Atomic-Germ/OpenFlowLM-Next` en origin). Cohérent avec le dossier du workspace : les conteneurs FLM officiels (`E:/flm/models/Qwen3.5-4B-NPU2`) travaillés aujourd'hui dans le ledger EVD-007/-008 viennent du même écosystème.
   - Lien croisé fort : EVD-20261017-007 a fait tourner le moteur `open_qwen36` (recette open de ce même repo) sur les kernels `Qwen3.5-4B-NPU2` exportés du runtime FLM officiel de la même famille.
2. **Stationing : même workspace, deux noms pour le package** : `repos_openflowlm_next` contient les skills `.agents/skills/` (commit #211), le work-dir desktop porte `skills/local/*` — nomenclature double à normaliser plus tard (analogie DECLARED, pas identique).
3. **L'API GitHub de cette machine est rate-limited sans token** (HTTP_403 5/5) — cela conditionne en amont TOUTE investigation GitHub future sur ce workspace.

## Ce qui n'est PAS une preuve
- Le diagramme Mermaid (`ecosystem-graph.mmd`) montre des relations déclarées ; il ne prouve aucun chemin d'exécution (règle du skill réaffichée).

## Renvois
- `RUNTIME_SANS_FLM.md` (workspace doc-skill) : liste des runtimes sans FLM validés avant le jour 2.7 — croisée une future partie avec les releases déclarées ici.
