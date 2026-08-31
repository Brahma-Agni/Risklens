import math
import statistics
from datetime import timedelta

from risk_service.models import EngineResult, HistoricalTransaction, RiskRequest, RiskSignal


def clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def transaction_engine(request: RiskRequest, history: list[HistoricalTransaction]) -> EngineResult:
    signals: list[RiskSignal] = []
    if not history:
        return EngineResult(
            score=0.35,
            signals=[
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
    amount_risk = clamp(math.log2(max(1.0, ratio)) / 4)
    if ratio >= 4:
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
    novelty_risk = max(novelty_scores, default=0.0)
    score = clamp(0.58 * amount_risk + 0.42 * novelty_risk)
    return EngineResult(
        score=score,
        signals=signals,
        metadata={
            "historyCount": len(history),
            "amountMedian": round(median, 2),
            "amountRatio": round(ratio, 2),
        },
    )


def behavior_engine(history: list[HistoricalTransaction]) -> EngineResult:
    if not history:
        return EngineResult(score=0.3, metadata={"historyCount": 0})
    adverse = {"REVIEW", "HOLD", "DECLINED", "RISK_UNAVAILABLE"}
    adverse_count = sum(item.status in adverse for item in history[:50])
    adverse_rate = adverse_count / min(50, len(history))
    receiver_concentration = _concentration([item.receiver_id for item in history[:50]])
    score = clamp(0.65 * adverse_rate + 0.35 * max(0, receiver_concentration - 0.5) * 2)
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
    if receiver_concentration >= 0.7 and len(history) >= 5:
        signals.append(
            RiskSignal(
                type="BENEFICIARY_CONCENTRATION",
                source="BEHAVIOR",
                score=clamp(receiver_concentration),
                description="Recent payments are unusually concentrated on one beneficiary.",
                evidence={"concentration": round(receiver_concentration, 3)},
            )
        )
    return EngineResult(
        score=score,
        signals=signals,
        metadata={
            "adverseRate": round(adverse_rate, 4),
            "receiverConcentration": round(receiver_concentration, 4),
        },
    )


def temporal_engine(request: RiskRequest, history: list[HistoricalTransaction]) -> EngineResult:
    five_minutes = request.timestamp - timedelta(minutes=5)
    one_hour = request.timestamp - timedelta(hours=1)
    recent_five = [item for item in history if five_minutes <= item.timestamp <= request.timestamp]
    recent_hour = [item for item in history if one_hour <= item.timestamp <= request.timestamp]
    velocity_5m = len(recent_five)
    velocity_1h = len(recent_hour)
    beneficiary_count = len({item.receiver_id for item in recent_five} | {request.receiver_id})
    velocity_risk = clamp(max(velocity_5m / 6, velocity_1h / 20))
    rotation_risk = clamp(max(0, beneficiary_count - 2) / 5)
    fragment_amount_ceiling = 5000
    fragment_payments = [
        item for item in recent_hour if item.amount <= fragment_amount_ceiling
    ]
    is_fragmented_burst = (
        request.amount <= fragment_amount_ceiling and len(fragment_payments) >= 4
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
    if velocity_5m >= 3:
        signals.append(
            RiskSignal(
                type="VELOCITY_SPIKE",
                source="TEMPORAL",
                score=velocity_risk,
                description="Sender transaction velocity is elevated within five minutes.",
                evidence={"priorFiveMinutes": velocity_5m, "priorHour": velocity_1h},
            )
        )
    if beneficiary_count >= 4:
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
        fragment_total = sum(item.amount for item in fragment_payments) + request.amount
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
            "priorFiveMinutes": velocity_5m,
            "priorHour": velocity_1h,
            "uniqueBeneficiariesFiveMinutes": beneficiary_count,
            "priorSmallPaymentsOneHour": len(fragment_payments),
            "fragmentationRisk": round(fragmentation_risk, 4),
        },
    )


def account_engine(history: list[HistoricalTransaction], transaction: EngineResult) -> EngineResult:
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
