# Security Policy

## Reporting Vulnerabilities

Please report security vulnerabilities privately to the maintainers instead of opening a public issue. Include a clear description, affected version or commit, reproduction steps, and expected impact.

Do not include real financial databases, real backups, real credentials, or screenshots containing private data.

## Sensitive Data in Issues

- Do not upload real finance databases.
- Do not share screenshots with private data.
- Use fake or anonymized data in issues, discussions, pull requests, and logs.
- Redact names, account labels, transaction descriptions, report identities, and file paths that reveal private information.

## Local SQLite Database Security

Personal Ledger Pro stores data locally in SQLite. Anyone with access to the database file may be able to inspect financial records depending on local filesystem permissions and database encryption status.

Recommended practices:

- Keep the database in a user-owned directory.
- Restrict filesystem permissions on shared machines.
- Do not sync the database through untrusted services.
- Test database issues with fake or anonymized copies only.

## Backup Security

Backups can contain the same private financial data as the main database.

- Store backups securely.
- Do not attach backups to public issues.
- Remove old backups when they are no longer needed.
- Prefer encrypted storage for external drives or cloud backup locations.

## Password Hashing

Passwords must never be stored in plaintext. Authentication changes should use established password hashing helpers and should include tests or review notes explaining how credentials are stored and verified.
