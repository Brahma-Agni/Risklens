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
