from fastapi.testclient import TestClient

from risk_service.api import create_app
from risk_service.config import Settings
from risk_service.orchestrator import RiskOrchestrator

from .fakes import FakeEngineStore, FakeHistory, FakeVerifier, historical


def test_api_returns_backend_camel_case_contract() -> None:
    service = RiskOrchestrator(
        settings=Settings(require_verifier=True),
        history_store=FakeHistory([historical()]),
        graph_store=FakeEngineStore(),
        similarity_store=FakeEngineStore(),
        verifier=FakeVerifier(),
    )
    app = create_app(settings=Settings(require_verifier=True), orchestrator=service)
    payload = {
        "transactionId": "TX-API-001",
        "senderId": "USER-001",
        "receiverId": "MERCHANT-001",
        "amount": 1500,
        "currency": "INR",
        "deviceId": "DEV-001",
        "ipAddress": "10.0.0.1",
        "paymentMethod": "UPI",
        "timestamp": "2026-01-01T00:10:00Z",
    }
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        response = client.post("/api/v1/risk/evaluate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "ALLOW"
    assert "transactionRisk" in body
    assert "ringRisk" in body
    assert body["signals"][-1]["type"] == "AI_VERIFICATION"


def test_api_rejects_invalid_transaction() -> None:
    service = RiskOrchestrator(
        settings=Settings(),
        history_store=FakeHistory(),
        graph_store=FakeEngineStore(),
        similarity_store=FakeEngineStore(),
        verifier=FakeVerifier(),
    )
    app = create_app(settings=Settings(), orchestrator=service)
    with TestClient(app) as client:
        response = client.post("/api/v1/risk/evaluate", json={"amount": -1})
    assert response.status_code == 422
