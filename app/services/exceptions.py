from __future__ import annotations


class LedgerError(Exception):
    """Base exception for recoverable application errors."""


class ValidationError(LedgerError):
    """Raised when user-provided data is invalid."""


class NotFoundError(LedgerError):
    """Raised when a requested record cannot be found."""

