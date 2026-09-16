from fastapi.testclient import TestClient

from risklens_backend.api import create_app
from risklens_backend.config import Settings
from risklens_backend.models import RiskEvaluation


class FakeRepository:
    def __init__(self) -> None:
        self.inserted = []

    def health(self) -> bool:
        return True

    def insert_transaction(self, payload) -> None:
        self.inserted.append(payload)

    def store_evaluation(self, payload, evaluation, review_threshold) -> str:
        assert review_threshold == 0.75
        return "CASE-1"


class FakeClients:
    def health(self) -> bool:
        return True

    def close(self) -> None:
        pass

    def evaluate(self, payload) -> RiskEvaluation:
        return RiskEvaluation(
            transactionRisk=0.8,
            accountRisk=0.2,
            behaviorRisk=0.3,
            temporalRisk=0.4,
            structuralRisk=0.9,
            similarityRisk=0.5,
            ringRisk=0.85,
            confidence=0.9,
            decision="HOLD",
            recommendation="Review linked activity",
            summary="Linked entities exceed the review threshold.",
            signals=[],
        )


def payment() -> dict:
    return {
        "transactionId": "TX-1",
        "senderId": "USER-1",
        "receiverId": "MERCHANT-1",
        "amount": 125.50,
        "currency": "INR",
        "deviceId": "DEVICE-1",
        "ipAddress": "10.0.0.1",
        "paymentMethod": "UPI",
        "timestamp": "2026-09-16T10:00:00Z",
    }


def test_transaction_contract_stays_compatible() -> None:
    repository = FakeRepository()
    app = create_app(Settings(), repository, FakeClients())

    with TestClient(app) as client:
        response = client.post("/api/v1/transactions", json=payment())

    assert response.status_code == 201
    assert response.json() == {
        "transactionId": "TX-1",
        "status": "HOLD",
        "recommendedAction": "HOLD",
        "riskScore": 0.9,
        "caseId": "CASE-1",
        "riskServiceAvailable": True,
    }
    assert len(repository.inserted) == 1


def test_invalid_transaction_is_rejected_before_persistence() -> None:
    repository = FakeRepository()
    app = create_app(Settings(), repository, FakeClients())
    payload = payment()
    payload["amount"] = -1

    with TestClient(app) as client:
        response = client.post("/api/v1/transactions", json=payload)

    assert response.status_code == 422
    assert repository.inserted == []
