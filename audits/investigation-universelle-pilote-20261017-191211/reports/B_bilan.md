# Bilan du moteur d'investigation

```json
{
  "per_claim": [
    {
      "claim": "Le papier 'Attention Is All You Need' est arXiv:1706.03762, auteurs Vaswani et 7 autres, soumis 12 juin 2017 (v7 du 2023-08-02).",
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
        "tool": "web_search (google)",
        "query": "Attention Is All You Need arXiv 1706.03762 Vaswani 2017"
      },
      {
        "tool": "read_url",
        "query": "arxiv.org/abs/1706.03762 (source primaire)"
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
