# RiskLens data generator

The data generator creates reproducible payment traffic for development,
demonstrations, and evaluation. Runtime transaction payloads exactly match the
Spring Boot API. Synthetic fraud truth is written to separate files and is never
sent to the backend.

## Scenarios

- `normal`: established account, device, IP, and spending patterns
- `shared_device_ring`: several accounts share one device and address
- `velocity_burst`: one account rapidly rotates merchants with stepped amounts
- `mule_fan_in`: unrelated senders converge on one beneficiary
- `account_takeover`: novel device/IP and abnormal high-value payments

Every run is deterministic when `--seed` and `--start` are fixed.

## Generate files

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'

riskgen generate \
  --count 1000 \
  --abuse-rate 0.15 \
  --seed 42 \
  --start 2026-01-01T00:00:00Z \
  --output output
```

Outputs include:

- `transactions.jsonl` and `transactions.csv`: backend-safe runtime payloads
- `labels.jsonl` and `labels.csv`: evaluation-only ground truth
- `manifest.json`: seed, class/scenario counts, and file checksums

## Stream to the backend

```bash
riskgen stream \
  --input output/transactions.jsonl \
  --backend-url http://localhost:8080 \
  --rate 20 \
  --concurrency 10
```

Or generate and stream in one command:

```bash
riskgen run --count 100 --abuse-rate 0.2 --backend-url http://localhost:8080
```

Retries are bounded. Duplicate transaction responses are recorded as duplicate
rather than blindly retried.

## Docker

```bash
docker compose run --rm data-generator generate --count 500 --output /app/output
docker compose run --rm data-generator run --count 50 --backend-url http://backend:8080
```

The Compose service uses the `tools` profile so it runs only on demand.
If your host user does not use UID/GID `1000`, set `DATA_GENERATOR_UID` and
`DATA_GENERATOR_GID` in the root `.env` so generated files remain writable.
