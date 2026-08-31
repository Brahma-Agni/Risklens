import random
from dataclasses import dataclass
from datetime import datetime, timezone

from risk_generator.entities import create_accounts, create_merchants
from risk_generator.models import Dataset, GeneratedEvent
from risk_generator.scenarios import ABUSE_SCENARIOS, IdFactory, normal_payment


@dataclass(frozen=True)
class GeneratorConfig:
    count: int = 1000
    abuse_rate: float = 0.15
    seed: int = 42
    account_count: int = 250
    merchant_count: int = 40
    duration_seconds: int = 3600
    start: datetime | None = None
    enabled_scenarios: tuple[str, ...] = tuple(ABUSE_SCENARIOS)

    def validate(self) -> None:
        if self.count < 1:
            raise ValueError("count must be at least 1")
        if not 0 <= self.abuse_rate <= 1:
            raise ValueError("abuse_rate must be between 0 and 1")
        if self.account_count < 10:
            raise ValueError("account_count must be at least 10")
        if self.merchant_count < 3:
            raise ValueError("merchant_count must be at least 3")
        if self.duration_seconds < 60:
            raise ValueError("duration_seconds must be at least 60")
        unknown = set(self.enabled_scenarios) - set(ABUSE_SCENARIOS)
        if unknown:
            raise ValueError(f"unknown scenarios: {', '.join(sorted(unknown))}")
        if self.abuse_rate > 0 and not self.enabled_scenarios:
            raise ValueError("at least one abuse scenario is required when abuse_rate is positive")


class TrafficGenerator:
    def __init__(self, config: GeneratorConfig) -> None:
        config.validate()
        self.config = config

    def generate(self) -> Dataset:
        rng = random.Random(self.config.seed)
        start = self.config.start or datetime.now(timezone.utc).replace(microsecond=0)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        accounts = create_accounts(self.config.account_count, rng)
        merchants = create_merchants(self.config.merchant_count, rng)
        ids = IdFactory(self.config.seed)

        abuse_target = round(self.config.count * self.config.abuse_rate)
        normal_target = self.config.count - abuse_target
        events: list[GeneratedEvent] = normal_payment(
            normal_target,
            rng=rng,
            accounts=accounts,
            merchants=merchants,
            start=start,
            duration_seconds=self.config.duration_seconds,
            ids=ids,
            batch_index=0,
        )

        generated_abuse = 0
        batch_index = 0
        scenario_names = list(self.config.enabled_scenarios)
        while generated_abuse < abuse_target:
            scenario_name = scenario_names[batch_index % len(scenario_names)]
            scenario, (minimum, maximum) = ABUSE_SCENARIOS[scenario_name]
            remaining = abuse_target - generated_abuse
            batch_size = min(remaining, rng.randint(minimum, maximum))
            events.extend(
                scenario(
                    batch_size,
                    rng=rng,
                    accounts=accounts,
                    merchants=merchants,
                    start=start,
                    duration_seconds=self.config.duration_seconds,
                    ids=ids,
                    batch_index=batch_index + 1,
                )
            )
            generated_abuse += batch_size
            batch_index += 1

        events.sort(
            key=lambda event: (event.transaction.timestamp, event.transaction.transaction_id)
        )
        return Dataset(
            events=events,
            seed=self.config.seed,
            requested_abuse_rate=self.config.abuse_rate,
            started_at=start,
            duration_seconds=self.config.duration_seconds,
        )
