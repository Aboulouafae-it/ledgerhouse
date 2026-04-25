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

## Coding Rules

- Keep business logic in services.
- Keep database access in repositories.
- Keep UI files focused on presentation.
- Never store plaintext passwords.
- Never use float for money.
- Do not hard delete financial records.
- Use fake or anonymized data in tests, screenshots, logs, and issue examples.
- Add focused tests for money calculations, debt payments, shared splits, settlement suggestions, migrations, and backup/restore behavior.
