"""Structured validation result types."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    """Severity of a validation result, ordered from least to most severe."""

    PASS = 0
    WARNING = 1
    ERROR = 2


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one named validation check."""

    check_id: str
    check_name: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class ValidationSummary:
    """Aggregate counts for a set of check results."""

    passed: int = 0
    warnings: int = 0
    errors: int = 0

    @property
    def total(self) -> int:
        """Return the total number of checks."""
        return self.passed + self.warnings + self.errors

    @property
    def highest_severity(self) -> Severity:
        """Return the highest severity represented by this summary."""
        if self.errors:
            return Severity.ERROR
        if self.warnings:
            return Severity.WARNING
        return Severity.PASS

    @classmethod
    def from_results(cls, results: Iterable[CheckResult]) -> ValidationSummary:
        """Build aggregate counts from an iterable of results."""
        counts = {severity: 0 for severity in Severity}
        for result in results:
            counts[result.severity] += 1
        return cls(
            passed=counts[Severity.PASS],
            warnings=counts[Severity.WARNING],
            errors=counts[Severity.ERROR],
        )


@dataclass(frozen=True)
class ObjectValidationReport:
    """All check results for one object snapshot."""

    object_name: str
    object_type: str
    results: tuple[CheckResult, ...]
    was_validated: bool = True

    @property
    def summary(self) -> ValidationSummary:
        """Summarize the report's check severities."""
        return ValidationSummary.from_results(self.results)
