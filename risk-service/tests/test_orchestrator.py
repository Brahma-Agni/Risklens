import pytest

from risk_service.config import Settings
from risk_service.models import Decision, EngineResult, RiskSignal
from risk_service.orchestrator import RiskOrchestrator

from .fakes import FakeEngineStore, FakeHistory, FakeVerifier, historical, request


def orchestrator(*, graph=None, similarity=None, verifier=None, history=None):
    return RiskOrchestrator(
        settings=Settings(require_verifier=True),
        history_store=FakeHistory(history or [historical() for _ in range(10)]),
        graph_store=FakeEngineStore(graph),
        similarity_store=FakeEngineStore(similarity),
        verifier=verifier or FakeVerifier(),
    )


@pytest.mark.asyncio
async def test_graph_ring_escalates_to_hold() -> None:
    graph = EngineResult(
        score=0.92,
        signals=[
            RiskSignal(
                type="SHARED_DEVICE",
                source="GRAPH",
                score=0.92,
                description="Six accounts share a device.",
            )
        ],
    )
    result = await orchestrator(graph=graph).evaluate(request())
    assert result.decision == Decision.HOLD
    assert result.structural_risk == 0.92
    assert len(result.recommendation) <= 64
    assert any(signal.type == "AI_VERIFICATION" for signal in result.signals)


@pytest.mark.asyncio
async def test_similarity_contributes_to_ring_risk() -> None:
    similarity = EngineResult(score=0.88)
    result = await orchestrator(similarity=similarity).evaluate(request())
    assert result.similarity_risk == 0.88
    assert result.ring_risk > 0


@pytest.mark.asyncio
async def test_verifier_outage_withholds_allow() -> None:
    result = await orchestrator(verifier=FakeVerifier(offline=True)).evaluate(request())
    assert result.decision == Decision.REVIEW
    assert any(signal.type == "VERIFIER_UNAVAILABLE" for signal in result.signals)
