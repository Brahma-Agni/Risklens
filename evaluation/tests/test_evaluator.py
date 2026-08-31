from risk_evaluation.evaluator import evaluate, markdown_report


def label(transaction_id: str, is_abuse: bool, scenario: str = "normal") -> dict:
    return {"transaction_id": transaction_id, "is_abuse": is_abuse, "scenario": scenario}


def result(transaction_id: str, status: str, score: float) -> dict:
    return {
        "transaction_id": transaction_id,
        "outcome": "created",
        "response": {
            "status": status,
            "riskScore": score,
            "riskServiceAvailable": True,
        },
    }


def test_decision_metrics_and_scenarios() -> None:
    report = evaluate(
        [
            label("one", True, "ring"),
            label("two", True, "takeover"),
            label("three", False),
            label("four", False),
        ],
        [
            result("one", "DECLINED", 0.98),
            result("two", "ALLOW", 0.4),
            result("three", "REVIEW", 0.7),
            result("four", "ALLOW", 0.2),
        ],
    )
    assert report["overall"]["true_positive"] == 1
    assert report["overall"]["false_positive"] == 1
    assert report["overall"]["true_negative"] == 1
    assert report["overall"]["false_negative"] == 1
    assert report["summary"]["coverage"] == 1
    assert report["by_scenario"]["ring"]["recall"] == 1
    assert "RiskLens evaluation report" in markdown_report(report)


def test_score_threshold_and_missing_results() -> None:
    report = evaluate(
        [label("one", True), label("missing", False)],
        [result("one", "ALLOW", 0.9), result("extra", "HOLD", 0.9)],
        score_threshold=0.8,
    )
    assert report["overall"]["true_positive"] == 1
    assert report["summary"]["missing_results"] == 1
    assert report["summary"]["results_without_labels"] == 1


def test_unavailable_results_are_not_classification_failures() -> None:
    unavailable = result("one", "RISK_UNAVAILABLE", 0.0)
    unavailable["response"]["riskServiceAvailable"] = False
    report = evaluate([label("one", True)], [unavailable])
    assert report["summary"]["matched_results"] == 1
    assert report["summary"]["risk_unavailable"] == 1
    assert report["summary"]["evaluated"] == 0
    assert report["overall"]["support"] == 0
