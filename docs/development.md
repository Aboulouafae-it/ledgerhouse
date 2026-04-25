# Development

## Debian Setup

Install Python and common Qt runtime dependencies:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libxcb-cursor0
```

## Create Virtual Environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## Install Requirements

```bash
python -m pip install -r requirements.txt
```

## Run the App

```bash
python -m app.main
```

## Run Tests

```bash
pytest
```

## Local Desktop Install

Install the launcher for the current Linux user:

```bash
install -D -m 755 packaging/linux/personal-ledger-pro ~/.local/bin/personal-ledger-pro
install -D -m 644 packaging/linux/personal-ledger-pro.desktop ~/.local/share/applications/personal-ledger-pro.desktop
update-desktop-database ~/.local/share/applications || true
```

Run the installed launcher:

```bash
personal-ledger-pro
```

## Coding Rules

- Keep business logic in services.
- Keep database access in repositories.
- Keep UI files focused on presentation.
- Keep owner/person synchronization in services.
- Treat the owner as a normal `Person` in shared living calculations.
- Keep shared expense edit, delete, and detail workflows routed through services.
- Keep PDF fixed-position page elements in report generation helpers, not in UI code.
- Never store plaintext passwords.
- Never use float for money.
- Do not hard delete financial records.
- Use fake or anonymized data in tests, screenshots, logs, and issue examples.
- Add focused tests for money calculations, debt payments, shared splits, settlement suggestions, migrations, and backup/restore behavior.
