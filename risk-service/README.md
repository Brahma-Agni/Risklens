# RiskLens risk service

The risk service is the real-time scoring and orchestration layer called by the
Spring Boot backend. It combines independent transaction, account, behavioral,
temporal, graph, similarity, and evidence-verification signals into one decision.

## Evaluation flow

1. Read sender history from PostgreSQL, excluding the transaction under review.
2. Score amount deviation, device/IP novelty, adverse history, velocity, and
   beneficiary rotation.
3. Upsert entity relationships into Neo4j and measure coordinated clusters.
4. Retrieve similar confirmed cases from Qdrant.
5. Produce a deterministic proposal and send its evidence to the AI verifier.
6. Return the exact camel-case response expected by the Java backend.

PostgreSQL is required. Neo4j and Qdrant degrade independently and add explicit
unavailable signals. When `RISK_REQUIRE_VERIFIER=true`, a verifier outage
withholds automated allow decisions and routes them to review.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/risk/evaluate` | Evaluate a payment |
| `GET` | `/health/live` | Process liveness |
| `GET` | `/health/ready` | Dependency readiness |
| `GET` | `/docs` | OpenAPI explorer |

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
python -m risk_service.main
```

## Docker

From the repository root:

```bash
make risk-test
make risk-up
curl http://localhost:8000/health/ready
```

After the service is healthy, new backend transactions receive real risk scores,
decisions, evidence signals, and cases instead of `RISK_UNAVAILABLE`.
