import math
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from risk_service.models import EngineResult, HistoricalTransaction, RiskRequest, RiskSignal


@dataclass(frozen=True)
class ScoringThresholds:
    amount_deviation_ratio: float = 3.0
    velocity_5m: int = 4
    velocity_1h: int = 12
    beneficiary_rotation_5m: int = 4
    fragment_amount_ceiling: float = 10_000
    fragment_count_1h: int = 4
    fragment_total_1h: float = 20_000


DEFAULT_THRESHOLDS = ScoringThresholds()


def clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _contextual_identity_anomaly(request: RiskRequest) -> tuple[float, list[RiskSignal]]:
    """Score corroborated, upstream-provided account-takeover context."""
    impossible_travel = request.context.get("impossibleTravel") is True
    device_trust = str(request.context.get("deviceTrust", "")).upper()
    ip_type = str(request.context.get("ipType", "")).upper()
    new_device = device_trust in {"NEW", "UNTRUSTED"}
    risky_network = ip_type in {"DATACENTER", "PROXY", "VPN"}
    foreign_origin = bool(request.location_country and request.location_country != "IN")

    if impossible_travel and new_device and risky_network and foreign_origin:
        score = 0.88
        return score, [
            RiskSignal(
                type="CORROBORATED_IDENTITY_ANOMALY",
                source="TRANSACTION",
                score=score,
                description=(
                    "Impossible travel is corroborated by a new device, risky network, "
                    "and foreign payment origin."
                ),
                evidence={
                    "locationCountry": request.location_country,
                    "deviceTrust": device_trust,
                    "ipType": ip_type,
                    "impossibleTravel": True,
                },
            )
        ]
    if impossible_travel:
        # Impossible-travel metadata alone is meaningful but remains below the
        # intervention threshold until another independent signal corroborates it.
        score = 0.65
        return score, [
            RiskSignal(
                type="IMPOSSIBLE_TRAVEL",
                source="TRANSACTION",
                score=score,
                description="Upstream telemetry indicates geographically impossible travel.",
                evidence={"locationCountry": request.location_country},
            )
        ]
    return 0.0, []


def transaction_engine(
    request: RiskRequest,
    history: list[HistoricalTransaction],
    thresholds: ScoringThresholds = DEFAULT_THRESHOLDS,
) -> EngineResult:
    history = _unique_history(history)
    contextual_risk, contextual_signals = _contextual_identity_anomaly(request)
    signals: list[RiskSignal] = list(contextual_signals)
    if not history:
        return EngineResult(
            score=max(0.35, contextual_risk),
            signals=[
                *signals,
                RiskSignal(
                    type="LIMITED_ACCOUNT_HISTORY",
                    source="TRANSACTION",
                    score=0.35,
                    description="No prior sender transactions were available for comparison.",
                    evidence={"historyCount": 0},
                )
            ],
            metadata={"historyCount": 0},
        )

    amounts = [item.amount for item in history]
    median = max(1.0, statistics.median(amounts))
    ratio = request.amount / median
    amount_risk = clamp(math.log2(max(1.0, ratio)) / 3.5)
    if ratio >= thresholds.amount_deviation_ratio:
        signals.append(
            RiskSignal(
                type="AMOUNT_DEVIATION",
                source="TRANSACTION",
                score=amount_risk,
                description="Amount is materially above the sender's historical median.",
                evidence={
                    "amount": request.amount,
                    "median": round(median, 2),
                    "ratio": round(ratio, 2),
                },
            )
        )

    devices = {item.device_id for item in history if item.device_id}
    ips = {item.ip_address for item in history if item.ip_address}
    methods = {item.payment_method for item in history}
    receivers = {item.receiver_id for item in history}
    novelty_scores = []
    for novel, score, signal_type, description, value in (
        (
            bool(request.device_id and request.device_id not in devices),
            0.72,
            "NOVEL_DEVICE",
            "Sender uses a previously unseen device.",
            request.device_id,
        ),
        (
            bool(request.ip_address and request.ip_address not in ips),
            0.62,
            "NOVEL_IP",
            "Sender uses a previously unseen network address.",
            request.ip_address,
        ),
        (
            request.payment_method not in methods,
            0.45,
            "NOVEL_PAYMENT_METHOD",
            "Sender uses a previously unseen payment method.",
            request.payment_method,
        ),
        (
            request.receiver_id not in receivers,
            0.30,
            "NEW_BENEFICIARY",
            "Sender pays a previously unseen beneficiary.",
            request.receiver_id,
        ),
    ):
        if novel:
            novelty_scores.append(score)
            signals.append(
                RiskSignal(
                    type=signal_type,
                    source="TRANSACTION",
                    score=score,
                    description=description,
                    evidence={"value": value},
                )
            )

    # Do not forget an account takeover after the attacker's first payment.
    # Compare the current identity attributes with the dominant established
    # profile, not only with set membership in the complete history.
    established = history[:50]
    dominant_device, dominant_device_share = _dominant_profile(
        [item.device_id for item in established if item.device_id]
    )
    dominant_ip, dominant_ip_share = _dominant_profile(
        [item.ip_address for item in established if item.ip_address]
    )
    profile_shift_scores: list[float] = []
    device_shift = bool(
        request.device_id
        and dominant_device
        and request.device_id != dominant_device
        and dominant_device_share >= 0.5
    )
    ip_shift = bool(
        request.ip_address
        and dominant_ip
        and request.ip_address != dominant_ip
        and dominant_ip_share >= 0.5
    )
    if device_shift:
        profile_shift_scores.append(0.82)
        signals.append(
            RiskSignal(
                type="DEVICE_PROFILE_SHIFT",
                source="TRANSACTION",
                score=0.82,
                description="Device differs from the account's dominant established profile.",
                evidence={
                    "currentDevice": request.device_id,
                    "dominantDevice": dominant_device,
                    "dominantShare": round(dominant_device_share, 4),
                },
            )
        )
    if ip_shift:
        profile_shift_scores.append(0.74)
        signals.append(
            RiskSignal(
                type="NETWORK_PROFILE_SHIFT",
                source="TRANSACTION",
                score=0.74,
                description="Network differs from the account's dominant established profile.",
                evidence={
                    "currentIp": request.ip_address,
                    "dominantIp": dominant_ip,
                    "dominantShare": round(dominant_ip_share, 4),
                },
            )
        )
    lifecycle_scores: list[float] = []
    if request.authentication_status in {"FAILED", "CHALLENGE_FAILED"}:
        lifecycle_scores.append(0.48)
        signals.append(
            RiskSignal(
                type="AUTHENTICATION_ANOMALY",
                source="TRANSACTION",
                score=0.48,
                description="The payment failed or did not complete authentication.",
                evidence={"authenticationStatus": request.authentication_status},
            )
        )
    if request.authorization_status in {"DECLINED", "DENIED"}:
        lifecycle_scores.append(0.4)
        signals.append(
            RiskSignal(
                type="AUTHORIZATION_DECLINED",
                source="TRANSACTION",
                score=0.4,
                description="The payment authorization was declined.",
                evidence={"authorizationStatus": request.authorization_status},
            )
        )

    novelty_risk = max([*novelty_scores, *profile_shift_scores], default=0.0)
    lifecycle_risk = max(lifecycle_scores, default=0.0)
    # A single novelty or payment failure should not be enough to hold a customer.
    # Correlated amount + identity novelty receives the strongest transaction score.
    score = clamp(
        max(
            0.52 * amount_risk + 0.38 * novelty_risk + 0.10 * lifecycle_risk,
            0.7 * lifecycle_risk,
            contextual_risk,
        )
    )
    return EngineResult(
        score=score,
        signals=signals,
        metadata={
            "historyCount": len(history),
            "amountMedian": round(median, 2),
            "amountRatio": round(ratio, 2),
        },
    )


def behavior_engine(
    history: list[HistoricalTransaction], request: RiskRequest | None = None
) -> EngineResult:
    history = _unique_history(history)
    if not history:
        return EngineResult(score=0.3, metadata={"historyCount": 0})
    adverse = {"REVIEW", "HOLD", "DECLINED", "RISK_UNAVAILABLE"}
    adverse_count = sum(item.status in adverse for item in history[:50])
    adverse_rate = adverse_count / min(50, len(history))
    sample = history[:50]
    lifecycle_failures = sum(
        item.authentication_status in {"FAILED", "CHALLENGE_FAILED"}
        or item.authorization_status in {"DECLINED", "DENIED"}
        or item.transaction_status == "FAILED"
        for item in sample
    )
    current_failure = bool(
        request
        and (
            request.authentication_status in {"FAILED", "CHALLENGE_FAILED"}
            or request.authorization_status in {"DECLINED", "DENIED"}
            or request.transaction_status == "FAILED"
        )
    )
    lifecycle_failure_rate = (lifecycle_failures + int(current_failure)) / (
        len(sample) + int(request is not None)
    )
    receiver_concentration = _concentration([item.receiver_id for item in sample])
    method_count = len({item.payment_method for item in sample})
    score = clamp(max(0.45 * adverse_rate, 0.85 * lifecycle_failure_rate))
    signals = []
    if adverse_rate >= 0.35:
        signals.append(
            RiskSignal(
                type="ADVERSE_DECISION_HISTORY",
                source="BEHAVIOR",
                score=clamp(adverse_rate),
                description="A high share of recent sender transactions required intervention.",
                evidence={"adverseCount": adverse_count, "sampleSize": min(50, len(history))},
            )
        )
    if lifecycle_failure_rate >= 0.3 and len(sample) >= 4:
        signals.append(
            RiskSignal(
                type="REPEATED_LIFECYCLE_FAILURES",
                source="BEHAVIOR",
                score=clamp(lifecycle_failure_rate),
                description="Recent payments repeatedly failed authentication or authorization.",
                evidence={
                    "failureCount": lifecycle_failures,
                    "sampleSize": len(sample),
                },
            )
        )
    return EngineResult(
        score=score,
        signals=signals,
        metadata={
            "adverseRate": round(adverse_rate, 4),
            "receiverConcentration": round(receiver_concentration, 4),
            "lifecycleFailureRate": round(lifecycle_failure_rate, 4),
            "paymentMethodCount": method_count,
        },
    )


def temporal_engine(
    request: RiskRequest,
    history: list[HistoricalTransaction],
    thresholds: ScoringThresholds = DEFAULT_THRESHOLDS,
) -> EngineResult:
    history = _unique_history(history)
    five_minutes = request.timestamp - timedelta(minutes=5)
    one_hour = request.timestamp - timedelta(hours=1)
    recent_five = [item for item in history if five_minutes <= item.timestamp <= request.timestamp]
    recent_hour = [item for item in history if one_hour <= item.timestamp <= request.timestamp]
    # Window counts include the transaction currently being evaluated.
    velocity_5m = len(recent_five) + 1
    velocity_1h = len(recent_hour) + 1
    beneficiary_count = len({item.receiver_id for item in recent_five} | {request.receiver_id})
    velocity_risk = clamp(
        max(
            velocity_5m / thresholds.velocity_5m,
            velocity_1h / thresholds.velocity_1h,
        )
    )
    rotation_risk = clamp(
        max(0, beneficiary_count - 1) / thresholds.beneficiary_rotation_5m
    )
    fragment_amount_ceiling = thresholds.fragment_amount_ceiling
    fragment_payments = [
        item
        for item in recent_hour
        if item.receiver_id == request.receiver_id and item.amount <= fragment_amount_ceiling
    ]
    fragment_total = sum(item.amount for item in fragment_payments) + request.amount
    is_fragmented_burst = (
        request.amount <= fragment_amount_ceiling
        and len(fragment_payments) >= thresholds.fragment_count_1h
        and fragment_total >= thresholds.fragment_total_1h
    )
    fragmentation_risk = (
        clamp(0.78 + 0.04 * min(len(fragment_payments) - 4, 4))
        if is_fragmented_burst
        else 0.0
    )
    score = clamp(
        max(0.7 * velocity_risk + 0.3 * rotation_risk, fragmentation_risk)
    )
    signals = []
    if velocity_5m >= thresholds.velocity_5m:
        signals.append(
            RiskSignal(
                type="VELOCITY_SPIKE",
                source="TEMPORAL",
                score=velocity_risk,
                description="Sender transaction velocity is elevated within five minutes.",
                evidence={"transactionsFiveMinutes": velocity_5m, "transactionsHour": velocity_1h},
            )
        )
    if beneficiary_count >= thresholds.beneficiary_rotation_5m:
        signals.append(
            RiskSignal(
                type="BENEFICIARY_ROTATION",
                source="TEMPORAL",
                score=rotation_risk,
                description="Sender rapidly rotates across multiple beneficiaries.",
                evidence={"uniqueBeneficiaries": beneficiary_count, "windowMinutes": 5},
            )
        )
    if is_fragmented_burst:
        signals.append(
            RiskSignal(
                type="FRAGMENTED_PAYMENT_BURST",
                source="TEMPORAL",
                score=fragmentation_risk,
                description=(
                    "A rapid sequence of small payments may be fragmenting a larger transfer."
                ),
                evidence={
                    "priorSmallPayments": len(fragment_payments),
                    "currentAmount": round(request.amount, 2),
                    "burstTotal": round(fragment_total, 2),
                    "amountCeiling": fragment_amount_ceiling,
                    "windowMinutes": 60,
                },
            )
        )
    return EngineResult(
        score=score,
        signals=signals,
        metadata={
            "transactionsFiveMinutes": velocity_5m,
            "transactionsHour": velocity_1h,
            "uniqueBeneficiariesFiveMinutes": beneficiary_count,
            "priorSmallPaymentsOneHour": len(fragment_payments),
            "fragmentationRisk": round(fragmentation_risk, 4),
        },
    )


def account_engine(history: list[HistoricalTransaction], transaction: EngineResult) -> EngineResult:
    history = _unique_history(history)
    history_depth = min(1.0, len(history) / 25)
    sparse_history_risk = (1 - history_depth) * 0.35
    score = clamp(0.65 * transaction.score + sparse_history_risk)
    signals = []
    if 0 < len(history) < 3:
        signals.append(
            RiskSignal(
                type="THIN_ACCOUNT_HISTORY",
                source="ACCOUNT",
                score=clamp(sparse_history_risk),
                description=(
                    "Sender has too little payment history for a stable behavioral baseline."
                ),
                evidence={"historyCount": len(history)},
            )
        )
    return EngineResult(
        score=score, signals=signals, metadata={"historyDepth": round(history_depth, 4)}
    )


def _concentration(values: list[str]) -> float:
    if not values:
        return 0.0
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts.values()) / len(values)


def _dominant_profile(values: list[str]) -> tuple[str | None, float]:
    if not values:
        return None, 0.0
    value, count = Counter(values).most_common(1)[0]
    return value, count / len(values)


def _unique_history(
    history: list[HistoricalTransaction],
) -> list[HistoricalTransaction]:
    seen: set[str] = set()
    unique = []
    for item in history:
        if item.transaction_id not in seen:
            seen.add(item.transaction_id)
            unique.append(item)
    return unique
