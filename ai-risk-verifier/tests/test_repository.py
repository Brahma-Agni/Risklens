import httpx
import pytest

from risk_verifier.embedding import HashingEmbedder
from risk_verifier.repository import QdrantEvidenceRepository


@pytest.mark.asyncio
async def test_search_retrieves_policies_and_historical_cases() -> None:
    requested_collections: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        collection = request.url.path.split("/")[2]
        requested_collections.append(collection)
        if collection == "risk_policies":
            payload = {
                "reference_id": "POLICY-RING-001",
                "title": "Ring policy",
                "text": "Hold corroborated coordinated abuse rings.",
                "minimum_action": "HOLD",
                "threshold": 0.75,
            }
            score = 0.91
        else:
            payload = {
                "reference_id": "CASE-REVIEWED-001",
                "case_summary": "Confirmed shared-device abuse ring.",
                "final_label": "CONFIRMED_ABUSE",
            }
            score = 0.88
        return httpx.Response(
            200,
            json={"result": [{"id": "point-1", "score": score, "payload": payload}]},
        )

    repository = QdrantEvidenceRepository(
        qdrant_url="http://qdrant.test",
        database_url="postgresql://unused",
        embedder=HashingEmbedder(384),
        api_key=None,
        timeout=1,
        limit=5,
        score_threshold=0.08,
    )
    await repository.client.aclose()
    repository.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        evidence = await repository.search("shared device coordinated ring")
    finally:
        await repository.close()

    assert set(requested_collections) == {"risk_policies", "risk_case_memory"}
    assert [item.kind for item in evidence] == ["policy", "case"]
    assert evidence[0].metadata["collection"] == "risk_policies"
    assert evidence[1].metadata["collection"] == "risk_case_memory"
