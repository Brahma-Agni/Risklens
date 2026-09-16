from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any
from uuid import UUID

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

Identifier64 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Identifier128 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=AliasGenerator(validation_alias=to_camel, serialization_alias=to_camel),
        populate_by_name=True,
        use_enum_values=True,
    )


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    HOLD = "HOLD"
    DECLINED = "DECLINED"
    RISK_UNAVAILABLE = "RISK_UNAVAILABLE"


class RiskCaseStatus(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"


class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnalystDecisionType(str, Enum):
    ALLOW = "ALLOW"
    VERIFY = "VERIFY"
    HOLD = "HOLD"
    CONFIRMED_ABUSE = "CONFIRMED_ABUSE"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class TransactionRequest(ApiModel):
    transaction_id: Identifier64
    sender_id: Identifier64
    receiver_id: Identifier64
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Annotated[str, StringConstraints(to_upper=True, pattern=r"^[A-Z]{3}$")]
    device_id: Annotated[str | None, StringConstraints(max_length=128)] = None
    ip_address: Annotated[
        str | None, StringConstraints(max_length=64, pattern=r"^[0-9a-fA-F:.]+$")
    ] = None
    payment_method: Annotated[str, StringConstraints(to_upper=True, min_length=1, max_length=32)]
    timestamp: datetime
    ip_id: Annotated[str | None, StringConstraints(max_length=128)] = None
    payment_instrument_id: Annotated[str | None, StringConstraints(max_length=128)] = None
    location_city: Annotated[str | None, StringConstraints(max_length=128)] = None
    location_state: Annotated[str | None, StringConstraints(max_length=128)] = None
    location_country: Annotated[
        str | None, StringConstraints(to_upper=True, pattern=r"^[A-Z]{2}$")
    ] = None
    authorization_status: Annotated[
        str | None, StringConstraints(to_upper=True, max_length=32)
    ] = None
    authentication_status: Annotated[
        str | None, StringConstraints(to_upper=True, max_length=32)
    ] = None
    transaction_status: Annotated[
        str | None, StringConstraints(to_upper=True, max_length=32)
    ] = None
    failure_reason: Annotated[
        str | None, StringConstraints(to_upper=True, max_length=64)
    ] = None
    merchant_category: Annotated[
        str | None, StringConstraints(to_upper=True, max_length=64)
    ] = None
    context: dict[str, Any] = Field(default_factory=dict, max_length=32)


class RiskSignal(ApiModel):
    type: str
    source: str
    score: float = Field(ge=0, le=1)
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class RiskEvaluation(ApiModel):
    transaction_risk: float = Field(ge=0, le=1)
    account_risk: float = Field(ge=0, le=1)
    behavior_risk: float = Field(ge=0, le=1)
    temporal_risk: float = Field(ge=0, le=1)
    structural_risk: float = Field(ge=0, le=1)
    similarity_risk: float = Field(ge=0, le=1)
    ring_risk: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    decision: TransactionStatus
    recommendation: str
    summary: str
    signals: list[RiskSignal] = Field(default_factory=list)

    @property
    def overall_risk(self) -> float:
        return max(
            self.transaction_risk,
            self.account_risk,
            self.behavior_risk,
            self.temporal_risk,
            self.structural_risk,
            self.similarity_risk,
            self.ring_risk,
        )


class TransactionResponse(ApiModel):
    transaction_id: str
    status: TransactionStatus
    recommended_action: str
    risk_score: float | None = None
    case_id: str | None = None
    risk_service_available: bool


class TransactionDetail(ApiModel):
    transaction_id: str
    sender_id: str
    receiver_id: str
    amount: Decimal
    currency: str
    device_id: str | None
    ip_address: str | None
    payment_method: str
    ip_id: str | None = None
    payment_instrument_id: str | None = None
    location_city: str | None = None
    location_state: str | None = None
    location_country: str | None = None
    authorization_status: str | None = None
    authentication_status: str | None = None
    transaction_status: str | None = None
    failure_reason: str | None = None
    merchant_category: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    received_at: datetime
    status: TransactionStatus
    risk_score: float | None
    case_id: str | None


class RiskCaseSummary(ApiModel):
    case_id: str
    transaction_id: str
    account_id: str
    status: RiskCaseStatus
    severity: RiskSeverity
    ring_risk: float
    confidence: float
    recommendation: str
    created_at: datetime


class StoredRiskSignal(RiskSignal):
    evidence: str
    created_at: datetime


class AnalystDecisionRequest(ApiModel):
    decision: AnalystDecisionType
    analyst: Identifier128
    comment: Annotated[str | None, StringConstraints(max_length=2000)] = None


class AnalystDecision(ApiModel):
    id: UUID
    decision: AnalystDecisionType
    analyst: str
    comment: str | None
    created_at: datetime


class AnalystAction(AnalystDecision):
    case_id: str
    transaction_id: str
    account_id: str


class RiskCaseDetail(RiskCaseSummary):
    transaction_risk: float
    account_risk: float
    behavior_risk: float
    temporal_risk: float
    structural_risk: float
    similarity_risk: float
    ai_summary: str
    updated_at: datetime
    resolved_at: datetime | None
    signals: list[StoredRiskSignal]
    decisions: list[AnalystDecision]


class CaseMemoryRequest(BaseModel):
    risk_case_id: str
    final_label: AnalystDecisionType
    case_summary: str
    feature_snapshot: dict[str, Any]
    evidence_snapshot: list[dict[str, Any]]
