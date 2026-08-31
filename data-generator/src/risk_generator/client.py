import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True)
class StreamResult:
    transaction_id: str
    outcome: str
    status_code: int | None
    attempts: int
    response: dict[str, Any] | None = None
    error: str | None = None


class RateLimiter:
    def __init__(self, per_second: float) -> None:
        self.interval = 0.0 if per_second <= 0 else 1.0 / per_second
        self.next_allowed = 0.0
        self.lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_allowed - now)
            if delay:
                await asyncio.sleep(delay)
            self.next_allowed = max(now, self.next_allowed) + self.interval


async def stream_transactions(
    transactions: list[dict[str, Any]],
    *,
    backend_url: str,
    rate_per_second: float = 20,
    concurrency: int = 10,
    retries: int = 2,
    timeout_seconds: float = 10,
) -> list[StreamResult]:
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    limiter = RateLimiter(rate_per_second)
    semaphore = asyncio.Semaphore(concurrency)
    endpoint = f"{backend_url.rstrip('/')}/api/v1/transactions"

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:

        async def submit(payload: dict[str, Any]) -> StreamResult:
            transaction_id = str(payload.get("transactionId", "unknown"))
            async with semaphore:
                for attempt in range(1, retries + 2):
                    await limiter.wait()
                    try:
                        response = await client.post(endpoint, json=payload)
                        if response.status_code == 201:
                            return StreamResult(
                                transaction_id, "created", 201, attempt, response=response.json()
                            )
                        if response.status_code == 409:
                            return StreamResult(transaction_id, "duplicate", 409, attempt)
                        if response.status_code < 500:
                            return StreamResult(
                                transaction_id,
                                "rejected",
                                response.status_code,
                                attempt,
                                error=response.text[:500],
                            )
                    except httpx.HTTPError as error:
                        if attempt > retries:
                            return StreamResult(
                                transaction_id, "failed", None, attempt, error=str(error)
                            )
                    if attempt <= retries:
                        await asyncio.sleep(min(2 ** (attempt - 1) * 0.2, 2.0))
                return StreamResult(transaction_id, "failed", None, retries + 1)

        return list(await asyncio.gather(*(submit(payload) for payload in transactions)))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_results(path: Path, results: list[StreamResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(asdict(result), separators=(",", ":"), sort_keys=True) + "\n")
