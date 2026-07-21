from __future__ import annotations


class RavenError(Exception):
    """Base exception for all RAVEN errors."""


class RepositoryValidationError(RavenError):
    """Raised when a repository does not satisfy the RAVEN Repository Specification."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("repository does not satisfy the RAVEN specification: " + ", ".join(missing))
