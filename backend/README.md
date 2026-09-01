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

## Transaction ingestion contract

The required fields remain `transactionId`, `senderId`, `receiverId`, `amount`,
`currency`, `paymentMethod`, and `timestamp`. In the C2B dataset, `senderId` is
the synthetic customer ID and `receiverId` is the synthetic merchant ID.

The API also accepts the optional context fields `deviceId`, `ipAddress`,
`ipId`, `paymentInstrumentId`, `locationCity`, `locationState`,
`locationCountry`, `authorizationStatus`, `authenticationStatus`,
`transactionStatus`, `failureReason`, `merchantCategory`, and `context`.
Frequently queried fields have dedicated PostgreSQL columns; `context` is JSONB
for versioned experimental features. The original request is retained in
`raw_payload` for auditability.

Fraud labels, scenario names, and ground-truth ring IDs are intentionally not
accepted by this endpoint. They belong to the evaluation dataset and must not
be exposed to production risk scoring.

When an analyst resolves a case, the committed decision is preserved even if
the verifier is temporarily unavailable. After commit, the backend sends the
case label, risk dimensions, signal evidence, model summary, and analyst note to
`POST /api/v1/memory/cases`. The verifier stores an idempotent PostgreSQL memory
row and a Qdrant embedding so later risk decisions can retrieve similar
confirmed-abuse and false-positive cases.

The immediate delivery runs only after the analyst transaction commits. If it
cannot reach the verifier, the decision remains successful and the verifier's
periodic idempotent reconciliation retries persisted resolved cases.
