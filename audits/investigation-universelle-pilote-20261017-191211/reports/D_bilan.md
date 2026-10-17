# Bilan du moteur d'investigation

```json
{
  "per_claim": [
    {
      "claim": "Le papier 'Attention Is All You Need' est arXiv:1706.03762 (Vaswani et al., 2017) — page HuggingFace associée non ouverte.",
      "status": "PARTIALLY_CONFIRMED",
      "essential": true
    }
  ],
  "global_status": "PARTIALLY_CONFIRMED",
  "pending_essential": [
    "Le papier 'Attention Is All You Need' est arXiv:1706.03762 (Vaswani et al., 2017) — page HuggingFace associée non ouverte."
  ],
  "limits": [],
  "step_compliance": {
    "done": {
      "analyze_request": 1,
      "external_search": 2,
      "verify_source": 2,
      "cross_check": 1,
      "coverage_eval": 2
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
    "decision": "PARTIAL",
    "qualification": "Page HuggingFace https://huggingface.co/papers/1706.03762 vue dans les résultats mais jamais ouverte : 1 source accessible non vérifiée sur 3",
    "refused_because": null,
    "note": "rapport PARTIEL explicitement qualifié — JAMAIS présenté comme entièrement vérifié"
  }
}
```
