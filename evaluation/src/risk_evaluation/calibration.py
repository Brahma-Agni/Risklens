from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evaluator import evaluate


def calibrate_and_evaluate(
    calibration_labels: list[dict[str, Any]],
    calibration_results: list[dict[str, Any]],
    holdout_labels: list[dict[str, Any]],
    holdout_results: list[dict[str, Any]],
    *,
    false_positive_cost: float = 2.0,
    false_negative_cost: float = 10.0,
) -> dict[str, Any]:
    if false_positive_cost < 0 or false_negative_cost < 0:
        raise ValueError("misclassification costs must be non-negative")

    sweep = []
    for step in range(101):
        threshold = step / 100
        report = evaluate(
            calibration_labels,
            calibration_results,
            score_threshold=threshold,
        )
        row = report["overall"]
        cost = (
            row["false_positive"] * false_positive_cost
            + row["false_negative"] * false_negative_cost
        )
        sweep.append({"threshold": threshold, "weighted_cost": round(cost, 6), **row})

    selected = min(
        sweep,
        key=lambda row: (
            row["weighted_cost"],
            -row["f1"],
            -row["recall"],
            -row["precision"],
            -row["threshold"],
        ),
    )
    threshold = selected["threshold"]
    calibration = evaluate(
        calibration_labels,
        calibration_results,
        score_threshold=threshold,
    )
    holdout = evaluate(
        holdout_labels,
        holdout_results,
        score_threshold=threshold,
    )
    holdout_cost = (
        holdout["overall"]["false_positive"] * false_positive_cost
        + holdout["overall"]["false_negative"] * false_negative_cost
    )
    return {
        "method": "cost_weighted_threshold_calibration",
        "selection_split": "calibration_only",
        "held_out_used_for_selection": False,
        "costs": {
            "false_positive": false_positive_cost,
            "false_negative": false_negative_cost,
            "units": "relative_cost_units",
        },
        "selected_threshold": threshold,
        "calibration": calibration,
        "holdout": holdout,
        "holdout_weighted_cost": round(holdout_cost, 6),
        "calibration_sweep": sweep,
    }


def markdown_calibration_report(report: dict[str, Any]) -> str:
    calibration = report["calibration"]["overall"]
    holdout = report["holdout"]["overall"]
    coverage = report["holdout"]["summary"]
    costs = report["costs"]
    lines = [
        "# RiskLens held-out threshold calibration",
        "",
        f"Selected threshold: `{report['selected_threshold']:.2f}`",
        "",
        "The threshold was selected only on the calibration split. The held-out split was "
        "evaluated once after selection.",
        "",
        "## Cost assumption",
        "",
        f"- False positive: {costs['false_positive']:.2f} relative cost unit(s)",
        f"- False negative: {costs['false_negative']:.2f} relative cost unit(s)",
        "",
        "## Results",
        "",
        "| Split | Precision | Recall | F1 | Specificity | TP | FP | TN | FN |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        _metric_row("Calibration", calibration),
        _metric_row("Held-out", holdout),
        "",
        f"Held-out weighted cost: `{report['holdout_weighted_cost']:.2f}`",
        "",
        "## Held-out coverage",
        "",
        f"- Evaluated: {coverage['evaluated']} / {coverage['labels']}",
        f"- Missing results: {coverage['missing_results']}",
        f"- Risk service unavailable: {coverage['risk_unavailable']}",
        "",
        "## Held-out scenario recall",
        "",
        "| Scenario | Support | Recall | TP | FN |",
        "|---|---:|---:|---:|---:|",
    ]
    for scenario, row in report["holdout"]["by_scenario"].items():
        lines.append(
            f"| {scenario} | {row['support']} | {row['recall']:.3f} | "
            f"{row['true_positive']} | {row['false_negative']} |"
        )
    datasets = report.get("datasets")
    if datasets:
        lines.extend(["", "## Dataset provenance", ""])
        for split in ("calibration", "holdout"):
            item = datasets[split]
            lines.append(
                f"- {split.title()}: seed `{item.get('seed', 'unknown')}`, "
                f"{item.get('count', 'unknown')} rows, abuse rate "
                f"`{item.get('actual_abuse_rate', 'unknown')}`"
            )
    return "\n".join(lines) + "\n"


def write_calibration_report(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_calibration_report(report), encoding="utf-8")


def _metric_row(name: str, row: dict[str, Any]) -> str:
    return (
        f"| {name} | {row['precision']:.3f} | {row['recall']:.3f} | "
        f"{row['f1']:.3f} | {row['specificity']:.3f} | {row['true_positive']} | "
        f"{row['false_positive']} | {row['true_negative']} | {row['false_negative']} |"
    )
