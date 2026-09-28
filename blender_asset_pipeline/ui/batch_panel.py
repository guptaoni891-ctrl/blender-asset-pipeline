"""Summary-focused sidebar panel for batch validation."""

from __future__ import annotations

import bpy


class BAP_PT_batch_panel(bpy.types.Panel):
    """Run scene-wide validation and summarize the latest batch."""

    bl_label = "Batch Validation"
    bl_idname = "BAP_PT_batch_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "BAP_PT_validation_panel"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        """Draw batch controls, bounded summary, and JSON export action."""
        layout = self.layout
        action_column = layout.column(align=True)
        action_column.operator("bap.batch_validate_current_scene", icon="SCENE_DATA")
        action_column.operator("bap.batch_validate_all_scenes", icon="OUTLINER")

        state = context.scene.bap_batch_state
        if not state.has_run:
            layout.label(text="No batch validation has been run.", icon="INFO")
            return

        summary_box = layout.box()
        summary_box.label(text="Latest Batch", icon="PRESET")
        summary_box.label(text=f"Scope: {state.scope.replace('_', ' ').title()}")
        summary_box.label(text=f"Scenes: {state.scene_names or 'None'}")
        summary_box.label(text=f"Objects: {state.objects_discovered}")
        summary_box.label(
            text=(
                f"Validated {state.objects_validated}, "
                f"Skipped {state.objects_skipped}"
            )
        )
        row = summary_box.row(align=True)
        row.label(text=f"Clean {state.clean_objects}", icon="CHECKMARK")
        row.label(text=f"Warn {state.warning_objects}", icon="ERROR")
        row.label(text=f"Error {state.error_objects}", icon="CANCEL")

        checks_box = layout.box()
        checks_box.label(text="Checks")
        row = checks_box.row(align=True)
        row.label(text=f"Pass {state.checks_passed}", icon="CHECKMARK")
        row.label(text=f"Warn {state.checks_warning}", icon="ERROR")
        row.label(text=f"Error {state.checks_error}", icon="CANCEL")

        geometry_box = layout.box()
        geometry_box.label(text="Geometry", icon="MESH_DATA")
        geometry_box.label(text=f"Vertices: {state.total_vertices:,}")
        geometry_box.label(text=f"Polygons: {state.total_polygons:,}")
        geometry_box.label(text=f"Triangles: {state.total_triangles:,}")
        geometry_box.label(
            text=f"Average triangles: {state.average_triangle_count:,.1f}"
        )
        if state.largest_object_name:
            geometry_box.label(
                text=(
                    f"Largest: {state.largest_object_name} "
                    f"({state.largest_triangle_count:,})"
                )
            )

        if state.attention_objects:
            attention_box = layout.box()
            attention_box.label(text="Objects Requiring Attention", icon="ERROR")
            for item in state.attention_objects:
                attention_box.label(
                    text=(
                        f"{item.object_name} - {item.error_count} error(s), "
                        f"{item.warning_count} warning(s)"
                    )
                )
            hidden = state.attention_object_count - len(state.attention_objects)
            if hidden > 0:
                attention_box.label(
                    text=f"... and {hidden} more. Export JSON for details."
                )

        layout.operator("bap.export_batch_json", icon="FILE_TICK")
