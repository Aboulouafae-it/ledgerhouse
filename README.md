# Personal Ledger Pro

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B3776AB.svg)
![Platform: Linux](https://img.shields.io/badge/Platform-Linux-black.svg)
![Status: Active Development](https://img.shields.io/badge/Status-Active%20Development-brightgreen.svg)

A local-first personal finance, debt, and shared living expense manager for Debian/Linux.

## Overview

Personal Ledger Pro is a Debian/Linux desktop finance manager built with Python, PySide6, SQLite, and SQLAlchemy. It helps manage personal income and expenses, debts, partial debt payments, shared living expenses, settlement suggestions, people, reports, settings, backups, and local login protection.

The application is local-first: financial data is stored in a local SQLite database and is not uploaded to a cloud service by default.

## Features

- Personal income and expense tracking.
- Debt tracking with creditors, debtors, and partial payments.
- Shared living expense splits and settlement suggestions.
- People management for creditors, debtors, and shared living members.
- PDF financial reports.
- Login protection with local credentials.
- Settings center for app, report, people, category, payment, backup, and appearance options.
- Backup and restore workflows.
- Database integrity checks.

## Screenshots

Screenshots are placeholders until real, privacy-safe images are added.

- `docs/assets/screenshots/dashboard.png`
- `docs/assets/screenshots/debts.png`
- `docs/assets/screenshots/shared-living.png`
- `docs/assets/screenshots/pdf-report.png`

## Demo

Demo placeholder:

- `docs/assets/demo/personal-ledger-pro-demo.gif`

## Installation on Debian

Install Python and common Qt runtime prerequisites:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libxcb-cursor0
```

Clone the repository and enter the project directory:

```bash
git clone https://github.com/your-org/personal-ledger-pro.git
cd personal-ledger-pro
```

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running from Source

Run the desktop app from the project root:

```bash
python -m app.main
```

Run tests:

```bash
pytest
```

## Default Login Credentials

The default first-run credentials are:

```text
Username: admin
Password: admin123
```

Change the password after first login.

## Project Structure

```text
app/
  core/            Configuration, database setup, backup, security, and session helpers
  models/          SQLAlchemy ORM models
  repositories/    Database access layer
  services/        Business rules and money calculations
  ui/              PySide6 windows, pages, widgets, and themes
  reports/         PDF report generation
  utils/           Money, date, and text helpers
tests/             Service and utility tests
docs/              Project documentation and media placeholders
data/              Local SQLite database files, ignored by Git
backups/           Local backup files, ignored by Git
```

## Database

Personal Ledger Pro uses a local SQLite database managed through SQLAlchemy models and repositories. The database stores users, people, transactions, debts, debt payments, shared expenses, settlements, settings, report exports, categories, payment methods, accounts, and audit logs.

Financial records should be treated as durable user data. Do not hard delete records without a reviewed retention strategy, and keep migration operations non-destructive.

See [docs/database.md](docs/database.md).

## Reports

PDF reports cover income, expenses, debts, shared living expenses, and full financial summaries. Report identity settings such as owner name and footer text are managed through app settings.

See [docs/reports.md](docs/reports.md).

## Backup

Backups are local files and may contain private financial information. Store backups securely, do not attach real backups to public issues, and test restore behavior with fake or anonymized data.

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## How Claude Can Help

Claude can help review services, write tests, improve documentation, audit migration safety, and reason about money calculations. Claude should not make destructive database changes, weaken authentication, or change financial logic without review.

See [CLAUDE.md](CLAUDE.md).

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue or pull request.

## Security

Please report vulnerabilities privately and do not upload real financial databases, logs, backups, or screenshots with private data.

See [SECURITY.md](SECURITY.md).

## License

Personal Ledger Pro is licensed under the MIT License. See [LICENSE](LICENSE).

## Disclaimer

Personal Ledger Pro is personal finance software, not professional financial, tax, legal, or accounting advice. Verify reports, balances, and settlement suggestions before relying on them.
