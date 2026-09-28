"""Text reporting for validation runs."""

from __future__ import annotations

from collections.abc import Sequence

from ..models import ObjectValidationReport, ValidationSummary


def summarize_reports(reports: Sequence[ObjectValidationReport]) -> ValidationSummary:
    """Combine all check results in multiple object reports."""
    return ValidationSummary.from_results(
        result for report in reports for result in report.results
    )


def format_reports(reports: Sequence[ObjectValidationReport]) -> str:
    """Format reports as a detailed, console-friendly text document."""
    summary = summarize_reports(reports)
    validated = sum(report.was_validated for report in reports)
    skipped = len(reports) - validated
    lines = [
        "=" * 72,
        "BLENDER ASSET PIPELINE - VALIDATION REPORT",
        "=" * 72,
        f"Objects: {len(reports)} total, {validated} validated, {skipped} skipped",
        "",
    ]
    for report in reports:
        state = "VALIDATED" if report.was_validated else "SKIPPED"
        lines.append(f"{report.object_name} [{report.object_type}] - {state}")
        lines.append("-" * 72)
        for result in report.results:
            lines.append(
                f"[{result.severity.name:<7}] {result.check_name}: {result.message}"
            )
        lines.append("")

    lines.extend(
        [
            "SUMMARY",
            "-" * 72,
            (
                f"PASS: {summary.passed} | WARNING: {summary.warnings} | "
                f"ERROR: {summary.errors}"
            ),
            f"RESULT: {summary.highest_severity.name}",
            "=" * 72,
        ]
    )
    return "\n".join(lines)
