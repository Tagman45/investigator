# Bilan du moteur d'investigation

```json
{
  "per_claim": [
    {
      "claim": "Tagman45/doc-skill-xdna2 est accessible en lecture (credentials locaux) et origin/main = 417ebfd3c9bd",
      "status": "CONFIRMED",
      "essential": true
    },
    {
      "claim": "Tagman45/investigator est accessible en lecture et origin/main = ec5e452e5f9a",
      "status": "CONFIRMED",
      "essential": true
    }
  ],
  "global_status": "CONFIRMED",
  "pending_essential": [],
  "limits": [],
  "step_compliance": {
    "done": {
      "analyze_request": 1,
      "external_search": 2,
      "verify_source": 2,
      "cross_check": 1,
      "coverage_eval": 1
    },
    "missing": {},
    "unknown_steps": [],
    "recorded_searches": [
      {
        "tool": "git ls-remote",
        "query": "HEAD distant doc-skill-xdna2"
      },
      {
        "tool": "git ls-remote",
        "query": "HEAD distant investigator"
      }
    ],
    "network_allowed": true
  },
  "network_allowed": true,
  "profile": "standard",
  "status_reasons": [],
  "close": {
    "decision": "VERIFIED",
    "refused_because": null
  }
}
```
