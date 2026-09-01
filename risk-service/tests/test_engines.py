from datetime import timedelta

from risk_service.engines import behavior_engine, temporal_engine, transaction_engine
from risk_service.services import relationship_engine

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
    }


def test_temporal_window_counts_include_current_transaction() -> None:
    current = request()
    history = [
        historical(
            transaction_id=f"TX-{index}",
            receiver_id=f"MERCHANT-{index}",
            timestamp=current.timestamp - timedelta(seconds=20 * (index + 1)),
        )
        for index in range(3)
    ]

    result = temporal_engine(current, history)

    assert result.metadata["transactionsFiveMinutes"] == 4
    assert any(signal.type == "VELOCITY_SPIKE" for signal in result.signals)


def test_transaction_engine_detects_persistent_identity_profile_shift() -> None:
    history = [
        historical(
            transaction_id=f"TX-HOME-{index}",
            amount=2000,
            device_id="DEV-HOME",
            ip_address="10.0.0.1",
        )
        for index in range(12)
    ] + [
        historical(
            transaction_id="TX-ATTACK-PRIOR",
            amount=45000,
            device_id="DEV-ATTACKER",
            ip_address="10.9.9.9",
        )
    ]

    result = transaction_engine(
        request(amount=45000, deviceId="DEV-ATTACKER", ipAddress="10.9.9.9"), history
    )

    assert result.score >= 0.8
    assert {"DEVICE_PROFILE_SHIFT", "NETWORK_PROFILE_SHIFT"}.issubset(
        {signal.type for signal in result.signals}
    )


def test_transaction_engine_detects_corroborated_identity_anomaly_without_history() -> None:
    result = transaction_engine(
        request(
            locationCountry="SG",
            context={
                "impossibleTravel": True,
                "deviceTrust": "NEW",
                "ipType": "DATACENTER",
            },
        ),
        [],
    )

    assert result.score == 0.88
    assert "CORROBORATED_IDENTITY_ANOMALY" in {signal.type for signal in result.signals}


def test_transaction_engine_does_not_hold_on_impossible_travel_alone() -> None:
    result = transaction_engine(
        request(locationCountry="SG", context={"impossibleTravel": True}),
        [],
    )

    assert result.score == 0.65


def test_temporal_engine_detects_fragmented_small_payment_burst() -> None:
    current = request(amount=4500, receiverId="MERCHANT-FINAL")
    history = [
        historical(
            transaction_id=f"TX-FRAGMENT-{index}",
            amount=4500 + index * 100,
            receiver_id="MERCHANT-FINAL",
            timestamp=current.timestamp - timedelta(minutes=index + 1),
        )
        for index in range(4)
    ]

    result = temporal_engine(current, history)

    signal = next(signal for signal in result.signals if signal.type == "FRAGMENTED_PAYMENT_BURST")
    assert result.score >= 0.78
    assert signal.evidence["priorSmallPayments"] == 4


def test_behavior_engine_scores_adverse_history() -> None:
    history = [
        historical(transaction_id=f"TX-{index}", status="HOLD" if index < 8 else "ALLOW")
        for index in range(10)
    ]
    result = behavior_engine(history)
    assert result.score >= 0.3
    assert result.signals[0].type == "ADVERSE_DECISION_HISTORY"


def test_behavior_engine_detects_repeated_lifecycle_failures() -> None:
    history = [
        historical(
            transaction_id=f"TX-FAIL-{index}",
            authentication_status="FAILED" if index < 4 else "SUCCESS",
        )
        for index in range(6)
    ]

    result = behavior_engine(history)

    assert result.score >= 0.5
    assert any(signal.type == "REPEATED_LIFECYCLE_FAILURES" for signal in result.signals)


def test_relationship_engine_detects_corroborated_ring() -> None:
    result = relationship_engine(
        request(paymentInstrumentId="UPI-SHARED"),
        device_accounts=4,
        ip_accounts=5,
        instrument_accounts=3,
        beneficiary_senders=5,
        beneficiary_payments=6,
        beneficiary_amount=48_000,
    )

    assert result.score >= 0.85
    assert {
        "SHARED_DEVICE",
        "SHARED_PAYMENT_INSTRUMENT",
        "MULE_FAN_IN",
        "MULTI_SOURCE_AMOUNT_SPLITTING",
    }.issubset({signal.type for signal in result.signals})


def test_relationship_engine_does_not_treat_merchant_fan_in_as_mule_activity() -> None:
    result = relationship_engine(
        request(merchantCategory="GROCERY"),
        device_accounts=1,
        ip_accounts=1,
        instrument_accounts=1,
        beneficiary_senders=50,
        beneficiary_payments=100,
        beneficiary_amount=250_000,
    )

    assert result.score == 0
    assert "MULE_FAN_IN" not in {signal.type for signal in result.signals}
    assert "MULTI_SOURCE_AMOUNT_SPLITTING" not in {signal.type for signal in result.signals}


def test_shared_ip_alone_is_capped_as_weak_evidence() -> None:
    result = relationship_engine(
        request(context={"ipType": "MOBILE"}),
        device_accounts=1,
        ip_accounts=100,
        instrument_accounts=1,
        beneficiary_senders=1,
        beneficiary_payments=1,
        beneficiary_amount=1500,
    )

    assert result.score == 0.45
