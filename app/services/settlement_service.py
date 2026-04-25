from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.utils.money import CENT, to_decimal


@dataclass(frozen=True)
class Settlement:
    from_person: str
    to_person: str
    amount: Decimal


class SettlementService:
    def optimize(self, balances: dict[str, Decimal]) -> list[Settlement]:
        normalized = {name: to_decimal(amount) for name, amount in balances.items() if to_decimal(amount) != Decimal("0.00")}
        drift = sum(normalized.values(), Decimal("0.00"))
        if abs(drift) >= CENT and normalized:
            largest = max(normalized, key=lambda name: abs(normalized[name]))
            normalized[largest] = to_decimal(normalized[largest] - drift)

        creditors = [[name, amount] for name, amount in normalized.items() if amount > Decimal("0.00")]
        debtors = [[name, -amount] for name, amount in normalized.items() if amount < Decimal("0.00")]
        creditors.sort(key=lambda row: row[1], reverse=True)
        debtors.sort(key=lambda row: row[1], reverse=True)

        settlements: list[Settlement] = []
        i = j = 0
        while i < len(debtors) and j < len(creditors):
            debtor_name, debtor_amount = debtors[i]
            creditor_name, creditor_amount = creditors[j]
            amount = to_decimal(min(debtor_amount, creditor_amount))
            if amount > Decimal("0.00"):
                settlements.append(Settlement(debtor_name, creditor_name, amount))
            debtors[i][1] -= amount
            creditors[j][1] -= amount
            if debtors[i][1] <= Decimal("0.00"):
                i += 1
            if creditors[j][1] <= Decimal("0.00"):
                j += 1
        return settlements
