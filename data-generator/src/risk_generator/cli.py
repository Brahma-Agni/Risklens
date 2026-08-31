import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from risk_generator.client import load_jsonl, stream_transactions, write_results
from risk_generator.exporter import export_dataset
from risk_generator.generator import GeneratorConfig, TrafficGenerator
from risk_generator.scenarios import ABUSE_SCENARIOS


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="riskgen",
        description="Generate and stream deterministic RiskLens payment scenarios.",
    )
    commands = root.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="Create transaction and ground-truth files")
    _generation_arguments(generate)

    stream = commands.add_parser("stream", help="Send a JSONL dataset to the backend")
    stream.add_argument("--input", type=Path, default=Path("output/transactions.jsonl"))
    _stream_arguments(stream)

    run = commands.add_parser("run", help="Generate a dataset and immediately stream it")
    _generation_arguments(run)
    _stream_arguments(run)
    return root


def _generation_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--count", type=int, default=int(os.getenv("DATA_GENERATOR_COUNT", "1000"))
    )
    command.add_argument(
        "--abuse-rate", type=float, default=float(os.getenv("DATA_GENERATOR_ABUSE_RATE", "0.15"))
    )
    command.add_argument("--seed", type=int, default=int(os.getenv("DATA_GENERATOR_SEED", "42")))
    command.add_argument("--accounts", type=int, default=250)
    command.add_argument("--merchants", type=int, default=40)
    command.add_argument("--duration-seconds", type=int, default=3600)
    command.add_argument("--start", type=_timestamp)
    command.add_argument("--scenarios", default="all")
    command.add_argument("--formats", default="jsonl,csv")
    command.add_argument(
        "--output", type=Path, default=Path(os.getenv("DATA_GENERATOR_OUTPUT", "output"))
    )


def _stream_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--backend-url",
        default=os.getenv("DATA_GENERATOR_BACKEND_URL", "http://localhost:8080"),
    )
    command.add_argument(
        "--rate", type=float, default=float(os.getenv("DATA_GENERATOR_RATE", "20"))
    )
    command.add_argument(
        "--concurrency", type=int, default=int(os.getenv("DATA_GENERATOR_CONCURRENCY", "10"))
    )
    command.add_argument(
        "--retries", type=int, default=int(os.getenv("DATA_GENERATOR_RETRIES", "2"))
    )
    command.add_argument(
        "--timeout", type=float, default=float(os.getenv("DATA_GENERATOR_TIMEOUT", "10"))
    )
    command.add_argument(
        "--results",
        type=Path,
        default=Path(os.getenv("DATA_GENERATOR_RESULTS", "output/stream-results.jsonl")),
    )


def _timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("start must be an ISO-8601 timestamp") from error


def _scenario_names(value: str) -> tuple[str, ...]:
    if value.strip().lower() == "all":
        return tuple(ABUSE_SCENARIOS)
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _formats(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def generate_from_args(args: argparse.Namespace):
    dataset = TrafficGenerator(
        GeneratorConfig(
            count=args.count,
            abuse_rate=args.abuse_rate,
            seed=args.seed,
            account_count=args.accounts,
            merchant_count=args.merchants,
            duration_seconds=args.duration_seconds,
            start=args.start,
            enabled_scenarios=_scenario_names(args.scenarios),
        )
    ).generate()
    manifest = export_dataset(dataset, args.output, _formats(args.formats))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return dataset


async def stream_from_args(args: argparse.Namespace, input_path: Path) -> int:
    transactions = load_jsonl(input_path)
    results = await stream_transactions(
        transactions,
        backend_url=args.backend_url,
        rate_per_second=args.rate,
        concurrency=args.concurrency,
        retries=args.retries,
        timeout_seconds=args.timeout,
    )
    write_results(args.results, results)
    counts: dict[str, int] = {}
    for result in results:
        counts[result.outcome] = counts.get(result.outcome, 0) + 1
    print(json.dumps({"submitted": len(results), "outcomes": counts}, indent=2, sort_keys=True))
    return 0 if all(item.outcome in {"created", "duplicate"} for item in results) else 1


def main() -> None:
    args = parser().parse_args()
    try:
        if args.command == "generate":
            generate_from_args(args)
            return
        if args.command == "stream":
            raise SystemExit(asyncio.run(stream_from_args(args, args.input)))
        generate_from_args(args)
        raise SystemExit(asyncio.run(stream_from_args(args, args.output / "transactions.jsonl")))
    except (ValueError, OSError) as error:
        raise SystemExit(f"riskgen: {error}") from error


if __name__ == "__main__":
    main()
