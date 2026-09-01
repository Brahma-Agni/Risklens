from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Counts:
    true_positive: int = 0
    false_positive: int = 0
    true_negative: int = 0
    false_negative: int = 0

    @property
    def total(self) -> int:
        return self.true_positive + self.false_positive + self.true_negative + self.false_negative


def _divide(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def metrics(counts: Counts) -> dict[str, float | int]:
    precision = _divide(counts.true_positive, counts.true_positive + counts.false_positive)
    recall = _divide(counts.true_positive, counts.true_positive + counts.false_negative)
    return {
        **asdict(counts),
        "support": counts.total,
        "precision": precision,
        "recall": recall,
        "f1": _divide(2 * precision * recall, precision + recall),
        "specificity": _divide(counts.true_negative, counts.true_negative + counts.false_positive),
        "accuracy": _divide(
            counts.true_positive + counts.true_negative,
            counts.total,
        ),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                message = f"Invalid JSON in {path} at line {line_number}: {error}"
                raise ValueError(message) from error
            if not isinstance(value, dict):
                raise ValueError(f"Expected an object in {path} at line {line_number}")
            records.append(value)
    return records


def _transaction_id(record: dict[str, Any]) -> str | None:
    value = record.get("transaction_id", record.get("transactionId"))
    return str(value) if value else None


def _response(result: dict[str, Any]) -> dict[str, Any] | None:
    value = result.get("response")
    return value if isinstance(value, dict) else None


def _decision(result: dict[str, Any]) -> str | None:
    response = _response(result)
    if not response:
        return None
    value = response.get("status", response.get("recommendedAction"))
    return str(value).upper() if value else None


def _score(result: dict[str, Any]) -> float | None:
    response = _response(result)
    if not response:
        return None
    value = response.get("riskScore")
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    return min(1.0, max(0.0, score))


def _counts(rows: Iterable[tuple[bool, bool]]) -> Counts:
    tp = fp = tn = fn = 0
    for actual, predicted in rows:
        if actual and predicted:
            tp += 1
        elif predicted:
            fp += 1
        elif actual:
            fn += 1
        else:
            tn += 1
    return Counts(tp, fp, tn, fn)


def evaluate(
    labels: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    positive_decisions: set[str] | None = None,
    score_threshold: float | None = None,
) -> dict[str, Any]:
    positive_decisions = positive_decisions or {"REVIEW", "HOLD", "DECLINED"}
    labels_by_id = {
        transaction_id: label
        for label in labels
        if (transaction_id := _transaction_id(label)) is not None
    }
    results_by_id: dict[str, dict[str, Any]] = {}
    duplicate_result_ids: set[str] = set()
    for result in results:
        transaction_id = _transaction_id(result)
        if transaction_id is None:
            continue
        if transaction_id in results_by_id:
            duplicate_result_ids.add(transaction_id)
        results_by_id[transaction_id] = result

    joined: list[tuple[dict[str, Any], dict[str, Any], bool, bool, float | None]] = []
    decision_counts: dict[str, int] = defaultdict(int)
    unavailable = 0
    matched = 0
    for transaction_id, label in labels_by_id.items():
        result = results_by_id.get(transaction_id)
        if not result or not _response(result):
            continue
        matched += 1
        decision = _decision(result)
        score = _score(result)
        if decision:
            decision_counts[decision] += 1
        if decision == "RISK_UNAVAILABLE" or not bool(
            _response(result).get("riskServiceAvailable", True)
        ):
            unavailable += 1
            continue
        actual = bool(label.get("is_abuse", label.get("isAbuse", False)))
        predicted = (
            score >= score_threshold
            if score_threshold is not None and score is not None
            else decision in positive_decisions
        )
        joined.append((label, result, actual, predicted, score))

    overall = metrics(_counts((actual, predicted) for _, _, actual, predicted, _ in joined))
    scenario_rows: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    for label, _, actual, predicted, _ in joined:
        scenario_rows[str(label.get("scenario", "unknown"))].append((actual, predicted))

    thresholds: list[dict[str, Any]] = []
    scored = [(actual, score) for _, _, actual, _, score in joined if score is not None]
    for step in range(21):
        threshold = step / 20
        row = metrics(_counts((actual, score >= threshold) for actual, score in scored))
        thresholds.append({"threshold": threshold, **row})
    best_threshold = max(thresholds, key=lambda row: (row["f1"], row["recall"])) if scored else None

    return {
        "summary": {
            "labels": len(labels_by_id),
            "results": len(results_by_id),
            "matched_results": matched,
            "evaluated": len(joined),
            "coverage": _divide(len(joined), len(labels_by_id)),
            "result_coverage": _divide(matched, len(labels_by_id)),
            "missing_results": len(set(labels_by_id) - set(results_by_id)),
            "results_without_labels": len(set(results_by_id) - set(labels_by_id)),
            "duplicate_result_ids": len(duplicate_result_ids),
            "risk_unavailable": unavailable,
        },
        "configuration": {
            "positive_decisions": sorted(positive_decisions),
            "score_threshold": score_threshold,
        },
        "overall": overall,
        "decisions": dict(sorted(decision_counts.items())),
        "by_scenario": {
            scenario: metrics(_counts(rows)) for scenario, rows in sorted(scenario_rows.items())
        },
        "best_score_threshold": best_threshold,
        "threshold_sweep": thresholds,
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    overall = report["overall"]
    lines = [
        "# RiskLens evaluation report",
        "",
        "## Coverage",
        "",
        f"- Labels: {summary['labels']}",
        f"- Matched results: {summary['matched_results']} ({summary['result_coverage']:.2%})",
        f"- Classifier evaluations: {summary['evaluated']} ({summary['coverage']:.2%})",
        f"- Missing results: {summary['missing_results']}",
        f"- Risk service unavailable: {summary['risk_unavailable']}",
        "",
        "## Overall classification",
        "",
        "| Precision | Recall | F1 | Specificity | Accuracy | TP | FP | TN | FN |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {overall['precision']:.3f} | {overall['recall']:.3f} | "
            f"{overall['f1']:.3f} | {overall['specificity']:.3f} | "
            f"{overall['accuracy']:.3f} | {overall['true_positive']} | "
            f"{overall['false_positive']} | {overall['true_negative']} | "
            f"{overall['false_negative']} |"
        ),
        "",
        "## Scenario breakdown",
        "",
        "| Scenario | Support | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for scenario, row in report["by_scenario"].items():
        lines.append(
            f"| {scenario} | {row['support']} | {row['precision']:.3f} | "
            f"{row['recall']:.3f} | {row['f1']:.3f} |"
        )
    best = report.get("best_score_threshold")
    if best:
        lines.extend(
            [
                "",
                "## Score threshold",
                "",
                f"Best sampled F1 threshold: `{best['threshold']:.2f}` "
                f"(precision {best['precision']:.3f}, recall {best['recall']:.3f}, "
                f"F1 {best['f1']:.3f}).",
            ]
        )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(report), encoding="utf-8")
