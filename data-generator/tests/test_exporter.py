import json
from datetime import datetime, timezone

from risk_generator.exporter import export_dataset
from risk_generator.generator import GeneratorConfig, TrafficGenerator


def test_export_writes_separate_runtime_and_label_files(tmp_path) -> None:
    dataset = TrafficGenerator(
        GeneratorConfig(
            count=25,
            abuse_rate=0.2,
            seed=11,
            start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    ).generate()
    manifest = export_dataset(dataset, tmp_path, {"jsonl", "csv"})

    transaction_rows = [
        json.loads(line) for line in (tmp_path / "transactions.jsonl").read_text().splitlines()
    ]
    label_rows = [json.loads(line) for line in (tmp_path / "labels.jsonl").read_text().splitlines()]
    assert len(transaction_rows) == len(label_rows) == 25
    assert "is_abuse" not in transaction_rows[0]
    assert "is_abuse" in label_rows[0]
    assert manifest["ground_truth_is_separate"] is True
    assert manifest["abuse_count"] == 5
    assert set(manifest["files"]) == {
        "transactions.jsonl",
        "labels.jsonl",
        "transactions.csv",
        "labels.csv",
    }


def test_manifest_checksums_are_reproducible_for_dataset_files(tmp_path) -> None:
    config = GeneratorConfig(
        count=10,
        seed=5,
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    dataset = TrafficGenerator(config).generate()
    first = export_dataset(dataset, tmp_path / "one", {"jsonl"})
    second = export_dataset(dataset, tmp_path / "two", {"jsonl"})
    assert first["files"] == second["files"]
