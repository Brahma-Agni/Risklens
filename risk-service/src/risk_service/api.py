import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from risk_service.config import Settings, get_settings
from risk_service.embedding import HashingEmbedder
from risk_service.models import RiskRequest, RiskResponse
from risk_service.orchestrator import RiskOrchestrator
from risk_service.services import (
    HttpVerificationClient,
    Neo4jGraphStore,
    PostgresHistoryStore,
    QdrantSimilarityStore,
    RequiredDependencyError,
)

logger = logging.getLogger(__name__)


def create_orchestrator(settings: Settings) -> RiskOrchestrator:
    return RiskOrchestrator(
        settings=settings,
        history_store=PostgresHistoryStore(settings.database_url),
        graph_store=Neo4jGraphStore(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        ),
        similarity_store=QdrantSimilarityStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            embedder=HashingEmbedder(settings.vector_size),
            timeout=settings.request_timeout_seconds,
            threshold=settings.similarity_threshold,
        ),
        verifier=HttpVerificationClient(
            settings.verifier_url, settings.verifier_api_key, settings.request_timeout_seconds
        ),
    )


def create_app(
    *, settings: Settings | None = None, orchestrator: RiskOrchestrator | None = None
) -> FastAPI:
    app_settings = settings or get_settings()
    owned = orchestrator is None

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        selected = orchestrator or create_orchestrator(app_settings)
        application.state.orchestrator = selected
        yield
        if owned:
            for component in (
                selected.graph_store,
                selected.similarity_store,
                selected.verifier,
            ):
                close = getattr(component, "close", None)
                if close:
                    await close()

    app = FastAPI(
        title="RiskLens Risk Service",
        version="0.1.0",
        description=(
            "Real-time payment risk orchestration across behavioral, temporal, graph, "
            "similarity, and evidence-verification engines."
        ),
        lifespan=lifespan,
    )

    async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if app_settings.api_key and x_api_key != app_settings.api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")

    def get_orchestrator(request: Request) -> RiskOrchestrator:
        return request.app.state.orchestrator

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
        return response

    @app.exception_handler(RequiredDependencyError)
    async def dependency_error(_: Request, error: RequiredDependencyError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(error), "code": "REQUIRED_DEPENDENCY_UNAVAILABLE"},
        )

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "UP", "service": app_settings.service_name}

    @app.get("/health/ready", tags=["health"])
    async def ready(
        selected: RiskOrchestrator = Depends(get_orchestrator),
    ) -> JSONResponse:
        dependencies = await selected.health()
        required_up = dependencies["postgres"] and (
            dependencies["verifier"] or not app_settings.require_verifier
        )
        all_up = all(dependencies.values())
        return JSONResponse(
            status_code=status.HTTP_200_OK if required_up else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "UP" if all_up else "DEGRADED", "dependencies": dependencies},
        )

    @app.post(
        "/api/v1/risk/evaluate",
        response_model=RiskResponse,
        response_model_by_alias=True,
        dependencies=[Depends(require_api_key)],
        tags=["risk"],
    )
    async def evaluate(
        payload: RiskRequest,
        selected: RiskOrchestrator = Depends(get_orchestrator),
    ) -> RiskResponse:
        return await selected.evaluate(payload)

    return app
