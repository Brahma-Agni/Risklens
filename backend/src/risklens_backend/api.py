from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .database import ConflictError, NotFoundError, Repository
from .models import (
    AnalystAction,
    AnalystDecision,
    AnalystDecisionRequest,
    RiskCaseDetail,
    RiskCaseStatus,
    RiskCaseSummary,
    RiskSeverity,
    TransactionDetail,
    TransactionRequest,
    TransactionResponse,
)
from .services import RiskClients

Limit = Annotated[int, Query(ge=1, le=500)]


def create_app(
    settings: Settings | None = None,
    repository: Repository | None = None,
    clients: RiskClients | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app_repository = repository or Repository(app_settings.backend_database_url)
    app_clients = clients or RiskClients(
        app_settings.risk_service_url,
        app_settings.verifier_url,
        app_settings.backend_request_timeout_seconds,
        app_settings.verifier_api_key,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        app_clients.close()

    app = FastAPI(
        title="RiskLens Backend",
        version="0.2.0",
        description="Pydantic-validated payment ingestion and analyst case management.",
        lifespan=lifespan,
    )
    app.state.repository = app_repository
    app.state.clients = app_clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def repo(request: Request) -> Repository:
        return request.app.state.repository

    def service_clients(request: Request) -> RiskClients:
        return request.app.state.clients

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, error: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        return {"status": "UP", "service": app_settings.service_name}

    @app.get("/health/ready", tags=["health"])
    def ready(
        selected_repo: Repository = Depends(repo),
        selected_clients: RiskClients = Depends(service_clients),
    ) -> JSONResponse:
        dependencies = {
            "postgres": selected_repo.health(),
            "riskService": selected_clients.health(),
        }
        is_ready = all(dependencies.values())
        return JSONResponse(
            status_code=200 if is_ready else 503,
            content={"status": "UP" if is_ready else "DEGRADED", "dependencies": dependencies},
        )

    @app.post(
        "/api/v1/transactions",
        response_model=TransactionResponse,
        response_model_by_alias=True,
        status_code=status.HTTP_201_CREATED,
        tags=["transactions"],
    )
    def create_transaction(
        payload: TransactionRequest,
        selected_repo: Repository = Depends(repo),
        selected_clients: RiskClients = Depends(service_clients),
    ) -> TransactionResponse:
        selected_repo.insert_transaction(payload)
        evaluation = selected_clients.evaluate(payload)
        if evaluation is None:
            selected_repo.mark_risk_unavailable(payload.transaction_id)
            return TransactionResponse(
                transaction_id=payload.transaction_id,
                status="RISK_UNAVAILABLE",
                recommended_action="REVIEW",
                risk_service_available=False,
            )
        case_id = selected_repo.store_evaluation(
            payload, evaluation, app_settings.backend_review_threshold
        )
        return TransactionResponse(
            transaction_id=payload.transaction_id,
            status=evaluation.decision,
            recommended_action=evaluation.decision,
            risk_score=evaluation.overall_risk,
            case_id=case_id,
            risk_service_available=True,
        )

    @app.get(
        "/api/v1/transactions",
        response_model=list[TransactionDetail],
        response_model_by_alias=True,
        tags=["transactions"],
    )
    def transactions(limit: Limit = 100, selected_repo: Repository = Depends(repo)):
        return selected_repo.list_transactions(limit)

    @app.get(
        "/api/v1/transactions/{transaction_id}",
        response_model=TransactionDetail,
        response_model_by_alias=True,
        tags=["transactions"],
    )
    def transaction(transaction_id: str, selected_repo: Repository = Depends(repo)):
        return selected_repo.get_transaction(transaction_id)

    @app.get(
        "/api/v1/accounts/{account_id}/transactions",
        response_model=list[TransactionDetail],
        response_model_by_alias=True,
        tags=["transactions"],
    )
    def account_transactions(
        account_id: str, limit: Limit = 100, selected_repo: Repository = Depends(repo)
    ):
        return selected_repo.list_transactions(limit, account_id)

    @app.get(
        "/api/v1/risk-cases",
        response_model=list[RiskCaseSummary],
        response_model_by_alias=True,
        tags=["cases"],
    )
    def cases(
        limit: Limit = 100,
        case_status: RiskCaseStatus | None = Query(default=None, alias="status"),
        severity: RiskSeverity | None = None,
        selected_repo: Repository = Depends(repo),
    ):
        return selected_repo.list_cases(
            limit,
            case_status.value if case_status else None,
            severity.value if severity else None,
        )

    @app.get(
        "/api/v1/risk-cases/high-risk-linked",
        response_model=list[RiskCaseSummary],
        response_model_by_alias=True,
        tags=["cases"],
    )
    def linked_cases(limit: Limit = 100, selected_repo: Repository = Depends(repo)):
        return selected_repo.list_cases(
            limit, linked_only=True, review_threshold=app_settings.backend_review_threshold
        )

    @app.get(
        "/api/v1/risk-cases/{case_id}",
        response_model=RiskCaseDetail,
        response_model_by_alias=True,
        tags=["cases"],
    )
    def case(case_id: str, selected_repo: Repository = Depends(repo)):
        return selected_repo.get_case(case_id)

    @app.post(
        "/api/v1/risk-cases/{case_id}/decision",
        response_model=AnalystDecision,
        response_model_by_alias=True,
        status_code=status.HTTP_201_CREATED,
        tags=["cases"],
    )
    def decide(
        case_id: str,
        payload: AnalystDecisionRequest,
        background_tasks: BackgroundTasks,
        selected_repo: Repository = Depends(repo),
        selected_clients: RiskClients = Depends(service_clients),
    ):
        decision, memory = selected_repo.decide(case_id, payload)
        background_tasks.add_task(selected_clients.store_memory, memory)
        return decision

    @app.get(
        "/api/v1/analyst-actions",
        response_model=list[AnalystAction],
        response_model_by_alias=True,
        tags=["cases"],
    )
    def actions(limit: Limit = 100, selected_repo: Repository = Depends(repo)):
        return selected_repo.list_actions(limit)

    return app
