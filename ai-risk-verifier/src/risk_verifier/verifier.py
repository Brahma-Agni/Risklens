import uuid

from risk_verifier import __version__
from risk_verifier.models import Decision, EvidenceReference, VerifyRequest, VerifyResponse
from risk_verifier.repository import EvidenceRepository, RepositoryUnavailableError

DECISION_RANK = {
    Decision.ALLOW: 0,
    Decision.REVIEW: 1,
    Decision.HOLD: 2,
    Decision.DECLINED: 3,
}


class RiskVerifier:
    def __init__(
        self,
        repository: EvidenceRepository,
        *,
        confirmed_case_threshold: float = 0.25,
        false_positive_threshold: float = 0.32,
    ) -> None:
        self.repository = repository
        self.confirmed_case_threshold = confirmed_case_threshold
        self.false_positive_threshold = false_positive_threshold

    async def verify(self, request: VerifyRequest) -> VerifyResponse:
        retrieval_unavailable = False
        try:
            evidence = await self.repository.search(request.retrieval_text())
        except RepositoryUnavailableError:
            evidence = []
            retrieval_unavailable = True
        values = request.dimensions.observed()
        max_risk = max(values, default=0.0)
        average_risk = sum(values) / len(values) if values else 0.0
        critical_signals = [signal for signal in request.signals if signal.score >= 0.85]
        confirmed_cases = [
            item
            for item in evidence
            if item.kind == "case"
            and item.metadata.get("final_label") == "CONFIRMED_ABUSE"
            and item.similarity >= self.confirmed_case_threshold
        ]
        false_positive_cases = [
            item
            for item in evidence
            if item.kind == "case"
            and item.metadata.get("final_label") == "FALSE_POSITIVE"
            and item.similarity >= self.false_positive_threshold
        ]

        final = request.proposed_decision
        reason_codes: list[str] = []
        guardrails: list[str] = []

        if retrieval_unavailable:
            final = self._maximum(final, Decision.REVIEW)
            reason_codes.append("EVIDENCE_RETRIEVAL_UNAVAILABLE")
            guardrails.append("retrieval-failure-review")

        if len(request.signals) == 0 or len(values) < 2:
            final = self._maximum(final, Decision.REVIEW)
            reason_codes.append("INSUFFICIENT_EVIDENCE")
            guardrails.append("minimum-evidence")

        if max_risk >= 0.9 and critical_signals:
            final = self._maximum(final, Decision.HOLD)
            reason_codes.append("CRITICAL_RISK_CORROBORATED")
            guardrails.append("critical-risk-hold")
        elif max_risk >= 0.7 or len(critical_signals) >= 2:
            final = self._maximum(final, Decision.REVIEW)
            reason_codes.append("ELEVATED_RISK")
            guardrails.append("elevated-risk-review")

        if confirmed_cases and max_risk >= 0.65:
            final = self._maximum(final, Decision.HOLD)
            reason_codes.append("SIMILAR_CONFIRMED_ABUSE")
            guardrails.append("case-memory-corroboration")

        policy_action = self._policy_floor(evidence, max_risk)
        if policy_action is not None and DECISION_RANK[policy_action] > DECISION_RANK[final]:
            final = policy_action
            reason_codes.append("POLICY_ACTION_FLOOR")
            guardrails.append("retrieved-policy-floor")

        if false_positive_cases and not confirmed_cases and max_risk < 0.55:
            reason_codes.append("SIMILAR_FALSE_POSITIVE")
            # Historical similarity can request review, but never silently override a hold/decline.
            if final == Decision.ALLOW:
                final = Decision.REVIEW
                guardrails.append("false-positive-human-review")

        if request.confidence < 0.55:
            final = self._maximum(final, Decision.REVIEW)
            reason_codes.append("LOW_MODEL_CONFIDENCE")
            guardrails.append("low-confidence-review")

        if not reason_codes:
            reason_codes.append("PROPOSAL_SUPPORTED")

        accepted = final == request.proposed_decision
        confidence = self._verification_confidence(request, evidence, average_risk, accepted)
        rationale = self._rationale(final, max_risk, critical_signals, evidence, accepted)
        recommendation = (
            request.proposed_recommendation
            if accepted
            else self._recommendation(final, request.proposed_recommendation)
        )
        return VerifyResponse(
            transaction_id=request.transaction_id,
            accepted=accepted,
            proposed_decision=request.proposed_decision,
            final_decision=final,
            recommendation=recommendation,
            confidence=confidence,
            rationale=rationale,
            reason_codes=list(dict.fromkeys(reason_codes)),
            evidence=evidence[:10],
            guardrails_applied=list(dict.fromkeys(guardrails)),
            trace_id=str(uuid.uuid4()),
            verifier_version=__version__,
        )

    @staticmethod
    def _maximum(left: Decision, right: Decision) -> Decision:
        return left if DECISION_RANK[left] >= DECISION_RANK[right] else right

    @staticmethod
    def _policy_floor(evidence: list[EvidenceReference], max_risk: float) -> Decision | None:
        applicable: list[tuple[int, Decision]] = []
        for item in evidence:
            if item.kind != "policy":
                continue
            threshold = float(item.metadata.get("threshold", 1.1))
            action = item.metadata.get("minimum_action")
            try:
                decision = Decision(action)
            except (TypeError, ValueError):
                continue
            if max_risk >= threshold:
                applicable.append((int(item.metadata.get("priority", 100)), decision))
        if not applicable:
            return None
        applicable.sort(key=lambda value: (DECISION_RANK[value[1]], value[0]), reverse=True)
        return applicable[0][1]

    @staticmethod
    def _verification_confidence(
        request: VerifyRequest,
        evidence: list[EvidenceReference],
        average_risk: float,
        accepted: bool,
    ) -> float:
        evidence_strength = max((item.similarity for item in evidence), default=0.0)
        completeness = min(1.0, (len(request.dimensions.observed()) + len(request.signals)) / 8)
        agreement = 0.1 if accepted else 0.0
        score = 0.4 * request.confidence + 0.25 * evidence_strength + 0.25 * completeness
        score += 0.1 * abs(average_risk - 0.5) * 2 + agreement
        return round(max(0.05, min(0.99, score)), 4)

    @staticmethod
    def _rationale(
        final: Decision,
        max_risk: float,
        critical_signals: list,
        evidence: list[EvidenceReference],
        accepted: bool,
    ) -> str:
        disposition = "supports" if accepted else "overrides"
        return (
            f"Evidence verification {disposition} the proposed action and returns {final.value}. "
            f"The strongest observed risk is {max_risk:.2f}, with {len(critical_signals)} "
            f"critical signal(s) and {len(evidence)} retrieved policy/case reference(s)."
        )

    @staticmethod
    def _recommendation(final: Decision, original: str) -> str:
        recommendations = {
            Decision.ALLOW: "Allow the transaction and continue routine monitoring.",
            Decision.REVIEW: (
                "Route to analyst review and request additional verification before release."
            ),
            Decision.HOLD: (
                "Hold the transaction while linked accounts and instruments are investigated."
            ),
            Decision.DECLINED: (
                "Decline the transaction and escalate the linked entities for investigation."
            ),
        }
        return f"{recommendations[final]} Original proposal: {original}"
