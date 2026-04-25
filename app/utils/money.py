from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CENT = Decimal("0.01")


def to_decimal(value: str | int | Decimal) -> Decimal:
    try:
        if isinstance(value, Decimal):
            amount = value
        else:
            amount = Decimal(str(value).strip().replace(",", "") or "0")
        return amount.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Enter a valid money amount.") from exc


def validate_positive_money(value: str | int | Decimal) -> Decimal:
    amount = to_decimal(value)
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    return amount


def round_money(value: Decimal) -> Decimal:
    return to_decimal(value)


def decimal_to_cents(value: Decimal | str | int) -> int:
    amount = to_decimal(value)
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def cents_to_decimal(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)


def format_money(cents: int, currency: str = "EUR") -> str:
    return money(cents_to_decimal(cents), currency)


def validate_money_input(value: str) -> Decimal:
    return validate_positive_money(value)


def split_money_evenly(total: Decimal, count: int) -> list[Decimal]:
    if count <= 0:
        raise ValueError("At least one participant is required.")
    cents = int((to_decimal(total) * 100).to_integral_value())
    base, remainder = divmod(cents, count)
    return [Decimal(base + (1 if index < remainder else 0)) / 100 for index in range(count)]


def money(value: Decimal | int | str, currency: str = "EUR") -> str:
    amount = to_decimal(value)
    return f"{amount:,.2f} {currency}"
