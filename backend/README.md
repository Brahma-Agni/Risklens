# RiskLens backend

The backend is the payment-facing Spring Boot API and PostgreSQL system-of-record
gateway. It persists every accepted request before asking the internal risk
service for an evaluation.

## Run locally

Start PostgreSQL from the repository root, then run the application:

```bash
make infra-up
cd backend
mvn spring-boot:run
```

The default local database URL uses port `5434`, matching this workspace's
`.env`. Override `DATABASE_URL`, `DATABASE_USER`, and `DATABASE_PASSWORD` when
needed.

## APIs

- `POST /api/v1/transactions`
- `GET /api/v1/transactions/{transactionId}`
- `GET /api/v1/transactions?limit=100`
- `GET /api/v1/accounts/{accountId}/transactions`
- `GET /api/v1/risk-cases`
- `GET /api/v1/risk-cases/{caseId}`
- `POST /api/v1/risk-cases/{caseId}/decision`
- `GET /actuator/health`

If the FastAPI risk service is unavailable, the transaction is retained with
`RISK_UNAVAILABLE` and the response recommends `REVIEW`. The backend never turns
an unavailable risk decision into an implicit allow.
