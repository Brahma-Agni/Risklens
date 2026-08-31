import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from risk_generator import __version__
from risk_generator.models import Dataset

TRANSACTION_FIELDS = (
    "transactionId",
    "senderId",
    "receiverId",
    "amount",
    "currency",
    "deviceId",
    "ipAddress",
    "paymentMethod",
    "timestamp",
)
LABEL_FIELDS = (
    "transaction_id",
    "is_abuse",
    "scenario",
    "expected_risk_band",
    "explanation",
    "ring_id",
    "related_entities",
)


def export_dataset(dataset: Dataset, output_dir: Path, formats: set[str]) -> dict[str, Any]:
    unsupported = formats - {"jsonl", "csv"}
    if unsupported:
        raise ValueError(f"unsupported formats: {', '.join(sorted(unsupported))}")
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []

    if "jsonl" in formats:
        transactions = output_dir / "transactions.jsonl"
        labels = output_dir / "labels.jsonl"
        _write_jsonl(
            transactions, [event.transaction.backend_payload() for event in dataset.events]
        )
        _write_jsonl(labels, [event.truth.record() for event in dataset.events])
        files.extend((transactions, labels))

    if "csv" in formats:
        transactions_csv = output_dir / "transactions.csv"
        labels_csv = output_dir / "labels.csv"
        with transactions_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRANSACTION_FIELDS)
            writer.writeheader()
            writer.writerows(event.transaction.backend_payload() for event in dataset.events)
        with labels_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
            writer.writeheader()
            for event in dataset.events:
                record = event.truth.record()
                record["related_entities"] = json.dumps(record["related_entities"])
                writer.writerow(record)
        files.extend((transactions_csv, labels_csv))

    manifest = {
        "generator_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": dataset.seed,
        "count": len(dataset.events),
        "abuse_count": dataset.abuse_count,
        "normal_count": len(dataset.events) - dataset.abuse_count,
        "requested_abuse_rate": dataset.requested_abuse_rate,
        "actual_abuse_rate": dataset.abuse_count / len(dataset.events),
        "started_at": dataset.started_at.isoformat(),
        "duration_seconds": dataset.duration_seconds,
        "scenario_counts": dataset.scenario_counts,
        "files": {
            path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size} for path in files
        },
        "ground_truth_is_separate": True,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
