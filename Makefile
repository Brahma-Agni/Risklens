.PHONY: setup stack-up stack-down stack-check infra-up infra-down infra-status infra-logs infra-check infra-reset backend-test backend-up backend-logs backend-down verifier-test verifier-up verifier-logs verifier-down data-test data-generate data-stream evaluation-test evaluate risk-test risk-up risk-logs risk-down

setup:
	@test -f .env || cp .env.example .env
	@echo "Local environment is ready. Review .env before non-development use."

stack-up:
	docker compose up -d --build --wait

stack-down:
	docker compose down

stack-check:
	@backend_port=$$(docker compose port backend 8080 | sed 's/.*://'); \
		curl --fail --silent "http://localhost:$${backend_port}/actuator/health" >/dev/null
	@risk_port=$$(docker compose port risk-service 8000 | sed 's/.*://'); \
		curl --fail --silent "http://localhost:$${risk_port}/health/ready" >/dev/null
	@verifier_port=$$(docker compose port ai-risk-verifier 8090 | sed 's/.*://'); \
		curl --fail --silent "http://localhost:$${verifier_port}/health/ready" >/dev/null
	@frontend_port=$$(docker compose port frontend-dashboard 3000 | sed 's/.*://'); \
		curl --fail --silent "http://localhost:$${frontend_port}" >/dev/null
	@echo "All application services are reachable."

infra-up:
	docker compose up -d --wait postgres neo4j qdrant
	docker compose up --no-deps neo4j-init qdrant-init

infra-down:
	docker compose down

infra-status:
	docker compose ps

infra-logs:
	docker compose logs -f postgres neo4j qdrant neo4j-init qdrant-init

infra-check:
	@docker compose exec -T postgres sh -c 'pg_isready -U "$${POSTGRES_USER}" -d "$${POSTGRES_DB}"'
	@neo4j_port=$$(docker compose port neo4j 7474 | sed 's/.*://'); \
		curl --fail --silent "http://localhost:$${neo4j_port}" >/dev/null
	@qdrant_port=$$(docker compose port qdrant 6333 | sed 's/.*://'); \
		curl --fail --silent "http://localhost:$${qdrant_port}/healthz"
	@echo
	@echo "All database endpoints are healthy."

# Destructive: removes all local database volumes and recreates them on next up.
infra-reset:
	docker compose down --volumes

backend-test:
	cd backend && mvn test

backend-up:
	docker compose up -d --build --wait backend

backend-logs:
	docker compose logs -f backend

backend-down:
	docker compose stop backend

verifier-test:
	cd ai-risk-verifier && python -m pytest

verifier-up:
	docker compose up -d --build --wait ai-risk-verifier

verifier-logs:
	docker compose logs -f ai-risk-verifier

verifier-down:
	docker compose stop ai-risk-verifier

data-test:
	cd data-generator && python -m pytest

data-generate:
	docker compose run --rm data-generator generate --count 1000 --abuse-rate 0.15 --output /app/output

data-stream:
	docker compose run --rm data-generator stream --input /app/output/transactions.jsonl

evaluation-test:
	cd evaluation && python -m pytest

evaluate:
	docker compose run --rm evaluation

risk-test:
	cd risk-service && python -m pytest

risk-up:
	docker compose up -d --build --wait risk-service

risk-logs:
	docker compose logs -f risk-service

risk-down:
	docker compose stop risk-service
