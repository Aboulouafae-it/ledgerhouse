# Contributing

Thank you for helping improve Personal Ledger Pro. This project handles sensitive financial workflows, so contributions should be careful, reviewable, and conservative with user data.

## Local Setup

Install Debian dependencies:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libxcb-cursor0
```

Create a virtual environment and install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the app:

```bash
python -m app.main
```

Run tests:

```bash
pytest
```

## Branch Workflow

- Create feature branches from the main development branch.
- Keep branches focused on one fix, feature, or documentation change.
- Rebase or merge the latest main branch before opening a pull request.
- Avoid mixing UI, database, and business logic changes in one pull request unless the feature requires it.

## Commit Message Examples

```text
docs: improve Debian setup instructions
fix: prevent negative debt payment totals
test: add shared living settlement coverage
chore: update issue templates
```

## Pull Request Workflow

- Describe the user-facing change and why it is needed.
- Link related issues.
- Include screenshots when UI changes are made.
- Include tests for financial calculations, database behavior, and service rules when relevant.
- Explain migration behavior for database changes.
- Confirm that fake or anonymized data was used in screenshots, logs, and test fixtures.

## Code Style Rules

- Keep business logic in services.
- Keep database access in repositories.
- Keep UI files focused on presentation.
- Prefer small, testable functions for financial rules.
- Use clear names for money, date, person, creditor, debtor, and settlement fields.
- Avoid broad refactors in feature or bug-fix pull requests.

## Database Safety Rules

- Do not hard delete financial records.
- Do not drop tables or columns without a reviewed migration and recovery plan.
- Make migrations idempotent where possible.
- Preserve user data during schema upgrades.
- Test migrations against copied, fake, or anonymized databases.
- Never upload real finance databases to issues, pull requests, or discussions.

## Money Calculation Rules

- Never use float for money.
- Use `Decimal` or integer minor units for money calculations.
- Define rounding behavior explicitly.
- Add tests for partial payments, equal splits, settlements, refunds, and edge cases.
- Avoid hidden conversions between strings, floats, and decimals.

## UI Rules

- Keep UI files focused on presentation and user interaction.
- Do not place money calculations or persistence rules in UI code.
- Route business operations through services.
- Show clear confirmation for destructive or irreversible actions.
- Use fake or anonymized data in screenshots.

## Security Rules

- Never store plaintext passwords.
- Do not log passwords, backup paths containing secrets, or private financial data.
- Use established password hashing helpers.
- Treat local database and backup files as sensitive.
