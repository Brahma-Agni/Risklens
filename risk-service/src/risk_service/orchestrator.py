import asyncio

from risk_service.config import Settings
from risk_service.engines import (
    account_engine,
    behavior_engine,
    clamp,
    temporal_engine,
    transaction_engine,
)
from risk_service.models import Decision, EngineResult, RiskRequest, RiskResponse, RiskSignal
from risk_service.services import (
    GraphStore,
    HistoryStore,
    RequiredDependencyError,
    SimilarityStore,
    VerificationClient,
)


class RiskOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        history_store: HistoryStore,
        graph_store: GraphStore,
        similarity_store: SimilarityStore,
        verifier: VerificationClient,
    ) -> None:
        self.settings = settings
        self.history_store = history_store
        self.graph_store = graph_store
        self.similarity_store = similarity_store
        self.verifier = verifier

    async def evaluate(self, request: RiskRequest) -> RiskResponse:
        history = await self.history_store.history(request, self.settings.history_limit)
        transaction = transaction_engine(request, history)
        behavior = behavior_engine(history)
        temporal = temporal_engine(request, history)
        account = account_engine(history, transaction)
        similarity_context = self._similarity_context(request, transaction, behavior, temporal)
        graph, similarity = await asyncio.gather(
            self.graph_store.analyze(request),
            self.similarity_store.analyze(request, similarity_context),
        )

        signals = [
            *transaction.signals,
            *account.signals,
            *behavior.signals,
            *temporal.signals,
            *graph.signals,
            *similarity.signals,
        ]
        if not graph.available:
            signals.append(self._unavailable_signal("GRAPH_UNAVAILABLE", "GRAPH"))
        if not similarity.available:
            signals.append(self._unavailable_signal("SIMILARITY_UNAVAILABLE", "SIMILARITY"))

        ring = clamp(
            max(
                graph.score,
                0.6 * graph.score + 0.25 * temporal.score + 0.15 * similarity.score,
            )
        )
        dimensions = {
            "transaction": transaction.score,
            "account": account.score,
            "behavior": behavior.score,
            "temporal": temporal.score,
            "structural": graph.score,
            "similarity": similarity.score,
            "ring": ring,
        }
        overall = max(transaction.score, account.score, behavior.score, temporal.score, ring)
        decision = self._decision(overall, signals)
        recommendation = self._recommendation(decision)
        available_optional = int(graph.available) + int(similarity.available)
        confidence = clamp(
            0.48
            + min(0.18, len(history) / 100)
            + 0.08 * available_optional
            + min(0.14, len(signals) * 0.025)
        )
        summary = self._summary(request, decision, overall, dimensions, signals)

        try:
            (
                verified_decision,
                _verified_recommendation,
                verified_confidence,
                verifier_signals,
            ) = await self.verifier.verify(
                request,
                decision=decision,
                recommendation=recommendation,
                confidence=confidence,
                dimensions=dimensions,
                signals=signals,
                summary=summary,
            )
            decision = verified_decision
            # The backend stores this action label in a VARCHAR(64). Verifier
            # prose belongs in its signal and the response summary instead.
            recommendation = self._recommendation(decision)
            confidence = clamp(verified_confidence)
            signals.extend(verifier_signals)
            summary = self._summary(request, decision, overall, dimensions, signals)
        except RequiredDependencyError:
            signals.append(self._unavailable_signal("VERIFIER_UNAVAILABLE", "VERIFIER"))
            if self.settings.require_verifier and decision == Decision.ALLOW:
                decision = Decision.REVIEW
                recommendation = self._recommendation(decision)
                confidence = min(confidence, 0.55)
                summary = (
                    "Automated allow was withheld because the evidence verifier was unavailable. "
                    + summary
                )

        return RiskResponse(
            transaction_risk=transaction.score,
            account_risk=account.score,
            behavior_risk=behavior.score,
            temporal_risk=temporal.score,
            structural_risk=graph.score,
            similarity_risk=similarity.score,
            ring_risk=ring,
            confidence=confidence,
            decision=decision,
            recommendation=recommendation,
            summary=summary,
            signals=signals,
        )

    def _decision(self, overall: float, signals: list[RiskSignal]) -> Decision:
        critical = sum(signal.score >= 0.85 for signal in signals)
        if overall >= self.settings.decline_threshold and critical >= 2:
            return Decision.DECLINED
        if overall >= self.settings.hold_threshold:
            return Decision.HOLD
        if overall >= self.settings.review_threshold:
            return Decision.REVIEW
        return Decision.ALLOW

    @staticmethod
    def _recommendation(decision: Decision) -> str:
        return {
            Decision.ALLOW: "Allow and continue routine monitoring.",
            Decision.REVIEW: "Route to analyst review before settlement.",
            Decision.HOLD: "Hold and investigate linked accounts and instruments.",
            Decision.DECLINED: "Decline and escalate linked entities for investigation.",
        }[decision]

    @staticmethod
    def _summary(
        request: RiskRequest,
        decision: Decision,
        overall: float,
        dimensions: dict[str, float],
        signals: list[RiskSignal],
    ) -> str:
        strongest = sorted(dimensions.items(), key=lambda item: item[1], reverse=True)[:3]
        factors = ", ".join(f"{name}={score:.2f}" for name, score in strongest)
        elevated = [signal.type for signal in signals if signal.score >= 0.6]
        signal_text = ", ".join(elevated[:4]) if elevated else "no elevated signal"
        return (
            f"Transaction {request.transaction_id} is assessed at {overall:.2f} and routed to "
            f"{decision.value}. Strongest dimensions: {factors}. Evidence: {signal_text}."
        )

    @staticmethod
    def _similarity_context(
        request: RiskRequest,
        transaction: EngineResult,
        behavior: EngineResult,
        temporal: EngineResult,
    ) -> str:
        types = " ".join(
            signal.type for result in (transaction, behavior, temporal) for signal in result.signals
        )
        return (
            f"payment {request.payment_method} amount {request.amount:.2f} sender "
            f"{request.sender_id} receiver {request.receiver_id} {types}"
        )

    @staticmethod
    def _unavailable_signal(signal_type: str, source: str) -> RiskSignal:
        return RiskSignal(
            type=signal_type,
            source=source,
            score=0,
            description=f"{source.title()} evidence source was unavailable for this evaluation.",
            evidence={"available": False},
        )

    async def health(self) -> dict[str, bool]:
        postgres, neo4j, qdrant, verifier = await asyncio.gather(
            self.history_store.health(),
            self.graph_store.health(),
            self.similarity_store.health(),
            self.verifier.health(),
        )
        return {
            "postgres": postgres,
            "neo4j": neo4j,
            "qdrant": qdrant,
            "verifier": verifier,
        }
