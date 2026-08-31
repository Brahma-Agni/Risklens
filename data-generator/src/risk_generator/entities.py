import random

from risk_generator.models import Account, Merchant

PAYMENT_METHODS = ("UPI", "CARD", "WALLET", "NETBANKING")
MERCHANT_CATEGORIES = (
    ("GROCERY", 1800.0),
    ("TRAVEL", 28000.0),
    ("ELECTRONICS", 22000.0),
    ("FOOD", 900.0),
    ("DIGITAL_GOODS", 3500.0),
    ("UTILITIES", 2400.0),
)


def private_ip(index: int, subnet: int = 20) -> str:
    third = (index // 250) % 250
    fourth = index % 250 + 1
    return f"10.{subnet}.{third}.{fourth}"


def create_accounts(count: int, rng: random.Random) -> list[Account]:
    accounts = []
    for index in range(count):
        method = rng.choice(PAYMENT_METHODS)
        typical = round(rng.lognormvariate(7.6, 0.75), 2)
        accounts.append(
            Account(
                account_id=f"USER-SYN-{index + 1:05d}",
                home_device_id=f"DEV-SYN-{index + 1:05d}",
                home_ip_address=private_ip(index),
                payment_method=method,
                typical_amount=min(typical, 75000.0),
            )
        )
    return accounts


def create_merchants(count: int, rng: random.Random) -> list[Merchant]:
    merchants = []
    for index in range(count):
        category, typical = rng.choice(MERCHANT_CATEGORIES)
        merchants.append(
            Merchant(
                merchant_id=f"MERCHANT-SYN-{index + 1:04d}",
                category=category,
                typical_amount=typical,
            )
        )
    return merchants
