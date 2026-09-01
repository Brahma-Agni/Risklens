from risk_evaluation.calibration import calibrate_and_evaluate


def label(transaction_id: str, is_abuse: bool) -> dict:
    return {"transaction_id": transaction_id, "is_abuse": is_abuse, "scenario": "test"}


def result(transaction_id: str, score: float) -> dict:
    return {
        "transaction_id": transaction_id,
        "response": {
            "status": "REVIEW" if score >= 0.5 else "ALLOW",
            "riskScore": score,
            "riskServiceAvailable": True,
        },
    }


def test_threshold_is_selected_only_from_calibration_split() -> None:
    calibration_labels = [label("fraud", True), label("normal", False)]
    calibration_results = [result("fraud", 0.8), result("normal", 0.3)]
    holdout_labels = [label("held-fraud", True), label("held-normal", False)]
    holdout_results = [result("held-fraud", 0.1), result("held-normal", 0.9)]

    report = calibrate_and_evaluate(
        calibration_labels,
        calibration_results,
        holdout_labels,
        holdout_results,
    )

    assert report["selected_threshold"] == 0.8
    assert report["held_out_used_for_selection"] is False
    assert report["calibration"]["overall"]["f1"] == 1
    assert report["holdout"]["overall"]["f1"] == 0
