"""Concise console formatting for batch validation runs."""

from __future__ import annotations

from .models import BatchObjectStatus, BatchValidationReport


def format_batch_report(
    report: BatchValidationReport,
    max_attention_objects: int = 20,
) -> str:
    """Format a bounded, console-friendly batch summary."""
    summary = report.summary
    geometry = summary.geometry
    attention = tuple(
        result
        for result in report.objects
        if result.status in {BatchObjectStatus.WARNING, BatchObjectStatus.ERROR}
    )
    largest = (
        f"{geometry.largest_object_name} "
        f"({geometry.largest_triangle_count:,} triangles)"
        if geometry.largest_object_name is not None
        else "None"
    )
    lines = [
        "=" * 72,
        "BATCH VALIDATION REPORT",
        "=" * 72,
        f"Scope: {report.scope.value}",
        f"Scenes: {', '.join(report.scene_names) or 'None'}",
        f"Objects discovered: {summary.objects_discovered}",
        f"Validated: {summary.objects_validated}",
        f"Skipped: {summary.objects_skipped}",
        "",
        f"Clean: {summary.clean_objects}",
        f"Warnings: {summary.warning_objects}",
        f"Errors: {summary.error_objects}",
        "",
        "Checks:",
        f"Pass: {summary.checks_passed}",
        f"Warning: {summary.checks_warning}",
        f"Error: {summary.checks_error}",
        "",
        "Geometry:",
        f"Vertices: {geometry.total_vertices:,}",
        f"Polygons: {geometry.total_polygons:,}",
        f"Triangles: {geometry.total_triangles:,}",
        f"Average triangles: {geometry.average_triangle_count:,.2f}",
        f"Largest asset: {largest}",
    ]
    if attention:
        lines.extend(["", "Objects requiring attention:"])
        for result in attention[:max_attention_objects]:
            object_summary = result.validation.summary
            lines.append(
                f"- {result.asset.name}: {object_summary.errors} error(s), "
                f"{object_summary.warnings} warning(s)"
            )
        hidden = len(attention) - max_attention_objects
        if hidden > 0:
            lines.append(f"... and {hidden} more; export JSON for full details.")
    lines.append("=" * 72)
    return "\n".join(lines)
