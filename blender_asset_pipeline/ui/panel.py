"""3D View sidebar panel for asset validation."""

from __future__ import annotations

import bpy

from ..constants import MAX_UI_RESULTS, PANEL_CATEGORY
from ..preferences import get_preferences

_SEVERITY_ICONS = {
    "PASS": "CHECKMARK",
    "WARNING": "ERROR",
    "ERROR": "CANCEL",
}


class BAP_PT_validation_panel(bpy.types.Panel):
    """Controls and results for game-asset validation."""

    bl_label = "Asset Validator"
    bl_idname = "BAP_PT_validation_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = PANEL_CATEGORY

    def draw(self, context: bpy.types.Context) -> None:
        """Draw validation controls, current policy, and latest results."""
        layout = self.layout

        action_column = layout.column(align=True)
        action_column.operator("bap.validate_active", icon="OBJECT_DATA")
        action_column.operator("bap.validate_selected", icon="RESTRICT_SELECT_OFF")

        preferences = get_preferences(context)
        policy_box = layout.box()
        policy_box.label(text="Current Policy", icon="PREFERENCES")
        policy_box.label(text=f"Triangle budget: {preferences.max_triangle_count:,}")
        naming_label = preferences.naming_convention.replace("_", " ").title()
        policy_box.label(text=f"Naming: {naming_label}")
        prefix = preferences.required_prefix or "None"
        policy_box.label(text=f"Required prefix: {prefix}")
        policy_box.label(
            text=f"Transform tolerance: {preferences.transform_tolerance:g}"
        )

        state = context.scene.bap_validation_state
        if not state.has_run:
            layout.label(text="No validation has been run.", icon="INFO")
            return

        summary_box = layout.box()
        if state.error_count:
            result_icon = "CANCEL"
        elif state.warning_count:
            result_icon = "ERROR"
        else:
            result_icon = "CHECKMARK"
        summary_box.label(
            text=f"{state.validated_count} validated, {state.skipped_count} skipped",
            icon=result_icon,
        )
        row = summary_box.row(align=True)
        row.label(text=f"Pass {state.passed_count}", icon="CHECKMARK")
        row.label(text=f"Warn {state.warning_count}", icon="ERROR")
        row.label(text=f"Error {state.error_count}", icon="CANCEL")

        layout.prop(state, "show_details", toggle=True)
        if not state.show_details:
            return

        current_object = None
        object_box = None
        visible_results = state.results[:MAX_UI_RESULTS]
        for result in visible_results:
            if result.object_name != current_object:
                current_object = result.object_name
                object_box = layout.box()
                object_box.label(text=current_object, icon="MESH_DATA")
            row = object_box.row(align=True)
            row.label(
                text=result.check_name,
                icon=_SEVERITY_ICONS.get(result.severity, "QUESTION"),
            )
            detail_row = object_box.row()
            detail_row.scale_y = 0.8
            detail_row.label(text=result.message)

        hidden_count = len(state.results) - len(visible_results)
        if hidden_count > 0:
            layout.label(
                text=f"{hidden_count} more result(s); see the system console.",
                icon="CONSOLE",
            )
