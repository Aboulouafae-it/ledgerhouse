from decimal import Decimal

from app.services.settlement_service import SettlementService


def test_settlement_optimization():
    rows = SettlementService().optimize({"A": Decimal("-10.00"), "B": Decimal("6.00"), "C": Decimal("4.00")})
    assert [(row.from_person, row.to_person, row.amount) for row in rows] == [
        ("A", "B", Decimal("6.00")),
        ("A", "C", Decimal("4.00")),
    ]

