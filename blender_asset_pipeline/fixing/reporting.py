"""Console formatting for structured fix execution results."""

from __future__ import annotations

from .models import FixExecutionReport


def format_fix_report(report: FixExecutionReport) -> str:
    """Format a detailed execution report grouped by object."""
    lines = ["=" * 72, "FIX REPORT", "=" * 72]
    current_object = None
    for result in report.results:
        if result.object_name != current_object:
            if current_object is not None:
                lines.append("")
            current_object = result.object_name
            lines.append(result.object_name)
            lines.append("-" * 72)
        lines.append(
            f"[{result.status.value:<7}] {result.title}: {result.message}"
        )

    if not report.results:
        lines.append("No fixes were selected.")
    if report.context_warnings:
        lines.extend(("", "CONTEXT RESTORATION WARNINGS", "-" * 72))
        lines.extend(f"- {warning}" for warning in report.context_warnings)
    lines.append("=" * 72)
    return "\n".join(lines)
