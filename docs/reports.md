# Reports

Personal Ledger Pro generates PDF reports from local financial data. Reports may contain private information and should be handled with the same care as the SQLite database and backups.

## PDF Report Types

The reporting layer supports focused reports and full summaries.

## Income Report

Income reports summarize incoming transactions over a selected period. They may include categories, dates, payment methods, totals, and report identity settings.

## Expense Report

Expense reports summarize outgoing transactions over a selected period. They can help review category-level spending, payment methods, and total expenses.

## Debt Report

Debt reports summarize creditors, debtors, outstanding balances, partial payments, and debt status. They should make paid, unpaid, and partially paid debts easy to distinguish.

## Shared Living Report

Shared living reports summarize shared expenses, participants, splits, owed amounts, and settlement suggestions.

## Full Report

Full reports combine personal transactions, debts, shared living activity, and summary totals into one PDF.

## Report Identity Settings

Report identity settings can include owner name, title text, footer text, and other persisted settings. These values may reveal private information and should be anonymized in public examples.

## Screenshot and Report Export Location Placeholders

Screenshots should be placed in:

```text
docs/assets/screenshots/
```

The demo GIF should be placed in:

```text
docs/assets/demo/personal-ledger-pro-demo.gif
```

Generated report examples should use fake data and can be documented with placeholder paths until a safe sample export policy is defined.
