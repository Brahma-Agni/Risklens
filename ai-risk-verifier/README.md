# RiskLens AI Risk Verifier

The verifier is the evidence-grounded second pass for RiskLens risk decisions.
It does not replace the scoring service. It checks a proposed decision against
machine-readable signals, retrieved policies, and resolved analyst cases before
accepting or escalating the action.

## Guarantees

- Never silently downgrades a proposed action.
- Routes missing evidence, low confidence, and retrieval failures to review.
- Returns the policies and historical cases used as citations.
- Uses deterministic local hashing embeddings, so development and tests do not
  require an external model or API key.
- Stores resolved case memory in PostgreSQL and Qdrant using idempotent IDs.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health/live` | Process liveness |
| `GET` | `/health/ready` | PostgreSQL and Qdrant readiness |
| `POST` | `/api/v1/verify` | Verify a proposed risk decision |
| `POST` | `/api/v1/memory/cases` | Index a resolved analyst case |
| `PUT` | `/api/v1/policies/{policy_id}` | Create or replace a policy |
| `GET` | `/docs` | OpenAPI explorer |

Protected endpoints require `X-API-Key` only when `VERIFIER_API_KEY` is set.

### Example verification

```bash
curl -X POST http://localhost:8090/api/v1/verify \
  -H 'Content-Type: application/json' \
  -d '{
    "transaction_id":"TX-001",
    "account_id":"USER-001",
    "proposed_decision":"ALLOW",
    "proposed_recommendation":"Allow payment",
    "confidence":0.82,
    "dimensions":{"transaction":0.91,"structural":0.88,"ring":0.94},
    "signals":[{
      "type":"SHARED_DEVICE",
      "source":"GRAPH",
      "score":0.96,
      "description":"Eight accounts share one device",
      "evidence":{"linked_accounts":8}
    }]
  }'
```

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
python -m risk_verifier.main
```

The existing database initialization creates the required
`fraud_case_memory`, `risk_case_memory`, and `risk_policies` stores. Default
governance policies are idempotently seeded when the service starts.
