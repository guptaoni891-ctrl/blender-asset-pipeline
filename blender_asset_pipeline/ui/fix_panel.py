"""Sidebar preview and controls for explicit asset fixes."""

from __future__ import annotations

import bpy

from ..constants import MAX_UI_FIX_ACTIONS

_RISK_ICONS = {
    "SAFE": "CHECKMARK",
    "CAUTION": "ERROR",
    "DESTRUCTIVE": "CANCEL",
}


class BAP_PT_fix_panel(bpy.types.Panel):
    """Preview-first fix controls nested under the validator."""

    bl_label = "Fix Preview"
    bl_idname = "BAP_PT_fix_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "BAP_PT_validation_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        """Draw planning controls, actions, and explicit apply controls."""
        layout = self.layout
        validation_state = context.scene.bap_validation_state
        fix_state = context.scene.bap_fix_state

        generate_column = layout.column()
        generate_column.enabled = validation_state.has_run and bool(
            validation_state.targets
        )
        generate_column.operator("bap.generate_fix_plan", icon="PRESET_NEW")
        layout.label(text="Generation only previews; it never applies fixes.")

        if not fix_state.has_plan:
            layout.label(text="Validate, then generate a fix plan.", icon="INFO")
            return
        if not fix_state.actions:
            layout.label(
                text="No fixes proposed for the validated objects.",
                icon="CHECKMARK",
            )
            layout.operator("bap.clear_fix_plan", icon="TRASH")
            return

        supported_count = sum(action.supported for action in fix_state.actions)
        selected_count = sum(
            action.supported and action.selected for action in fix_state.actions
        )
        layout.label(
            text=(
                f"{fix_state.object_count} object(s), "
                f"{supported_count} supported, {selected_count} selected"
            ),
            icon="INFO",
        )

        selection_row = layout.row(align=True)
        selection_row.operator("bap.select_all_safe_fixes", icon="CHECKBOX_HLT")
        selection_row.operator("bap.deselect_all_fixes", icon="CHECKBOX_DEHLT")

        current_object = None
        object_box = None
        visible_actions = fix_state.actions[:MAX_UI_FIX_ACTIONS]
        for action in visible_actions:
            if action.object_name != current_object:
                current_object = action.object_name
                object_box = layout.box()
                object_box.label(text=current_object, icon="MESH_DATA")

            action_row = object_box.row(align=True)
            action_row.enabled = action.supported
            action_row.prop(action, "selected", text="")
            action_row.label(
                text=f"{action.risk} - {action.title}",
                icon=_RISK_ICONS.get(action.risk, "QUESTION"),
            )
            detail_row = object_box.row()
            detail_row.scale_y = 0.8
            detail_row.label(text=action.description)
            if not action.supported:
                reason_row = object_box.row()
                reason_row.alert = True
                reason_row.label(
                    text=f"Manual/unsupported: {action.unsupported_reason}",
                    icon="LOCKED",
                )

        hidden_count = len(fix_state.actions) - len(visible_actions)
        if hidden_count > 0:
            layout.label(text=f"{hidden_count} additional action(s) hidden.")

        action_row = layout.row(align=True)
        action_row.operator("bap.apply_selected_fixes", icon="CHECKMARK")
        action_row.operator("bap.clear_fix_plan", icon="TRASH")
