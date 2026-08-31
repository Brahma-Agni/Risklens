from datetime import datetime, timezone

from risk_service.models import (
    Decision,
    EngineResult,
    HistoricalTransaction,
    RiskRequest,
    RiskSignal,
)
from risk_service.services import RequiredDependencyError


def request(**overrides) -> RiskRequest:
    values = {
        "transactionId": "TX-TEST-001",
        "senderId": "USER-001",
        "receiverId": "MERCHANT-001",
        "amount": 1500,
        "currency": "INR",
        "deviceId": "DEV-001",
        "ipAddress": "10.0.0.1",
        "paymentMethod": "UPI",
        "timestamp": "2026-01-01T00:10:00Z",
    }
    values.update(overrides)
    return RiskRequest.model_validate(values)


def historical(**overrides) -> HistoricalTransaction:
    values = {
        "transaction_id": "TX-OLD-001",
        "amount": 1200,
        "receiver_id": "MERCHANT-001",
        "device_id": "DEV-001",
        "ip_address": "10.0.0.1",
        "payment_method": "UPI",
        "timestamp": datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
        "status": "ALLOW",
    }
    values.update(overrides)
    return HistoricalTransaction(**values)


class FakeHistory:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []

    async def history(self, request, limit):
        del request, limit
        return self.rows

    async def health(self):
        return True


class FakeEngineStore:
    def __init__(self, result: EngineResult | None = None) -> None:
        self.result = result or EngineResult(score=0)

    async def analyze(self, request, context=None):
        del request, context
        return self.result

    async def health(self):
        return True


class FakeVerifier:
    def __init__(self, *, offline=False, decision: Decision | None = None) -> None:
        self.offline = offline
        self.decision = decision

    async def verify(self, request, *, decision, recommendation, confidence, **kwargs):
        del request, kwargs
        if self.offline:
            raise RequiredDependencyError("offline")
        return (
            self.decision or decision,
            recommendation,
            confidence,
            [
                RiskSignal(
                    type="AI_VERIFICATION",
                    source="VERIFIER",
                    score=confidence,
                    description="Proposal verified in test.",
                )
            ],
        )

    async def health(self):
        return not self.offline
