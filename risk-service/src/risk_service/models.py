from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=to_camel, serialization_alias=to_camel),
        populate_by_name=True,
    )


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    HOLD = "HOLD"
    DECLINED = "DECLINED"


class RiskRequest(ApiModel):
    transaction_id: Identifier
    sender_id: Identifier
    receiver_id: Identifier
    amount: float = Field(gt=0, le=10**16)
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    device_id: Annotated[str | None, StringConstraints(max_length=128)] = None
    ip_address: Annotated[str | None, StringConstraints(max_length=64)] = None
    payment_method: Identifier
    timestamp: datetime


class RiskSignal(ApiModel):
    type: str
    source: str
    score: float = Field(ge=0, le=1)
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class RiskResponse(ApiModel):
    transaction_risk: float = Field(ge=0, le=1)
    account_risk: float = Field(ge=0, le=1)
    behavior_risk: float = Field(ge=0, le=1)
    temporal_risk: float = Field(ge=0, le=1)
    structural_risk: float = Field(ge=0, le=1)
    similarity_risk: float = Field(ge=0, le=1)
    ring_risk: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    decision: Decision
    recommendation: Annotated[str, StringConstraints(max_length=64)]
    summary: str
    signals: list[RiskSignal]


class HistoricalTransaction:
    def __init__(
        self,
        *,
        transaction_id: str,
        amount: float,
        receiver_id: str,
        device_id: str | None,
        ip_address: str | None,
        payment_method: str,
        timestamp: datetime,
        status: str,
    ) -> None:
        self.transaction_id = transaction_id
        self.amount = amount
        self.receiver_id = receiver_id
        self.device_id = device_id
        self.ip_address = ip_address
        self.payment_method = payment_method
        self.timestamp = timestamp
        self.status = status


class EngineResult(BaseModel):
    score: float = Field(ge=0, le=1)
    signals: list[RiskSignal] = Field(default_factory=list)
    available: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
