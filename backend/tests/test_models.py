from decimal import Decimal

import pytest
from pydantic import ValidationError

from risklens_backend.models import TransactionRequest


def valid_payment() -> dict:
    return {
        "transactionId": "TX-1",
        "senderId": "USER-1",
        "receiverId": "MERCHANT-1",
        "amount": "125.50",
        "currency": "INR",
        "deviceId": "DEVICE-1",
        "ipAddress": "10.0.0.1",
        "paymentMethod": "upi",
        "timestamp": "2026-09-16T10:00:00Z",
    }


def test_transaction_request_validates_and_normalizes() -> None:
    payment = TransactionRequest.model_validate(valid_payment())

    assert payment.amount == Decimal("125.50")
    assert payment.payment_method == "UPI"


@pytest.mark.parametrize(
    ("field", "value"),
    [("amount", 0), ("currency", "RUPEES"), ("ipAddress", "not-an-ip")],
)
def test_transaction_request_rejects_invalid_boundary_data(field: str, value: object) -> None:
    payload = valid_payment()
    payload[field] = value

    with pytest.raises(ValidationError):
        TransactionRequest.model_validate(payload)
