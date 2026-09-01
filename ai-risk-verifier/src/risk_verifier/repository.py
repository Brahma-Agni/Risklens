import asyncio
import json
import uuid
from typing import Any, Protocol

import httpx
import psycopg

from risk_verifier.embedding import HashingEmbedder
from risk_verifier.models import EvidenceReference, MemoryCaseRequest, PolicyRequest, StoreResponse


class EvidenceRepository(Protocol):
    async def search(self, text: str) -> list[EvidenceReference]: ...

    async def store_memory(self, request: MemoryCaseRequest) -> StoreResponse: ...

    async def store_policy(self, request: PolicyRequest) -> StoreResponse: ...

    async def backfill_memories(self) -> int: ...

    async def health(self) -> dict[str, bool]: ...


class RepositoryUnavailableError(RuntimeError):
    pass


class UnknownRiskCaseError(ValueError):
    pass


class QdrantEvidenceRepository:
    def __init__(
        self,
        *,
        qdrant_url: str,
        database_url: str,
        embedder: HashingEmbedder,
        api_key: str | None,
        timeout: float,
        limit: int,
        score_threshold: float,
    ) -> None:
        self.qdrant_url = qdrant_url.rstrip("/")
        self.database_url = database_url
        self.embedder = embedder
        self.limit = limit
        self.score_threshold = score_threshold
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"api-key": api_key} if api_key else None,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def search(self, text: str) -> list[EvidenceReference]:
        vector = self.embedder.embed(text)
        try:
            policies, cases = await asyncio.gather(
                self._search_collection("risk_policies", "policy", vector),
                self._search_collection("risk_case_memory", "case", vector),
            )
        except httpx.HTTPError as error:
            raise RepositoryUnavailableError("Qdrant evidence retrieval is unavailable") from error
        # Keep the strongest result from each source near the front so the API
        # response remains visibly grounded in both policy and case memory.
        leaders = [items[0] for items in (policies, cases) if items]
        remaining = [*policies[1:], *cases[1:]]
        return leaders + sorted(remaining, key=lambda item: item.similarity, reverse=True)

    async def _search_collection(
        self, collection: str, kind: str, vector: list[float]
    ) -> list[EvidenceReference]:
        response = await self.client.post(
            f"{self.qdrant_url}/collections/{collection}/points/search",
            json={
                "vector": vector,
                "limit": self.limit,
                "score_threshold": self.score_threshold,
                "with_payload": True,
                "with_vector": False,
            },
        )
        response.raise_for_status()
        results = []
        for item in response.json().get("result", []):
            payload = item.get("payload") or {}
            reference_id = str(payload.get("reference_id") or item["id"])
            title = str(payload.get("title") or payload.get("final_label") or reference_id)
            excerpt = str(payload.get("text") or payload.get("case_summary") or "")[:1000]
            metadata = {
                key: value
                for key, value in payload.items()
                if key not in {"text", "case_summary"}
            }
            metadata["collection"] = collection
            results.append(
                EvidenceReference(
                    kind=kind,
                    reference_id=reference_id,
                    title=title,
                    excerpt=excerpt,
                    similarity=max(0.0, min(1.0, float(item.get("score", 0)))),
                    metadata=metadata,
                )
            )
        return sorted(results, key=lambda item: item.similarity, reverse=True)

    async def store_memory(self, request: MemoryCaseRequest) -> StoreResponse:
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"risklens:case:{request.risk_case_id}"))
        embedding_text = " ".join(
            [
                request.final_label.value,
                request.case_summary,
                json.dumps(request.feature_snapshot, sort_keys=True),
                json.dumps(request.evidence_snapshot, sort_keys=True),
            ]
        )
        vector = self.embedder.embed(embedding_text)
        payload = {
            "reference_id": request.risk_case_id,
            "title": f"Resolved case {request.risk_case_id}",
            "case_summary": request.case_summary,
            "final_label": request.final_label.value,
            "feature_snapshot": request.feature_snapshot,
            "evidence_snapshot": request.evidence_snapshot,
        }
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
                cursor = await connection.execute(
                    """
                    INSERT INTO fraud_case_memory (
                        risk_case_id, final_label, case_summary, feature_snapshot,
                        evidence_snapshot, qdrant_point_id
                    )
                    SELECT id, %s::analyst_decision_type, %s, %s::jsonb, %s::jsonb, %s::uuid
                    FROM risk_cases WHERE case_id = %s
                    ON CONFLICT (risk_case_id) DO UPDATE SET
                        final_label = EXCLUDED.final_label,
                        case_summary = EXCLUDED.case_summary,
                        feature_snapshot = EXCLUDED.feature_snapshot,
                        evidence_snapshot = EXCLUDED.evidence_snapshot,
                        qdrant_point_id = EXCLUDED.qdrant_point_id
                    """,
                    (
                        request.final_label.value,
                        request.case_summary,
                        json.dumps(request.feature_snapshot),
                        json.dumps(request.evidence_snapshot),
                        point_id,
                        request.risk_case_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise UnknownRiskCaseError(f"risk case {request.risk_case_id!r} does not exist")
                await self._upsert("risk_case_memory", point_id, vector, payload)
        except psycopg.Error:
            # Qdrant remains the online retrieval source. Database reconciliation can retry safely.
            raise
        return StoreResponse(reference_id=request.risk_case_id, point_id=point_id)

    async def store_policy(self, request: PolicyRequest) -> StoreResponse:
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"risklens:policy:{request.policy_id}"))
        payload = {
            "reference_id": request.policy_id,
            "title": request.title,
            "text": request.text,
            "minimum_action": request.minimum_action.value,
            "threshold": request.threshold,
            "priority": request.priority,
            "tags": request.tags,
            "source_name": request.source_name,
            "source_url": request.source_url,
            "source_date": request.source_date,
            "source_section": request.source_section,
        }
        embedding_text = " ".join([request.title, request.text, *request.tags])
        await self._upsert("risk_policies", point_id, self.embedder.embed(embedding_text), payload)
        return StoreResponse(reference_id=request.policy_id, point_id=point_id)

    async def backfill_memories(self) -> int:
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
                cursor = await connection.execute(
                    """
                    SELECT rc.case_id, decision.decision::text,
                           concat(
                               'Analyst resolved ', rc.case_id, ' as ',
                               decision.decision::text, '. ', coalesce(rc.ai_summary, ''),
                               CASE WHEN decision.comment IS NULL OR decision.comment = ''
                                   THEN '' ELSE ' Analyst note: ' || decision.comment END
                           ) AS case_summary,
                           jsonb_build_object(
                               'severity', rc.severity::text,
                               'transactionRisk', rc.transaction_risk,
                               'accountRisk', rc.account_risk,
                               'behaviorRisk', rc.behavior_risk,
                               'temporalRisk', rc.temporal_risk,
                               'structuralRisk', rc.structural_risk,
                               'similarityRisk', rc.similarity_risk,
                               'ringRisk', rc.ring_risk,
                               'confidence', rc.confidence
                           ) AS features,
                           coalesce(signals.items, '[]'::jsonb) AS evidence
                    FROM risk_cases rc
                    JOIN LATERAL (
                        SELECT ad.decision, ad.comment
                        FROM analyst_decisions ad
                        WHERE ad.risk_case_id = rc.id
                        ORDER BY ad.created_at DESC
                        LIMIT 1
                    ) decision ON true
                    LEFT JOIN LATERAL (
                        SELECT jsonb_agg(jsonb_build_object(
                            'type', rs.signal_type,
                            'source', rs.source_engine,
                            'score', rs.score,
                            'description', rs.description,
                            'evidence', rs.evidence
                        ) ORDER BY rs.created_at) AS items
                        FROM risk_signals rs
                        WHERE rs.risk_case_id = rc.id
                    ) signals ON true
                    WHERE rc.status = 'RESOLVED'::risk_case_status
                    """
                )
                rows = await cursor.fetchall()
        except psycopg.Error as error:
            raise RepositoryUnavailableError(
                "PostgreSQL reviewed-case backfill is unavailable"
            ) from error

        stored = 0
        for row in rows:
            await self.store_memory(
                MemoryCaseRequest(
                    risk_case_id=row[0],
                    final_label=row[1],
                    case_summary=row[2],
                    feature_snapshot=row[3] or {},
                    evidence_snapshot=row[4] or [],
                )
            )
            stored += 1
        return stored

    async def _upsert(
        self, collection: str, point_id: str, vector: list[float], payload: dict[str, Any]
    ) -> None:
        try:
            response = await self.client.put(
                f"{self.qdrant_url}/collections/{collection}/points",
                params={"wait": "true"},
                json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise RepositoryUnavailableError(
                f"Qdrant collection {collection!r} is unavailable"
            ) from error

    async def health(self) -> dict[str, bool]:
        qdrant = False
        postgres = False
        try:
            response = await self.client.get(f"{self.qdrant_url}/healthz")
            qdrant = response.is_success
        except httpx.HTTPError:
            pass
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
                result = await connection.execute("SELECT 1")
                postgres = (await result.fetchone()) == (1,)
        except psycopg.Error:
            pass
        return {"qdrant": qdrant, "postgres": postgres}


class InMemoryEvidenceRepository:
    def __init__(self, evidence: list[EvidenceReference] | None = None) -> None:
        self.evidence = evidence or []
        self.memories: dict[str, MemoryCaseRequest] = {}
        self.policies: dict[str, PolicyRequest] = {}

    async def search(self, text: str) -> list[EvidenceReference]:
        del text
        return self.evidence

    async def store_memory(self, request: MemoryCaseRequest) -> StoreResponse:
        self.memories[request.risk_case_id] = request
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"risklens:case:{request.risk_case_id}"))
        return StoreResponse(reference_id=request.risk_case_id, point_id=point_id)

    async def store_policy(self, request: PolicyRequest) -> StoreResponse:
        self.policies[request.policy_id] = request
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"risklens:policy:{request.policy_id}"))
        return StoreResponse(reference_id=request.policy_id, point_id=point_id)

    async def backfill_memories(self) -> int:
        return 0

    async def health(self) -> dict[str, bool]:
        return {"qdrant": True, "postgres": True}
