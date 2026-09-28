"""Blender file-selector operator for exporting the latest batch report."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from ..reporting.json_report import batch_report_to_json
from ..reporting.runtime import get_latest_batch_run
from ..reporting.writer import write_json_report


class BAP_OT_export_batch_json(bpy.types.Operator, ExportHelper):
    """Export the exact batch report represented by current transient UI state."""

    bl_idname = "bap.export_batch_json"
    bl_label = "Export JSON Report..."
    bl_description = "Save the latest displayed batch validation as JSON"
    bl_options = {"REGISTER"}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Require displayed state with a matching in-memory report."""
        state = getattr(context.scene, "bap_batch_state", None)
        return bool(
            state
            and state.has_run
            and get_latest_batch_run(state.run_id) is not None
        )

    def invoke(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> set[str]:
        """Open Blender's file selector with a useful default filename."""
        if not self.filepath:
            self.filepath = "batch-validation-report.json"
        return super().invoke(context, event)

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Serialize and atomically write the matching cached report."""
        state = context.scene.bap_batch_state
        run = get_latest_batch_run(state.run_id)
        if run is None:
            self.report(
                {"ERROR"},
                "The displayed batch report is stale; run batch validation again",
            )
            return {"CANCELLED"}

        try:
            json_text = batch_report_to_json(
                run.report,
                run.generator,
                run.source,
                run.generated_at_utc,
            )
            destination = write_json_report(self.filepath, json_text)
        except (OSError, TypeError, ValueError) as error:
            self.report({"ERROR"}, f"Could not export JSON report: {error}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"JSON report saved to {destination}")
        return {"FINISHED"}
