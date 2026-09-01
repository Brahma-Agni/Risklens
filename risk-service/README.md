# RiskLens risk service

The risk service is the real-time scoring and orchestration layer called by the
Spring Boot backend. It combines independent transaction, account, behavioral,
temporal, graph, similarity, and evidence-verification signals into one decision.

## Evaluation flow

1. Read sender history from PostgreSQL, excluding the transaction under review.
2. Score robust amount deviation, device/IP/payment-instrument novelty,
   lifecycle failures, velocity, beneficiary rotation, and same-beneficiary
   amount splitting.
3. Upsert time-bounded entity relationships into Neo4j and measure shared
   devices, shared instruments, many-to-one flows, and multi-source splitting.
4. Retrieve similar confirmed cases from Qdrant.
5. Produce a deterministic proposal and send its evidence to the AI verifier.
6. Return the exact camel-case response expected by the Java backend.

PostgreSQL is required. Neo4j and Qdrant degrade independently and add explicit
unavailable signals. When `RISK_REQUIRE_VERIFIER=true`, a verifier outage
withholds automated allow decisions and routes them to review.

Shared IP evidence is deliberately capped when it appears alone because mobile
carrier NAT, campuses, offices, and households can legitimately share an
address. Graph risk escalates when independent signals corroborate one another.

The behavioral thresholds can be tuned through `.env` using
`RISK_AMOUNT_DEVIATION_RATIO`, `RISK_VELOCITY_5M_THRESHOLD`,
`RISK_VELOCITY_1H_THRESHOLD`, `RISK_BENEFICIARY_ROTATION_5M_THRESHOLD`,
`RISK_FRAGMENT_AMOUNT_CEILING`, `RISK_FRAGMENT_COUNT_1H_THRESHOLD`, and
`RISK_FRAGMENT_TOTAL_1H_THRESHOLD`. Tune these values on a training/calibration
split; report final precision and recall only on the untouched held-out split.

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
