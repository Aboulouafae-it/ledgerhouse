from __future__ import annotations

from decimal import Decimal

from app.services.exceptions import ValidationError
from app.utils.money import split_money_evenly, to_decimal


def equal_split(total: Decimal, participant_count: int) -> list[Decimal]:
    return split_money_evenly(total, participant_count)


def validate_custom_split(total: Decimal, shares: list[Decimal]) -> list[Decimal]:
    normalized = [to_decimal(share) for share in shares]
    if sum(normalized, Decimal("0.00")) != to_decimal(total):
        raise ValidationError("Custom split amounts must equal the expense total.")
    return normalized


def validate_percentage_split(percentages: list[Decimal]) -> list[Decimal]:
    normalized = [to_decimal(percent) for percent in percentages]
    if sum(normalized, Decimal("0.00")) != Decimal("100.00"):
        raise ValidationError("Percentage split must total 100%.")
    return normalized

