# Bilan du moteur d'investigation

```json
{
  "per_claim": [
    {
      "claim": "La tour Eiffel a été inaugurée le 31 mars 1889 (jour d'achèvement du chantier).",
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
      "external_search": 3,
      "verify_source": 5,
      "cross_check": 2,
      "coverage_eval": 1
    },
    "missing": {},
    "unknown_steps": [],
    "recorded_searches": [
      {
        "tool": "web_search (google)",
        "query": "tour Eiffel inaugurée 1889 date inauguration 31 mars"
      },
      {
        "tool": "web_search (google)",
        "query": "Eiffel Tower inauguration day March 31 1889 Gustave Eiffel official"
      },
      {
        "tool": "web_search (google)",
        "query": "tower Eiffel opening date public May 6 1889 universal exposition"
      }
    ],
    "network_allowed": true
  },
  "network_allowed": true,
  "profile": "deep",
  "status_reasons": [],
  "close": {
    "decision": "VERIFIED",
    "refused_because": null
  }
}
```
