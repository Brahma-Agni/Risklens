from datetime import timedelta

from risk_service.engines import behavior_engine, temporal_engine, transaction_engine

from .fakes import historical, request


def test_transaction_engine_detects_amount_and_novelty() -> None:
    history = [historical(transaction_id=f"TX-{index}") for index in range(10)]
    result = transaction_engine(
        request(amount=18000, deviceId="DEV-NOVEL", ipAddress="10.8.8.8"), history
    )
    types = {signal.type for signal in result.signals}
    assert result.score >= 0.65
    assert {"AMOUNT_DEVIATION", "NOVEL_DEVICE", "NOVEL_IP"}.issubset(types)


def test_temporal_engine_detects_velocity_and_rotation() -> None:
    current = request()
    history = [
        historical(
            transaction_id=f"TX-{index}",
            receiver_id=f"MERCHANT-{index}",
            timestamp=current.timestamp - timedelta(seconds=30 * (index + 1)),
        )
        for index in range(5)
    ]
    result = temporal_engine(current, history)
    assert result.score >= 0.6
    assert {signal.type for signal in result.signals} == {
        "VELOCITY_SPIKE",
        "BENEFICIARY_ROTATION",
        "FRAGMENTED_PAYMENT_BURST",
    }


def test_temporal_engine_detects_fragmented_small_payment_burst() -> None:
    current = request(amount=299, receiverId="MERCHANT-FINAL")
    history = [
        historical(
            transaction_id=f"TX-FRAGMENT-{index}",
            amount=199 + index * 25,
            receiver_id=f"MERCHANT-{index % 2}",
            timestamp=current.timestamp - timedelta(minutes=index + 1),
        )
        for index in range(4)
    ]

    result = temporal_engine(current, history)

    signal = next(
        signal for signal in result.signals if signal.type == "FRAGMENTED_PAYMENT_BURST"
    )
    assert result.score >= 0.78
    assert signal.evidence["priorSmallPayments"] == 4


def test_behavior_engine_scores_adverse_history() -> None:
    history = [
        historical(transaction_id=f"TX-{index}", status="HOLD" if index < 8 else "ALLOW")
        for index in range(10)
    ]
    result = behavior_engine(history)
    assert result.score >= 0.5
    assert result.signals[0].type == "ADVERSE_DECISION_HISTORY"
