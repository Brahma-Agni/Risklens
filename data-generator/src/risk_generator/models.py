from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Account:
    account_id: str
    home_device_id: str
    home_ip_address: str
    payment_method: str
    typical_amount: float


@dataclass(frozen=True)
class Merchant:
    merchant_id: str
    category: str
    typical_amount: float


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    sender_id: str
    receiver_id: str
    amount: float
    currency: str
    device_id: str
    ip_address: str
    payment_method: str
    timestamp: datetime

    def backend_payload(self) -> dict[str, Any]:
        return {
            "transactionId": self.transaction_id,
            "senderId": self.sender_id,
            "receiverId": self.receiver_id,
            "amount": round(self.amount, 2),
            "currency": self.currency,
            "deviceId": self.device_id,
            "ipAddress": self.ip_address,
            "paymentMethod": self.payment_method,
            "timestamp": self.timestamp.isoformat().replace("+00:00", "Z"),
        }


@dataclass(frozen=True)
class GroundTruth:
    transaction_id: str
    is_abuse: bool
    scenario: str
    expected_risk_band: str
    explanation: str
    ring_id: str | None = None
    related_entities: list[str] = field(default_factory=list)

    def record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeneratedEvent:
    transaction: Transaction
    truth: GroundTruth


@dataclass(frozen=True)
class Dataset:
    events: list[GeneratedEvent]
    seed: int
    requested_abuse_rate: float
    started_at: datetime
    duration_seconds: int

    @property
    def abuse_count(self) -> int:
        return sum(event.truth.is_abuse for event in self.events)

    @property
    def scenario_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self.events:
            counts[event.truth.scenario] = counts.get(event.truth.scenario, 0) + 1
        return dict(sorted(counts.items()))
