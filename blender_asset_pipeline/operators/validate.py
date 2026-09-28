"""Blender operators that coordinate read-only validation runs."""

from __future__ import annotations

from collections.abc import Sequence

import bpy

from ..preferences import get_preferences
from ..ui.fix_state import clear_fix_plan
from ..ui.state import store_reports
from ..utils.blender_adapter import snapshot_object
from ..validation import format_reports, validate_asset


def _run_validation(
    operator: bpy.types.Operator,
    context: bpy.types.Context,
    objects: Sequence[bpy.types.Object],
) -> set[str]:
    """Validate objects, update transient UI state, and print the full report."""
    if not objects:
        operator.report({"WARNING"}, "No objects available to validate")
        return {"CANCELLED"}

    config = get_preferences(context).to_validation_config()
    reports = [validate_asset(snapshot_object(obj), config) for obj in objects]
    store_reports(context.scene.bap_validation_state, reports, list(objects))
    clear_fix_plan(context.scene.bap_fix_state)
    print(format_reports(reports))

    errors = sum(report.summary.errors for report in reports)
    warnings = sum(report.summary.warnings for report in reports)
    validated = sum(report.was_validated for report in reports)
    skipped = len(reports) - validated
    message = (
        f"Validated {validated} object(s), skipped {skipped}: "
        f"{errors} error(s), {warnings} warning(s)"
    )
    operator.report({"WARNING" if errors or warnings else "INFO"}, message)
    return {"FINISHED"}


class BAP_OT_validate_active(bpy.types.Operator):
    """Validate the active object."""

    bl_idname = "bap.validate_active"
    bl_label = "Validate Active Object"
    bl_description = "Validate the active object without changing it"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Run validation for the active object."""
        active_object = context.active_object
        return _run_validation(self, context, [active_object] if active_object else [])


class BAP_OT_validate_selected(bpy.types.Operator):
    """Validate every selected object."""

    bl_idname = "bap.validate_selected"
    bl_label = "Validate Selected Objects"
    bl_description = "Validate all selected objects without changing them"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Run validation for the current selection."""
        return _run_validation(self, context, list(context.selected_objects))
