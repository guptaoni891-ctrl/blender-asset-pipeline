"""Blender operators coordinating read-only scene batch validation."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import bpy

from ..batch.collector import collect_all_scenes, collect_current_scene
from ..batch.engine import validate_batch
from ..batch.reporting import format_batch_report
from ..constants import ADDON_VERSION
from ..preferences import get_preferences
from ..reporting.models import LatestBatchRun, ReportGenerator, ReportSource
from ..reporting.runtime import clear_latest_batch_run, set_latest_batch_run
from ..ui.batch_state import clear_batch_state, store_batch_report


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _run_batch(
    operator: bpy.types.Operator,
    context: bpy.types.Context,
    all_scenes: bool,
) -> set[str]:
    clear_latest_batch_run()
    for scene in bpy.data.scenes:
        clear_batch_state(scene.bap_batch_state)

    try:
        collection = (
            collect_all_scenes(bpy.data.scenes)
            if all_scenes
            else collect_current_scene(context.scene)
        )
        config = get_preferences(context).to_validation_config()
        report = validate_batch(collection, config)
    except (RuntimeError, ValueError) as error:
        operator.report({"ERROR"}, f"Batch validation failed: {error}")
        return {"CANCELLED"}
    run_id = uuid4().hex
    version = ".".join(str(component) for component in ADDON_VERSION)
    filepath = bpy.data.filepath or None
    latest_run = LatestBatchRun(
        run_id=run_id,
        report=report,
        generator=ReportGenerator(
            tool_name="Blender Asset Pipeline",
            addon_version=version,
            blender_version=bpy.app.version_string,
        ),
        source=ReportSource(
            blend_filepath=filepath,
            is_saved=bool(filepath),
        ),
        generated_at_utc=_utc_timestamp(),
    )
    store_batch_report(context.scene.bap_batch_state, run_id, report)
    set_latest_batch_run(latest_run)
    print(format_batch_report(report))

    summary = report.summary
    severity = (
        "WARNING"
        if summary.checks_error or summary.checks_warning
        else "INFO"
    )
    operator.report(
        {severity},
        (
            f"Batch validated {summary.objects_validated} object(s), "
            f"skipped {summary.objects_skipped}: "
            f"{summary.error_objects} object(s) with errors"
        ),
    )
    return {"FINISHED"}


class BAP_OT_batch_validate_current_scene(bpy.types.Operator):
    """Validate every unique object in the current scene without mutation."""

    bl_idname = "bap.batch_validate_current_scene"
    bl_label = "Validate Current Scene"
    bl_description = "Batch validate all objects in the current scene"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Run a read-only current-scene batch."""
        return _run_batch(self, context, all_scenes=False)


class BAP_OT_batch_validate_all_scenes(bpy.types.Operator):
    """Validate unique objects across all scenes without mutation."""

    bl_idname = "bap.batch_validate_all_scenes"
    bl_label = "Validate All Scenes"
    bl_description = "Batch validate unique objects across every Blender scene"
    bl_options = {"REGISTER"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        """Run a read-only all-scenes batch."""
        return _run_batch(self, context, all_scenes=True)
