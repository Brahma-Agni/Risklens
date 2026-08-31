from datetime import datetime, timedelta, timezone

import pytest

from risk_generator.generator import GeneratorConfig, TrafficGenerator

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def build(seed: int = 42):
    return TrafficGenerator(
        GeneratorConfig(
            count=100,
            abuse_rate=0.2,
            seed=seed,
            start=START,
            duration_seconds=3600,
        )
    ).generate()


def test_generation_is_exact_and_deterministic() -> None:
    first = build()
    second = build()

    assert len(first.events) == 100
    assert first.abuse_count == 20
    assert [event.transaction.backend_payload() for event in first.events] == [
        event.transaction.backend_payload() for event in second.events
    ]
    assert [event.truth.record() for event in first.events] == [
        event.truth.record() for event in second.events
    ]


def test_different_seed_changes_dataset() -> None:
    assert [event.transaction.backend_payload() for event in build(1).events] != [
        event.transaction.backend_payload() for event in build(2).events
    ]


def test_all_events_stay_inside_requested_window() -> None:
    dataset = TrafficGenerator(
        GeneratorConfig(
            count=40,
            abuse_rate=1,
            seed=99,
            start=START,
            duration_seconds=60,
        )
    ).generate()
    end = START + timedelta(seconds=60)
    assert all(START <= event.transaction.timestamp < end for event in dataset.events)


def test_runtime_payload_never_contains_ground_truth() -> None:
    forbidden = {"is_abuse", "scenario", "expected_risk_band", "ring_id"}
    for event in build().events:
        assert forbidden.isdisjoint(event.transaction.backend_payload())


def test_shared_device_ring_has_coordinated_entities() -> None:
    dataset = TrafficGenerator(
        GeneratorConfig(
            count=8,
            abuse_rate=1,
            seed=7,
            start=START,
            enabled_scenarios=("shared_device_ring",),
        )
    ).generate()
    assert {event.truth.scenario for event in dataset.events} == {"shared_device_ring"}
    ring_ids = {event.truth.ring_id for event in dataset.events}
    for ring_id in ring_ids:
        ring = [event for event in dataset.events if event.truth.ring_id == ring_id]
        assert len({event.transaction.device_id for event in ring}) == 1
        assert len({event.transaction.sender_id for event in ring}) == len(ring)


@pytest.mark.parametrize(
    ("field", "value"),
    [("count", 0), ("abuse_rate", 1.1), ("account_count", 2), ("duration_seconds", 5)],
)
def test_invalid_configuration_is_rejected(field: str, value: int | float) -> None:
    values = {"count": 10, "start": START}
    values[field] = value
    with pytest.raises(ValueError):
        TrafficGenerator(GeneratorConfig(**values))
