import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from risk_verifier.config import Settings, get_settings
from risk_verifier.embedding import HashingEmbedder
from risk_verifier.models import (
    Decision,
    MemoryCaseRequest,
    PolicyRequest,
    StoreResponse,
    VerifyRequest,
    VerifyResponse,
)
from risk_verifier.repository import (
    EvidenceRepository,
    QdrantEvidenceRepository,
    RepositoryUnavailableError,
    UnknownRiskCaseError,
)
from risk_verifier.verifier import RiskVerifier

logger = logging.getLogger(__name__)

DEFAULT_POLICIES = [
    PolicyRequest(
        policy_id="POLICY-SHARED-DEVICE-001",
        title="Shared device coordination",
        text=(
            "Transactions involving multiple recently created accounts sharing a device or IP "
            "must be held when structural or ring risk is elevated."
        ),
        minimum_action=Decision.HOLD,
        threshold=0.75,
        priority=900,
        tags=["device", "coordination", "ring"],
    ),
    PolicyRequest(
        policy_id="POLICY-VELOCITY-001",
        title="High-velocity payment attempts",
        text=(
            "Rapid repeated payments, beneficiary rotation, or amount stepping require analyst "
            "review and a temporary hold when risk exceeds the elevated threshold."
        ),
        minimum_action=Decision.HOLD,
        threshold=0.8,
        priority=800,
        tags=["velocity", "temporal", "beneficiary"],
    ),
    PolicyRequest(
        policy_id="POLICY-EVIDENCE-001",
        title="Minimum evidence requirement",
        text=(
            "No automated allow decision may be verified without corroborating risk dimensions "
            "and machine-readable signals. Missing evidence must route to manual review."
        ),
        minimum_action=Decision.ALLOW,
        threshold=0.0,
        priority=1000,
        tags=["evidence", "review", "governance"],
    ),
]


def create_repository(settings: Settings) -> QdrantEvidenceRepository:
    return QdrantEvidenceRepository(
        qdrant_url=settings.qdrant_url,
        database_url=settings.database_url,
        embedder=HashingEmbedder(settings.vector_size),
        api_key=settings.qdrant_api_key,
        timeout=settings.request_timeout_seconds,
        limit=settings.retrieval_limit,
        score_threshold=settings.retrieval_score_threshold,
    )


def create_app(
    *,
    settings: Settings | None = None,
    repository: EvidenceRepository | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    owned_repository = repository is None

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        selected = repository or create_repository(app_settings)
        application.state.repository = selected
        application.state.verifier = RiskVerifier(selected)
        if app_settings.seed_default_policies:
            for policy in DEFAULT_POLICIES:
                try:
                    await selected.store_policy(policy)
                except RepositoryUnavailableError:
                    logger.warning("Default policy seed deferred because Qdrant is unavailable")
                    break
        yield
        if owned_repository and isinstance(selected, QdrantEvidenceRepository):
            await selected.close()

    app = FastAPI(
        title="RiskLens AI Risk Verifier",
        version="0.1.0",
        description=(
            "Evidence-grounded second-pass verification for payment risk decisions, with "
            "policy and resolved-case citations."
        ),
        lifespan=lifespan,
    )

    async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if app_settings.api_key and x_api_key != app_settings.api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")

    def get_repository(request: Request) -> EvidenceRepository:
        return request.app.state.repository

    def get_verifier(request: Request) -> RiskVerifier:
        return request.app.state.verifier

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
        return response

    @app.exception_handler(RepositoryUnavailableError)
    async def repository_unavailable(_: Request, error: RepositoryUnavailableError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(error), "code": "EVIDENCE_STORE_UNAVAILABLE"},
        )

    @app.exception_handler(UnknownRiskCaseError)
    async def unknown_case(_: Request, error: UnknownRiskCaseError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(error), "code": "RISK_CASE_NOT_FOUND"},
        )

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "UP", "service": app_settings.service_name}

    @app.get("/health/ready", tags=["health"])
    async def ready(
        evidence_repository: EvidenceRepository = Depends(get_repository),
    ) -> JSONResponse:
        dependencies = await evidence_repository.health()
        ready_state = all(dependencies.values())
        return JSONResponse(
            status_code=status.HTTP_200_OK if ready_state else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "UP" if ready_state else "DEGRADED", "dependencies": dependencies},
        )

    @app.post(
        "/api/v1/verify",
        response_model=VerifyResponse,
        dependencies=[Depends(require_api_key)],
        tags=["verification"],
    )
    async def verify(
        payload: VerifyRequest,
        risk_verifier: RiskVerifier = Depends(get_verifier),
    ) -> VerifyResponse:
        return await risk_verifier.verify(payload)

    @app.post(
        "/api/v1/memory/cases",
        response_model=StoreResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_api_key)],
        tags=["memory"],
    )
    async def store_case(
        payload: MemoryCaseRequest,
        evidence_repository: EvidenceRepository = Depends(get_repository),
    ) -> StoreResponse:
        return await evidence_repository.store_memory(payload)

    @app.put(
        "/api/v1/policies/{policy_id}",
        response_model=StoreResponse,
        dependencies=[Depends(require_api_key)],
        tags=["policies"],
    )
    async def store_policy(
        policy_id: str,
        payload: PolicyRequest,
        evidence_repository: EvidenceRepository = Depends(get_repository),
    ) -> StoreResponse:
        if policy_id != payload.policy_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="path policy_id must match request policy_id",
            )
        return await evidence_repository.store_policy(payload)

    return app
