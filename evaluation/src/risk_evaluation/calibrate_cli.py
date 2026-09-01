from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .calibration import calibrate_and_evaluate, write_calibration_report
from .evaluator import load_jsonl


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Select a risk threshold on calibration data and evaluate held-out data"
    )
    command.add_argument("--calibration-labels", type=Path, required=True)
    command.add_argument("--calibration-results", type=Path, required=True)
    command.add_argument("--holdout-labels", type=Path, required=True)
    command.add_argument("--holdout-results", type=Path, required=True)
    command.add_argument("--false-positive-cost", type=float, default=2.0)
    command.add_argument("--false-negative-cost", type=float, default=10.0)
    command.add_argument(
        "--output-json", type=Path, default=Path("evaluation/reports/calibration.json")
    )
    command.add_argument(
        "--output-markdown", type=Path, default=Path("evaluation/reports/calibration.md")
    )
    return command


def main() -> None:
    args = parser().parse_args()
    report = calibrate_and_evaluate(
        load_jsonl(args.calibration_labels),
        load_jsonl(args.calibration_results),
        load_jsonl(args.holdout_labels),
        load_jsonl(args.holdout_results),
        false_positive_cost=args.false_positive_cost,
        false_negative_cost=args.false_negative_cost,
    )
    report["datasets"] = {
        "calibration": _provenance(args.calibration_labels, args.calibration_results),
        "holdout": _provenance(args.holdout_labels, args.holdout_results),
    }
    write_calibration_report(report, args.output_json, args.output_markdown)
    holdout = report["holdout"]["overall"]
    print(
        f"threshold={report['selected_threshold']:.2f} "
        f"heldout_precision={holdout['precision']:.3f} "
        f"heldout_recall={holdout['recall']:.3f} heldout_f1={holdout['f1']:.3f}"
    )


def _provenance(labels_path: Path, results_path: Path) -> dict[str, object]:
    manifest_path = labels_path.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    return {
        "seed": manifest.get("seed"),
        "count": manifest.get("count"),
        "actual_abuse_rate": manifest.get("actual_abuse_rate"),
        "labels_path": str(labels_path.resolve()),
        "labels_sha256": _sha256(labels_path),
        "results_path": str(results_path.resolve()),
        "results_sha256": _sha256(results_path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
