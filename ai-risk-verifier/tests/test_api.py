from fastapi.testclient import TestClient

from risk_verifier.api import create_app
from risk_verifier.config import Settings
from risk_verifier.repository import InMemoryEvidenceRepository


def test_health_and_verification_api() -> None:
    app = create_app(
        settings=Settings(api_key="test-secret", seed_default_policies=False),
        repository=InMemoryEvidenceRepository(),
    )
    payload = {
        "transaction_id": "TX-API-001",
        "account_id": "ACC-001",
        "proposed_decision": "ALLOW",
        "proposed_recommendation": "Allow",
        "confidence": 0.9,
        "dimensions": {"transaction": 0.93, "structural": 0.9, "ring": 0.95},
        "signals": [
            {
                "type": "SHARED_DEVICE",
                "source": "GRAPH",
                "score": 0.96,
                "description": "Shared by eight accounts",
            }
        ],
    }
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").json()["status"] == "UP"
        assert client.post("/api/v1/verify", json=payload).status_code == 401
        response = client.post("/api/v1/verify", json=payload, headers={"X-API-Key": "test-secret"})

    assert response.status_code == 200
    assert response.json()["final_decision"] == "HOLD"
    assert response.headers["x-request-id"]


def test_request_requires_evidence() -> None:
    app = create_app(
        settings=Settings(seed_default_policies=False),
        repository=InMemoryEvidenceRepository(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/verify",
            json={
                "transaction_id": "TX-EMPTY",
                "account_id": "ACC-001",
                "proposed_decision": "ALLOW",
                "proposed_recommendation": "Allow",
                "confidence": 0.9,
                "dimensions": {},
                "signals": [],
            },
        )
    assert response.status_code == 422
