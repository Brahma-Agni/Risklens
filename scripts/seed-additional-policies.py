#!/usr/bin/env python3
"""Seed the Qdrant policy collection through the validated verifier API."""

import json
import os
import urllib.request


BASE_URL = os.getenv("VERIFIER_PUBLIC_URL", "http://localhost:28090")

POLICIES = [
    ("NEW-ACCOUNT-RISK", "New-account activity", "Review high-value activity from a newly created account when another risk signal is present.", "REVIEW", .60, 700, ["new_account", "amount", "account"]),
    ("ACCOUNT-TAKEOVER", "Account takeover indicators", "Hold when a new device, unusual location, authentication failures, and changed payment behaviour occur together.", "HOLD", .80, 940, ["account_takeover", "device", "location", "authentication"]),
    ("AUTH-FAILURE-BURST", "Authentication failure burst", "Review repeated authentication failures followed by a payment from the same account or device.", "REVIEW", .60, 760, ["authentication", "velocity"]),
    ("PASSWORD-RESET-PAYMENT", "Post-reset payment review", "Review payments made shortly after a password, phone-number, or identity reset.", "REVIEW", .65, 780, ["account_takeover", "authentication"]),
    ("MULTI-ACCOUNT-DEVICE", "Multi-account device", "Hold when many sender accounts transact from one device within a short period.", "HOLD", .75, 920, ["shared_device", "ring", "graph"]),
    ("SHARED-IDENTITY", "Shared identity attributes", "Review or hold unrelated accounts that share identity, contact, or payment-instrument attributes.", "HOLD", .78, 900, ["shared_identity", "shared_instrument", "graph"]),
    ("VELOCITY-5MIN", "Five-minute velocity", "Review more than four payments from one account within five minutes, especially with a new beneficiary or device.", "REVIEW", .60, 800, ["velocity", "temporal"]),
    ("VELOCITY-1HOUR", "Hourly velocity", "Hold unusually high hourly transaction velocity when it materially exceeds the account's established behaviour.", "HOLD", .82, 850, ["velocity", "temporal", "behaviour"]),
    ("DECLINE-BURST", "Decline burst", "Review repeated declined payments followed by a successful payment from the same account or device.", "REVIEW", .60, 740, ["decline", "velocity"]),
    ("ROUND-AMOUNT", "Repeated round amounts", "Review repeated round-value payments only when combined with another independent risk signal.", "REVIEW", .65, 620, ["amount", "behaviour"]),
    ("AMOUNT-DEVIATION", "Amount deviation", "Review a payment substantially larger than the customer's normal transaction amount.", "REVIEW", .60, 720, ["amount", "behaviour"]),
    ("MICRO-PAYMENT-BURST", "Micro-payment burst", "Review many small payments made by one account or device in a short period.", "REVIEW", .60, 730, ["fragmentation", "velocity", "amount"]),
    ("REPEATED-PAYEE", "Repeated new payee", "Review repeated payments to the same newly observed beneficiary within a short window.", "REVIEW", .60, 700, ["beneficiary", "velocity"]),
    ("FRAGMENTED-FUNDING", "Fragmented funding", "Hold multiple small payments whose aggregate value is material and whose senders are coordinated.", "HOLD", .78, 925, ["amount_splitting", "fragmentation", "multi_source"]),
    ("MULE-FAN-IN", "Mule fan-in", "Hold when many senders transfer funds to one receiver quickly and the receiver is linked to other risk signals.", "HOLD", .75, 930, ["mule_fan_in", "beneficiary", "graph"]),
    ("MULE-FAN-OUT", "Mule fan-out", "Review one account distributing funds to many new receivers within a short period.", "REVIEW", .65, 820, ["mule_fan_out", "beneficiary", "graph"]),
    ("BENEFICIARY-ROTATION", "Beneficiary rotation", "Review rapid rotation across several beneficiaries when paired with velocity or unusual account behaviour.", "REVIEW", .60, 810, ["beneficiary_rotation", "velocity"]),
    ("RAPID-COLLECTION", "Rapid collection", "Hold coordinated inbound payments from unrelated accounts when aggregate value and timing are suspicious.", "HOLD", .78, 900, ["multi_source", "mule_fan_in", "temporal"]),
    ("FUND-LOOP", "Circular fund movement", "Hold when funds circulate between accounts connected in the relationship graph.", "HOLD", .80, 940, ["fund_loop", "graph", "ring"]),
    ("RING-CORROBORATION-002", "Two-signal ring corroboration", "A payment-ring decision requires at least two independent signals; a shared IP address alone is insufficient.", "HOLD", .75, 955, ["ring", "corroboration", "graph"]),
    ("SHARED-INSTRUMENT", "Shared payment instrument", "Hold when unrelated accounts use the same payment instrument and transact within a coordinated window.", "HOLD", .78, 915, ["shared_instrument", "graph"]),
    ("SHARED-IP-CONTEXT", "Shared IP context", "Never hold on a shared IP alone; require a second independent signal before escalation.", "REVIEW", .60, 650, ["shared_ip", "corroboration"]),
    ("NOVEL-DEVICE", "Novel device", "Review a payment from a new device when the amount, velocity, or beneficiary is unusual.", "REVIEW", .60, 760, ["novel_device", "device", "behaviour"]),
    ("NOVEL-LOCATION", "Novel location", "Review a payment from an unusual location or network origin when another risk signal is present.", "REVIEW", .60, 700, ["novel_location", "location", "network"]),
    ("GRAPH-COMPONENT", "Suspicious graph component", "Escalate dense clusters of accounts, devices, instruments, and beneficiaries with coordinated activity.", "HOLD", .80, 950, ["graph", "ring", "shared_device"]),
]


def main() -> None:
    stored = 0
    for suffix, title, text, action, threshold, priority, tags in POLICIES:
        policy_id = f"POLICY-{suffix}-001"
        payload = {
            "policy_id": policy_id,
            "title": title,
            "text": text,
            "minimum_action": action,
            "threshold": threshold,
            "priority": priority,
            "tags": tags,
            "source_name": "RiskLens internal fraud control catalog",
            "source_date": "2026-09-16",
            "source_section": "Additional behavioural and relationship controls",
        }
        request = urllib.request.Request(
            f"{BASE_URL}/api/v1/policies/{policy_id}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status not in (200, 201):
                raise RuntimeError(f"{policy_id}: HTTP {response.status}")
        stored += 1
    print(f"Stored {stored} additional policies in risk_policies at {BASE_URL}")


if __name__ == "__main__":
    main()
