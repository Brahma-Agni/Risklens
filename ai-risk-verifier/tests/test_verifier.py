import pytest

from risk_verifier.models import Decision, EvidenceReference, RiskDimensions, Signal, VerifyRequest
from risk_verifier.repository import InMemoryEvidenceRepository, RepositoryUnavailableError
from risk_verifier.verifier import RiskVerifier


def request(**overrides) -> VerifyRequest:
    values = {
        "transaction_id": "TX-001",
        "account_id": "ACC-001",
        "proposed_decision": Decision.ALLOW,
        "proposed_recommendation": "Allow payment",
        "confidence": 0.9,
        "dimensions": RiskDimensions(transaction=0.2, account=0.15, behavior=0.1),
        "signals": [
            Signal(
                type="KNOWN_DEVICE",
                source="BEHAVIOR",
                score=0.1,
                description="Device has an established history",
            )
        ],
    }
    values.update(overrides)
    return VerifyRequest(**values)


@pytest.mark.asyncio
async def test_corroborated_critical_risk_escalates_allow_to_hold() -> None:
    verifier = RiskVerifier(InMemoryEvidenceRepository())
    result = await verifier.verify(
        request(
            dimensions=RiskDimensions(transaction=0.94, structural=0.91, ring=0.96),
            signals=[
                Signal(
                    type="SHARED_DEVICE",
                    source="GRAPH",
                    score=0.96,
                    description="Eight accounts share one device",
                )
            ],
        )
    )

    assert result.final_decision == Decision.HOLD
    assert result.accepted is False
    assert "CRITICAL_RISK_CORROBORATED" in result.reason_codes


@pytest.mark.asyncio
async def test_complete_low_risk_evidence_accepts_allow() -> None:
    result = await RiskVerifier(InMemoryEvidenceRepository()).verify(request())
    assert result.final_decision == Decision.ALLOW
    assert result.accepted is True


@pytest.mark.asyncio
async def test_policy_can_set_action_floor() -> None:
    evidence = [
        EvidenceReference(
            kind="policy",
            reference_id="POLICY-1",
            title="Elevated ring policy",
            excerpt="Hold elevated coordinated rings",
            similarity=0.9,
            metadata={"threshold": 0.65, "minimum_action": "HOLD", "priority": 900},
        )
    ]
    result = await RiskVerifier(InMemoryEvidenceRepository(evidence)).verify(
        request(dimensions=RiskDimensions(transaction=0.7, structural=0.68, ring=0.69))
    )

    assert result.final_decision == Decision.HOLD
    assert "POLICY_ACTION_FLOOR" in result.reason_codes
    assert result.evidence[0].reference_id == "POLICY-1"


@pytest.mark.asyncio
async def test_missing_corroboration_requires_review() -> None:
    result = await RiskVerifier(InMemoryEvidenceRepository()).verify(
        request(dimensions=RiskDimensions(transaction=0.2), signals=[])
    )
    assert result.final_decision == Decision.REVIEW
    assert "INSUFFICIENT_EVIDENCE" in result.reason_codes


class OfflineRepository(InMemoryEvidenceRepository):
    async def search(self, text: str):
        raise RepositoryUnavailableError(text)


@pytest.mark.asyncio
async def test_retrieval_failure_fails_safe_to_review() -> None:
    result = await RiskVerifier(OfflineRepository()).verify(request())
    assert result.final_decision == Decision.REVIEW
    assert "EVIDENCE_RETRIEVAL_UNAVAILABLE" in result.reason_codes
