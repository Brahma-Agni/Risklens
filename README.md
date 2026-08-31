# RiskLens

RiskLens is a hackathon prototype for detecting coordinated payment abuse using
behavioral, temporal, graph, and semantic case-memory signals.

The repository includes the database infrastructure, Spring Boot API, and a
complete analyst dashboard for live monitoring and investigations.

## Repository layout

```text
.
├── backend/                 # Spring Boot payment-facing API
├── data-generator/          # Synthetic traffic and scenarios
├── risk-service/            # FastAPI risk orchestration and engines
├── ai-risk-verifier/        # Evidence-based verifier and retrieval
├── frontend-dashboard/      # React analyst dashboard
├── evaluation/              # Training/test metrics and reports
├── shared/                  # Shared contracts and documentation
├── database/
│   ├── postgres/init/       # Transactional schema and seed data
│   ├── neo4j/init/          # Graph constraints and indexes
│   └── qdrant/init/         # Vector collection initialization
├── docker-compose.yml
├── .env.example
└── Makefile
```

## Prerequisites

- Docker Engine 24 or newer
- Docker Compose v2
- `make` and `curl` for the convenience commands

## Start the database stack

```bash
make setup
make infra-up
make infra-status
make infra-check
```

`make setup` copies `.env.example` to the ignored `.env` file. The committed
Compose defaults are suitable only for local development. Change all passwords
before running on a shared host.

To build and start the complete application from the root `.env`:

```bash
make setup
make stack-up
make stack-check
```

Compose reads `.env` once as the configuration source for database credentials,
internal service URLs, exposed ports, risk thresholds, generator settings,
evaluation gates, CORS, and the dashboard's public API URL. Internal URLs use
Docker service names; browser-facing URLs use `localhost` and the exposed ports.
Changing `NEXT_PUBLIC_*` values requires rebuilding the dashboard image.

To build and start the Spring Boot gateway after the databases are running:

```bash
make backend-test
make backend-up
curl http://localhost:8080/actuator/health
```

### Local endpoints

| Service | Endpoint | Local credentials |
|---|---|---|
| PostgreSQL | `localhost:${POSTGRES_PORT}/risklens` | `risklens` / value of `POSTGRES_PASSWORD` |
| Neo4j Browser | `http://localhost:${NEO4J_HTTP_PORT}` | `neo4j` / value of `NEO4J_PASSWORD` |
| Neo4j Bolt | `bolt://localhost:${NEO4J_BOLT_PORT}` | same as above |
| Qdrant REST | `http://localhost:${QDRANT_HTTP_PORT}` | no local authentication |
| Qdrant gRPC | `localhost:${QDRANT_GRPC_PORT}` | no local authentication |
| Spring Boot API | `http://localhost:${BACKEND_PORT}` | no local authentication |
| RiskLens dashboard | `http://localhost:${FRONTEND_PORT}` | no local authentication |
| AI risk verifier | `http://localhost:${VERIFIER_PORT}` | optional `VERIFIER_API_KEY` |
| Risk scoring service | `http://localhost:${RISK_SERVICE_PORT}` | internal API |

Containers communicate using service names (`postgres`, `neo4j`, and `qdrant`)
on the `risklens-network` Docker network, not `localhost`.

## Initialization behavior

- PostgreSQL creates the runtime tables, indexes, and minimal demo reference
  records on the first creation of its volume.
- `neo4j-init` applies idempotent graph constraints after Neo4j is healthy.
- `qdrant-init` creates `risk_case_memory` and `risk_policies` collections after
  Qdrant is healthy.
- Synthetic ground-truth labels are deliberately excluded from all runtime
  schemas so they cannot leak into risk inference.

The initializer containers should exit successfully after setup. This is normal;
the three database containers remain running.

## Common commands

```bash
make infra-logs       # follow database and initializer logs
make infra-down       # stop containers and preserve data
make infra-up         # restart with preserved data
make infra-reset      # destructive: delete all database volumes
```

PostgreSQL entrypoint SQL only runs for a new volume. During schema development,
use migrations once application services are introduced. For this initial
milestone, run `make infra-reset && make infra-up` to deliberately rebuild local
development data from the initialization scripts.

## Backend behavior

The backend persists transaction requests to PostgreSQL and calls the internal
FastAPI risk service. Until that service is available, requests are retained as
`RISK_UNAVAILABLE` and explicitly recommend manual review. See
[`backend/README.md`](backend/README.md) for the implemented endpoints.

## Frontend dashboard

The dashboard includes overview metrics, a polling transaction monitor,
filterable risk-case queue, analyst decision workflow, entity graph, model
health charts, and a scenario simulator connected to the backend API.

For local development:

```bash
cd frontend-dashboard
npm ci
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` when the backend is not available at
`http://localhost:8080`. The interface clearly labels representative demo data
when the API or risk-case dataset is unavailable.

## AI risk verifier

The verifier performs an evidence-grounded second pass over proposed risk
decisions. It retrieves applicable policies and resolved analyst cases from
Qdrant, applies fail-safe decision guardrails, returns citations, and persists
resolved case memory to PostgreSQL and Qdrant.

```bash
make verifier-test
make verifier-up
curl http://localhost:8090/health/ready
```

See [`ai-risk-verifier/README.md`](ai-risk-verifier/README.md) for request
examples and the service contract.

## Synthetic data generation

The deterministic data generator creates normal payments plus shared-device
rings, velocity bursts, mule fan-in, and account-takeover scenarios. Backend
payloads and evaluation-only ground truth are always exported separately.

```bash
make data-generate
make data-stream
```

Generated files are written under `data-generator/output/`. See
[`data-generator/README.md`](data-generator/README.md) for scenario controls,
reproducibility options, and direct CLI usage.

## Risk scoring service

The FastAPI risk service combines PostgreSQL behavioral history, temporal
velocity, Neo4j entity coordination, Qdrant case similarity, and the evidence
verifier into the response consumed by the Spring Boot backend.

```bash
make risk-test
make risk-up
curl http://localhost:8000/health/ready
```

See [`risk-service/README.md`](risk-service/README.md) for the scoring flow and
degraded-dependency behavior.

## Evaluation

The offline evaluator joins generator labels to backend streaming results and
produces confusion-matrix metrics, precision, recall, F1, availability,
per-scenario metrics, and a score-threshold sweep. Ground truth remains outside
the runtime scoring path.

```bash
make evaluation-test
make evaluate
```

Reports are written under `evaluation/reports/`. Configure input paths,
positive decisions, score classification, and minimum quality gates using the
`EVALUATION_*` variables in `.env`. See
[`evaluation/README.md`](evaluation/README.md).

## Shared folder

`shared/` is not a service. It holds language-neutral JSON Schemas for the
transaction, risk response, generator result, and evaluation-label boundaries.
Java, Python, and TypeScript implementations stay within their own services;
the shared contracts provide one compatibility reference without coupling
their source code. See [`shared/README.md`](shared/README.md).
