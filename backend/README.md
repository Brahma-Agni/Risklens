# RiskLens backend

This is the small public API in front of the RiskLens services. FastAPI exposes
the routes, Pydantic validates every request and response, and psycopg stores
transactions, cases, signals, and analyst decisions in PostgreSQL.

## Responsibilities

- Validate incoming payments with Pydantic.
- Persist the payment before requesting its risk score.
- Call the Python risk service and store the returned dimensions and signals.
- Expose the dashboard case queue and transaction details.
- Persist analyst decisions and send reviewed cases to the verifier's Qdrant memory.

It does not calculate fraud risk. That responsibility remains in `risk-service`.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[dev]'
pytest
uvicorn risklens_backend.api:create_app --factory --reload --port 8080
```

Interactive API documentation is available at <http://localhost:8080/docs>.

## Main routes

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/v1/transactions` | Validate, store, and score a payment |
| `GET` | `/api/v1/transactions` | List recent payments |
| `GET` | `/api/v1/risk-cases/high-risk-linked` | Dashboard investigation queue |
| `GET` | `/api/v1/risk-cases/{caseId}` | Case evidence and risk dimensions |
| `POST` | `/api/v1/risk-cases/{caseId}/decision` | Record the analyst outcome |
| `GET` | `/api/v1/analyst-actions` | List completed analyst actions |
| `GET` | `/health/ready` | PostgreSQL and risk-service readiness |
