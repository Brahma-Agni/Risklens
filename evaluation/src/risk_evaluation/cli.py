from __future__ import annotations

import argparse
import os
from pathlib import Path

from .evaluator import evaluate, load_jsonl, write_report


def _optional_float(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Evaluate RiskLens decisions against ground truth"
    )
    command.add_argument(
        "--labels",
        type=Path,
        default=Path(os.getenv("EVALUATION_LABELS", "data-generator/output/labels.jsonl")),
    )
    command.add_argument(
        "--results",
        type=Path,
        default=Path(os.getenv("EVALUATION_RESULTS", "data-generator/output/results.jsonl")),
    )
    command.add_argument(
        "--output-json",
        type=Path,
        default=Path(os.getenv("EVALUATION_OUTPUT_JSON", "evaluation/reports/latest.json")),
    )
    command.add_argument(
        "--output-markdown",
        type=Path,
        default=Path(os.getenv("EVALUATION_OUTPUT_MARKDOWN", "evaluation/reports/latest.md")),
    )
    command.add_argument(
        "--positive-decisions",
        default=os.getenv("EVALUATION_POSITIVE_DECISIONS", "REVIEW,HOLD,DECLINED"),
    )
    command.add_argument(
        "--score-threshold",
        type=float,
        default=_optional_float(os.getenv("EVALUATION_SCORE_THRESHOLD")),
    )
    command.add_argument(
        "--min-precision",
        type=float,
        default=float(os.getenv("EVALUATION_MIN_PRECISION", "0")),
    )
    command.add_argument(
        "--min-recall",
        type=float,
        default=float(os.getenv("EVALUATION_MIN_RECALL", "0")),
    )
    return command


def main() -> None:
    args = parser().parse_args()
    decisions = {
        item.strip().upper() for item in args.positive_decisions.split(",") if item.strip()
    }
    report = evaluate(
        load_jsonl(args.labels),
        load_jsonl(args.results),
        positive_decisions=decisions,
        score_threshold=args.score_threshold,
    )
    write_report(report, args.output_json, args.output_markdown)
    overall = report["overall"]
    print(
        f"evaluated={report['summary']['evaluated']} precision={overall['precision']:.3f} "
        f"recall={overall['recall']:.3f} f1={overall['f1']:.3f}"
    )
    print(f"json={args.output_json} markdown={args.output_markdown}")
    if overall["precision"] < args.min_precision or overall["recall"] < args.min_recall:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
