"""Transient Blender UI state for the most recent validation run."""

import bpy
from bpy.props import BoolProperty, CollectionProperty, IntProperty, StringProperty

from ..models import ObjectValidationReport
from ..validation.reporting import summarize_reports

_TRANSIENT_OPTIONS = {"SKIP_SAVE"}


class BAP_PG_validation_result(bpy.types.PropertyGroup):
    """One validation result rendered in the sidebar."""

    object_name: StringProperty(options=_TRANSIENT_OPTIONS)
    check_name: StringProperty(options=_TRANSIENT_OPTIONS)
    severity: StringProperty(options=_TRANSIENT_OPTIONS)
    message: StringProperty(options=_TRANSIENT_OPTIONS)


class BAP_PG_validation_state(bpy.types.PropertyGroup):
    """Summary and result collection for the latest run."""

    has_run: BoolProperty(default=False, options=_TRANSIENT_OPTIONS)
    show_details: BoolProperty(
        name="Show Details",
        default=True,
        options=_TRANSIENT_OPTIONS,
    )
    object_count: IntProperty(default=0, options=_TRANSIENT_OPTIONS)
    validated_count: IntProperty(default=0, options=_TRANSIENT_OPTIONS)
    skipped_count: IntProperty(default=0, options=_TRANSIENT_OPTIONS)
    passed_count: IntProperty(default=0, options=_TRANSIENT_OPTIONS)
    warning_count: IntProperty(default=0, options=_TRANSIENT_OPTIONS)
    error_count: IntProperty(default=0, options=_TRANSIENT_OPTIONS)
    results: CollectionProperty(
        type=BAP_PG_validation_result,
        options=_TRANSIENT_OPTIONS,
    )


def store_reports(
    state: BAP_PG_validation_state,
    reports: list[ObjectValidationReport],
) -> None:
    """Replace sidebar state with a completed validation run."""
    summary = summarize_reports(reports)
    state.results.clear()
    state.has_run = True
    state.object_count = len(reports)
    state.validated_count = sum(report.was_validated for report in reports)
    state.skipped_count = state.object_count - state.validated_count
    state.passed_count = summary.passed
    state.warning_count = summary.warnings
    state.error_count = summary.errors

    for report in reports:
        for result in report.results:
            item = state.results.add()
            item.object_name = report.object_name
            item.check_name = result.check_name
            item.severity = result.severity.name
            item.message = result.message
