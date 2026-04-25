from decimal import Decimal

from app.utils.money import cents_to_decimal, decimal_to_cents, format_money, round_money, validate_money_input


def test_money_conversion_round_trip():
    assert decimal_to_cents(Decimal("12.50")) == 1250
    assert cents_to_decimal(1250) == Decimal("12.50")
    assert format_money(1250) == "12.50 EUR"


def test_money_input_rounding():
    assert validate_money_input("12.5") == Decimal("12.50")
    assert round_money(Decimal("12.345")) == Decimal("12.35")

