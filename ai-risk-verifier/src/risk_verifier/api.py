import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

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


async def reconcile_memories_forever(
    repository: EvidenceRepository, interval_seconds: float
) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            stored = await repository.backfill_memories()
            if stored:
                logger.info("Reconciled %s reviewed case(s) into Qdrant memory", stored)
        except RepositoryUnavailableError:
            logger.warning("Reviewed-case memory reconciliation will retry later")

DEFAULT_POLICIES = [
    PolicyRequest(
        policy_id="POLICY-RING-CORROBORATION-001",
        title="Corroborated abuse-ring intervention",
        text=(
            "Hold a payment when elevated structural risk is corroborated by at least one "
            "independent indicator such as a shared device, shared payment instrument, "
            "many-to-one beneficiary flow, rapid coordination, or a similar confirmed case. "
            "A shared IP address by itself is insufficient because legitimate networks may be "
            "used by many customers."
        ),
        minimum_action=Decision.HOLD,
        threshold=0.75,
        priority=950,
        tags=["shared_device", "shared_instrument", "mule_fan_in", "ring", "corroboration"],
        source_name="RBI Digital Payment Security Controls",
        source_url="https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12032&Mode=0",
        source_date="2021-02-18",
        source_section="Fraud Risk Management, paragraphs 36-39",
    ),
    PolicyRequest(
        policy_id="POLICY-VELOCITY-CONTEXT-001",
        title="Contextual velocity and behavioural monitoring",
        text=(
            "Route elevated velocity, beneficiary rotation, new-account activity, unusual "
            "location or IP origin, repeated authentication failure, or declined-payment bursts "
            "to review. Escalate only when the signal is material or corroborated, and compare "
            "the activity with the customer's established behaviour."
        ),
        minimum_action=Decision.REVIEW,
        threshold=0.6,
        priority=850,
        tags=["velocity", "temporal", "beneficiary_rotation", "novel_ip", "authentication"],
        source_name="RBI Digital Payment Security Controls",
        source_url="https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12032&Mode=0",
        source_date="2021-02-18",
        source_section="Fraud Risk Management, paragraph 37",
    ),
    PolicyRequest(
        policy_id="POLICY-AMOUNT-SPLITTING-001",
        title="Multi-source amount-splitting response",
        text=(
            "Hold and investigate when multiple apparently separate customers send a material "
            "aggregate value to one beneficiary through coordinated smaller payments within a "
            "short window. Require evidence of multiple sources, temporal coordination, and "
            "aggregate value; do not classify an isolated small payment as abuse."
        ),
        minimum_action=Decision.HOLD,
        threshold=0.78,
        priority=925,
        tags=["amount_splitting", "multi_source", "fragmentation", "beneficiary", "graph"],
        source_name="RiskLens internal control informed by RBI monitoring parameters",
        source_url="https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12032&Mode=0",
        source_date="2021-02-18",
        source_section="Fraud Risk Management, paragraphs 36-38",
    ),
    PolicyRequest(
        policy_id="POLICY-REALTIME-ALERT-001",
        title="Real-time alert and analyst resolution",
        text=(
            "Generate a review case for suspicious transactional behaviour in real time or near "
            "real time. Preserve the transaction, model dimensions, evidence, recommendation, "
            "analyst identity, decision, comment, and timestamps so the response is auditable."
        ),
        minimum_action=Decision.REVIEW,
        threshold=0.6,
        priority=800,
        tags=["realtime", "alert", "analyst", "audit", "case_management"],
        source_name="RBI Cyber Resilience and Digital Payment Security Controls for non-bank PSOs",
        source_url="https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12715&Mode=0",
        source_date="2024-07-30",
        source_section="Security Incident Response and Fraud Monitoring",
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
        source_name="RiskLens internal model-risk control",
        source_date="2026-08-31",
        source_section="Evidence and human-oversight guardrail",
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
        application.state.verifier = RiskVerifier(
            selected,
            confirmed_case_threshold=app_settings.confirmed_case_similarity_threshold,
            false_positive_threshold=app_settings.false_positive_similarity_threshold,
        )
        if app_settings.seed_default_policies:
            for policy in DEFAULT_POLICIES:
                try:
                    await selected.store_policy(policy)
                except RepositoryUnavailableError:
                    logger.warning("Default policy seed deferred because Qdrant is unavailable")
                    break
        reconciliation_task: asyncio.Task[None] | None = None
        if app_settings.backfill_reviewed_cases:
            try:
                stored = await selected.backfill_memories()
                logger.info("Backfilled %s reviewed case(s) into Qdrant memory", stored)
            except RepositoryUnavailableError:
                logger.warning(
                    "Reviewed-case memory backfill deferred because a store is unavailable"
                )
            reconciliation_task = asyncio.create_task(
                reconcile_memories_forever(
                    selected, app_settings.memory_reconciliation_interval_seconds
                )
            )
        try:
            yield
        finally:
            if reconciliation_task is not None:
                reconciliation_task.cancel()
                with suppress(asyncio.CancelledError):
                    await reconciliation_task
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
