# Database

Personal Ledger Pro uses a local SQLite database accessed through SQLAlchemy models and repository classes. The database is intended to remain on the user's machine unless the user explicitly backs it up or moves it.

## SQLite Local Database

The default database file is stored under the local project data directory during development. Database files, write-ahead logs, and shared-memory files are ignored by Git because they can contain private financial information.

## Main Tables

Primary data areas include:

- Users and login credentials.
- People.
- Accounts.
- Categories.
- Payment methods.
- Personal transactions.
- Debts.
- Debt payments.
- Shared expenses.
- Shared expense participants.
- Settlements.
- App settings.
- Report exports.
- Audit logs.

## Owner Person

The current app owner is represented as a normal `Person` row, not as a text-only setting.

When `owner_name` is saved in General Settings or report identity settings, the settings service creates or updates a matching person using `normalized_name`. The owner person is always marked as active and as a shared living member:

- `is_active = true`
- `is_house_member = true`

The corresponding `people.id` is stored in `AppSetting` as `owner_person_id`. This lets the app identify the owner for dashboard summaries and reports while keeping shared living calculations generic.

The owner is not hardcoded in split logic. Shared expenses treat the owner like any other participant; the owner role only tells the app which person's balance belongs to the current user.

## People Roles

People can represent multiple finance roles at the same time:

- creditor
- debtor
- shared living member

A person may appear in debt workflows, shared living workflows, and reporting without being duplicated across separate tables.

## Money Handling Rule

Never use float for money. Use `Decimal` or integer minor units and make rounding behavior explicit. Tests should cover partial payments, shared expense splits, settlements, and boundary conditions.

## Migration Safety

Migrations must preserve user data.

- Prefer additive schema changes.
- Make migrations idempotent where possible.
- Do not drop tables or columns without review.
- Do not hard delete financial records.
- Test migrations with copied, fake, or anonymized databases.

## Backup Safety

Backups contain private financial data. Store them securely, do not upload them to public issues, and verify restore behavior with fake or anonymized databases.
