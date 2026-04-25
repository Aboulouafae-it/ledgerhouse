# Architecture

Personal Ledger Pro is organized as a local-first desktop application with clear boundaries between presentation, business rules, persistence, database schema, and reporting.

## UI Layer

The UI layer contains PySide6 windows, pages, widgets, and themes. UI files should focus on presentation, input handling, validation messages, and calling services. Financial calculations and database queries should not live in UI code.

## Services Layer

Services contain business logic for transactions, debts, partial payments, shared living expenses, settlements, reports, settings, authentication, backups, and dashboard summaries. Services coordinate repositories and enforce application rules.

## Repositories Layer

Repositories own database access. They should contain SQLAlchemy queries, persistence operations, and data retrieval methods. UI code should not query the database directly.

## Models Layer

Models define SQLAlchemy ORM entities, fields, relationships, and schema-level constraints. Models should stay focused on data shape rather than user workflows.

## Database Layer

The database layer initializes SQLite, manages sessions, and applies safe startup migrations or schema checks. Database operations should preserve user data and avoid destructive changes without review.

## Reports Layer

The reports layer generates PDF output from application data. Report generation should not mutate financial records. Reports may contain private data and should be treated as sensitive files.

## Local-first Design

Personal Ledger Pro stores data locally by default. The app should work without a remote service. Optional future sync features must preserve user control, privacy, backup safety, and clear conflict behavior.
