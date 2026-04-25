from decimal import Decimal

from app.utils.money import split_money_evenly
from app.services.exceptions import ValidationError
from app.services.shared_split_rules import validate_custom_split, validate_percentage_split


def test_equal_split_preserves_cents():
    shares = split_money_evenly(Decimal("10.00"), 3)
    assert sum(shares, Decimal("0.00")) == Decimal("10.00")
    assert shares == [Decimal("3.34"), Decimal("3.33"), Decimal("3.33")]


def test_custom_split_validation():
    assert validate_custom_split(Decimal("10.00"), [Decimal("4"), Decimal("6")]) == [Decimal("4.00"), Decimal("6.00")]


def test_percentage_split_validation():
    assert validate_percentage_split([Decimal("40"), Decimal("60")]) == [Decimal("40.00"), Decimal("60.00")]
