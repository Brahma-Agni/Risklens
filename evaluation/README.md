# RiskLens evaluation

This package measures backend decisions against the data generator's separate
ground-truth labels. It never sends labels into the scoring path.

It reports coverage, availability, confusion-matrix counts, precision, recall,
F1, specificity, accuracy, per-scenario results, and a score-threshold sweep.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
risk-evaluate \
  --labels ../data-generator/output/labels.jsonl \
  --results ../data-generator/output/results.jsonl
```

From the repository root, `make evaluate` uses the paths and quality gates in
the root `.env`. Reports are written to `evaluation/reports/latest.json` and
`evaluation/reports/latest.md` by default. Set `EVALUATION_MIN_PRECISION` and
`EVALUATION_MIN_RECALL` to make the command exit with status 2 when a quality
gate is missed.

For threshold calibration, keep entity namespaces separate between the two
splits and choose the threshold only on calibration data:

```bash
risk-calibrate \
  --calibration-labels ../data-generator/output/calibration-final/labels.jsonl \
  --calibration-results ../data-generator/output/calibration-final/results.jsonl \
  --holdout-labels ../data-generator/output/heldout-locked/labels.jsonl \
  --holdout-results ../data-generator/output/heldout-locked/results.jsonl \
  --false-positive-cost 2 \
  --false-negative-cost 10 \
  --output-json reports/heldout-calibration.json \
  --output-markdown reports/heldout-calibration.md
```

The default relative costs are 2 for an unnecessary analyst review and 10 for
a missed fraudulent payment. Change them only from an explicit business-cost
assumption, then lock them before evaluating a fresh held-out split.
