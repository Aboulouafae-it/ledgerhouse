# Claude Development Guide

This guide explains how Claude can safely help develop Personal Ledger Pro.

## Project Overview

Personal Ledger Pro is a local-first Debian/Linux desktop finance manager built with Python, PySide6, SQLite, and SQLAlchemy. It manages personal transactions, debts, partial debt payments, shared living expenses, settlement suggestions, people, PDF reports, settings, backups, restore workflows, login protection, and database integrity checks.

## Architecture Rules

- Keep UI code focused on presentation and user interaction.
- Keep business logic in services.
- Keep database access in repositories.
- Keep SQLAlchemy models focused on schema and relationships.
- Keep reports isolated in the reporting layer.
- Keep owner/person synchronization in settings and people services, not UI code.
- Avoid broad cross-layer refactors without maintainer review.

## Database Rules

- Do not hard delete financial records without review.
- Do not drop tables or columns without review.
- Prefer additive, idempotent migrations.
- Preserve user data during schema changes.
- Test database changes with fake or anonymized data.
- Never ask users to upload real financial databases.
- Store the current app owner through `owner_person_id` and a normal `Person` record.

## Money Handling Rules

- Never use float for money.
- Use `Decimal` or integer minor units.
- Make rounding rules explicit.
- Add tests for debt payments, shared splits, settlement suggestions, refunds, and edge cases.
- Watch for accidental string, float, and decimal conversions.

## UI Rules

- Keep calculations out of UI files.
- Route user actions through services.
- Keep UI text clear and practical.
- Use fake or anonymized data in screenshots.
- Do not expose private database paths, passwords, or personal finance details.

## Reporting Rules

- Reports must not mutate financial data.
- Report identity settings should come from persisted settings.
- Generated reports may contain private data and should be treated as sensitive.
- Use fake or anonymized data when testing or documenting reports.

## Testing Rules

- Add tests for service-level business rules.
- Add tests for database migrations and integrity behavior when changing schema.
- Add edge cases for rounding, partial payments, settlement optimization, and shared living splits.
- Keep fixtures fake and minimal.

## Safe Tasks Claude Can Do

- Review service logic for money calculation bugs.
- Add focused tests for financial rules.
- Improve README, docs, issue templates, and contribution guidance.
- Audit database migrations for destructive operations.
- Add tests around owner/person synchronization and shared living balances.
- Suggest refactors with clear risk notes.
- Improve report documentation and fake-data examples.

## Dangerous Tasks Claude Must Not Do Without Review

- Change authentication or password storage behavior.
- Rewrite debt, settlement, or shared living calculations.
- Delete or rewrite database migration history.
- Add destructive schema migrations.
- Change backup or restore behavior.
- Modify generated reports in ways that could hide or misstate financial data.
- Move responsibilities across UI, services, repositories, and models without review.

## Example Prompts

```text
Review DebtService for money calculation bugs. Do not change UI files.
```

```text
Add tests for shared living equal split and settlement optimization.
```

```text
Improve README installation instructions for Debian.
```

```text
Audit database migrations for destructive operations.
```
