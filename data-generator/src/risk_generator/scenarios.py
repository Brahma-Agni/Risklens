import random
from collections.abc import Callable
from datetime import datetime, timedelta

from risk_generator.entities import INDIA_LOCATIONS, private_ip
from risk_generator.models import Account, GeneratedEvent, GroundTruth, Merchant, Transaction


class IdFactory:
    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.index = 0

    def next(self) -> str:
        self.index += 1
        return f"TX-SYN-{self.seed}-{self.index:07d}"


def burst_timeline(
    *,
    rng: random.Random,
    start: datetime,
    duration_seconds: int,
    count: int,
    minimum_step: int,
    maximum_step: int,
) -> tuple[datetime, int]:
    if count <= 1:
        return start + timedelta(seconds=rng.randrange(max(1, duration_seconds))), 0
    fitting_step = max(1, (duration_seconds - 1) // (count - 1))
    step = min(rng.randint(minimum_step, maximum_step), fitting_step)
    span = step * (count - 1)
    available_start_seconds = max(1, duration_seconds - span)
    return start + timedelta(seconds=rng.randrange(available_start_seconds)), step


def normal_payment(
    count: int,
    *,
    rng: random.Random,
    accounts: list[Account],
    merchants: list[Merchant],
    start: datetime,
    duration_seconds: int,
    ids: IdFactory,
    batch_index: int,
) -> list[GeneratedEvent]:
    del batch_index
    events = []
    for _ in range(count):
        account = rng.choice(accounts)
        merchant = rng.choice(merchants)
        legitimate_travel = rng.random() < 0.08
        city, state = (account.home_city, account.home_state)
        if legitimate_travel:
            alternatives = [item for item in INDIA_LOCATIONS if item[0] != account.home_city]
            city, state = rng.choice(alternatives)
        baseline = (account.typical_amount + merchant.typical_amount) / 2
        amount = max(10.0, min(150000.0, rng.lognormvariate(0, 0.35) * baseline))
        transaction = Transaction(
            transaction_id=ids.next(),
            sender_id=account.account_id,
            receiver_id=merchant.merchant_id,
            amount=amount,
            currency="INR",
            device_id=account.home_device_id,
            ip_address=account.home_ip_address,
            payment_method=account.payment_method,
            timestamp=start + timedelta(seconds=rng.randrange(max(1, duration_seconds))),
            location_city=city,
            location_state=state,
            merchant_category=merchant.category,
            context={
                "ipType": "MOBILE" if legitimate_travel else "RESIDENTIAL",
                "deviceTrust": "TRUSTED",
                "locationSource": "DEVICE",
                "legitimateTravel": legitimate_travel,
            },
        )
        events.append(
            GeneratedEvent(
                transaction,
                GroundTruth(
                    transaction_id=transaction.transaction_id,
                    is_abuse=False,
                    scenario="normal",
                    expected_risk_band="LOW",
                    explanation="Established account, device, and payment pattern.",
                    related_entities=[account.account_id, merchant.merchant_id],
                ),
            )
        )
    return events


def shared_device_ring(
    count: int,
    *,
    rng: random.Random,
    accounts: list[Account],
    merchants: list[Merchant],
    start: datetime,
    duration_seconds: int,
    ids: IdFactory,
    batch_index: int,
) -> list[GeneratedEvent]:
    ring_id = f"RING-DEVICE-{ids.seed}-{batch_index:04d}"
    device = f"DEV-RING-{ids.seed}-{batch_index:04d}"
    ip_address = private_ip(batch_index, subnet=30 + ids.seed % 200)
    selected_accounts = rng.sample(accounts, k=min(count, len(accounts)))
    selected_merchants = rng.sample(merchants, k=min(3, len(merchants)))
    base, step = burst_timeline(
        rng=rng,
        start=start,
        duration_seconds=duration_seconds,
        count=count,
        minimum_step=8,
        maximum_step=20,
    )
    events = []
    for index in range(count):
        account = selected_accounts[index % len(selected_accounts)]
        merchant = selected_merchants[index % len(selected_merchants)]
        transaction = Transaction(
            ids.next(),
            account.account_id,
            merchant.merchant_id,
            round(rng.uniform(18000, 68000), 2),
            "INR",
            device,
            ip_address,
            rng.choice(("UPI", "CARD")),
            base + timedelta(seconds=index * step),
            location_city=account.home_city,
            location_state=account.home_state,
            merchant_category=merchant.category,
            context={
                "ipType": "PROXY",
                "deviceTrust": "NEW",
                "locationSource": "IP",
            },
        )
        events.append(
            GeneratedEvent(
                transaction,
                GroundTruth(
                    transaction.transaction_id,
                    True,
                    "shared_device_ring",
                    "CRITICAL",
                    "Multiple accounts rapidly transact through one device and network address.",
                    ring_id,
                    [device, ip_address, account.account_id, merchant.merchant_id],
                ),
            )
        )
    return events


def velocity_burst(
    count: int,
    *,
    rng: random.Random,
    accounts: list[Account],
    merchants: list[Merchant],
    start: datetime,
    duration_seconds: int,
    ids: IdFactory,
    batch_index: int,
) -> list[GeneratedEvent]:
    ring_id = f"BURST-{ids.seed}-{batch_index:04d}"
    account = rng.choice(accounts)
    base, step = burst_timeline(
        rng=rng,
        start=start,
        duration_seconds=duration_seconds,
        count=count,
        minimum_step=5,
        maximum_step=8,
    )
    events = []
    for index in range(count):
        merchant = merchants[(batch_index + index) % len(merchants)]
        transaction = Transaction(
            ids.next(),
            account.account_id,
            merchant.merchant_id,
            round(6500 * (1.33**index), 2),
            "INR",
            account.home_device_id,
            account.home_ip_address,
            account.payment_method,
            base + timedelta(seconds=index * step),
            location_city=account.home_city,
            location_state=account.home_state,
            merchant_category=merchant.category,
            context={
                "ipType": "RESIDENTIAL",
                "deviceTrust": "TRUSTED",
                "locationSource": "DEVICE",
            },
        )
        events.append(
            GeneratedEvent(
                transaction,
                GroundTruth(
                    transaction.transaction_id,
                    True,
                    "velocity_burst",
                    "HIGH",
                    (
                        "One account attempts rapidly increasing payments across rotating "
                        "beneficiaries."
                    ),
                    ring_id,
                    [account.account_id, account.home_device_id, merchant.merchant_id],
                ),
            )
        )
    return events


def mule_fan_in(
    count: int,
    *,
    rng: random.Random,
    accounts: list[Account],
    merchants: list[Merchant],
    start: datetime,
    duration_seconds: int,
    ids: IdFactory,
    batch_index: int,
) -> list[GeneratedEvent]:
    del merchants
    ring_id = f"RING-MULE-{ids.seed}-{batch_index:04d}"
    receiver = f"MULE-SYN-{ids.seed}-{batch_index:04d}"
    selected = rng.sample(accounts, k=min(count, len(accounts)))
    base, step = burst_timeline(
        rng=rng,
        start=start,
        duration_seconds=duration_seconds,
        count=count,
        minimum_step=15,
        maximum_step=30,
    )
    events = []
    for index in range(count):
        account = selected[index % len(selected)]
        transaction = Transaction(
            ids.next(),
            account.account_id,
            receiver,
            round(rng.uniform(9000, 26000), 2),
            "INR",
            account.home_device_id,
            account.home_ip_address,
            "UPI",
            base + timedelta(seconds=index * step),
            location_city=account.home_city,
            location_state=account.home_state,
            context={
                "ipType": "RESIDENTIAL",
                "deviceTrust": "TRUSTED",
                "locationSource": "DEVICE",
            },
        )
        events.append(
            GeneratedEvent(
                transaction,
                GroundTruth(
                    transaction.transaction_id,
                    True,
                    "mule_fan_in",
                    "HIGH",
                    "Multiple unrelated senders converge on a single synthetic mule beneficiary.",
                    ring_id,
                    [account.account_id, receiver],
                ),
            )
        )
    return events


def account_takeover(
    count: int,
    *,
    rng: random.Random,
    accounts: list[Account],
    merchants: list[Merchant],
    start: datetime,
    duration_seconds: int,
    ids: IdFactory,
    batch_index: int,
) -> list[GeneratedEvent]:
    account = rng.choice(accounts)
    device = f"DEV-NOVEL-{ids.seed}-{batch_index:04d}"
    ip_address = private_ip(batch_index, subnet=40 + ids.seed % 200)
    base, step = burst_timeline(
        rng=rng,
        start=start,
        duration_seconds=duration_seconds,
        count=count,
        minimum_step=30,
        maximum_step=60,
    )
    events = []
    for index in range(count):
        merchant = rng.choice(merchants)
        transaction = Transaction(
            ids.next(),
            account.account_id,
            merchant.merchant_id,
            round(max(45000, account.typical_amount * rng.uniform(8, 15)), 2),
            "INR",
            device,
            ip_address,
            "CARD",
            base + timedelta(seconds=index * step),
            location_city="Singapore",
            location_state="Singapore",
            location_country="SG",
            merchant_category=merchant.category,
            context={
                "ipType": "DATACENTER",
                "deviceTrust": "NEW",
                "locationSource": "IP",
                "impossibleTravel": True,
            },
        )
        events.append(
            GeneratedEvent(
                transaction,
                GroundTruth(
                    transaction.transaction_id,
                    True,
                    "account_takeover",
                    "CRITICAL",
                    (
                        "Established account suddenly uses a novel device and IP for "
                        "high-value payments."
                    ),
                    f"ATO-{ids.seed}-{batch_index:04d}",
                    [account.account_id, device, ip_address],
                ),
            )
        )
    return events


Scenario = Callable[..., list[GeneratedEvent]]
ABUSE_SCENARIOS: dict[str, tuple[Scenario, tuple[int, int]]] = {
    "shared_device_ring": (shared_device_ring, (5, 9)),
    "velocity_burst": (velocity_burst, (4, 8)),
    "mule_fan_in": (mule_fan_in, (5, 10)),
    "account_takeover": (account_takeover, (2, 4)),
}
