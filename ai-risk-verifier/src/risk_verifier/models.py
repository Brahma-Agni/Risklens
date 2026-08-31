from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    HOLD = "HOLD"
    DECLINED = "DECLINED"


class FinalLabel(str, Enum):
    ALLOW = "ALLOW"
    VERIFY = "VERIFY"
    HOLD = "HOLD"
    CONFIRMED_ABUSE = "CONFIRMED_ABUSE"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class Signal(BaseModel):
    type: Identifier
    source: Identifier
    score: float = Field(ge=0, le=1)
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]
    evidence: dict[str, Any] = Field(default_factory=dict)


class RiskDimensions(BaseModel):
    transaction: float | None = Field(default=None, ge=0, le=1)
    account: float | None = Field(default=None, ge=0, le=1)
    behavior: float | None = Field(default=None, ge=0, le=1)
    temporal: float | None = Field(default=None, ge=0, le=1)
    structural: float | None = Field(default=None, ge=0, le=1)
    similarity: float | None = Field(default=None, ge=0, le=1)
    ring: float | None = Field(default=None, ge=0, le=1)

    def observed(self) -> list[float]:
        return [value for value in self.model_dump().values() if value is not None]


class VerifyRequest(BaseModel):
    transaction_id: Identifier
    account_id: Identifier
    proposed_decision: Decision
    proposed_recommendation: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    confidence: float = Field(ge=0, le=1)
    dimensions: RiskDimensions
    signals: list[Signal] = Field(default_factory=list, max_length=100)
    summary: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=4000)] = None
    context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_evidence_input(self) -> "VerifyRequest":
        if not self.dimensions.observed() and not self.signals:
            raise ValueError("at least one risk dimension or signal is required")
        return self

    def retrieval_text(self) -> str:
        factors = " ".join(
            f"{name} risk {value:.2f}"
            for name, value in self.dimensions.model_dump().items()
            if value is not None
        )
        signals = " ".join(f"{item.type} {item.description}" for item in self.signals)
        return " ".join(
            part
            for part in [
                self.summary or "",
                factors,
                signals,
                f"proposed {self.proposed_decision.value}",
            ]
            if part
        )


class EvidenceReference(BaseModel):
    kind: str
    reference_id: str
    title: str
    excerpt: str
    similarity: float = Field(ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerifyResponse(BaseModel):
    transaction_id: str
    accepted: bool
    proposed_decision: Decision
    final_decision: Decision
    recommendation: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    reason_codes: list[str]
    evidence: list[EvidenceReference]
    guardrails_applied: list[str]
    trace_id: str
    verifier_version: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryCaseRequest(BaseModel):
    risk_case_id: Identifier
    final_label: FinalLabel
    case_summary: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)
    ]
    feature_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence_snapshot: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


class PolicyRequest(BaseModel):
    policy_id: Identifier
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=250)]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]
    minimum_action: Decision = Decision.REVIEW
    threshold: float = Field(default=0.7, ge=0, le=1)
    priority: int = Field(default=100, ge=0, le=1000)
    tags: list[str] = Field(default_factory=list, max_length=30)


class StoreResponse(BaseModel):
    reference_id: str
    point_id: str
    status: str = "stored"
