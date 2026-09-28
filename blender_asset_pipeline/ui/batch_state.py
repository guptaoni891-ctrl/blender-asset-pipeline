"""Transient Blender UI state for the latest batch validation run."""

from __future__ import annotations

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

from ..batch.models import BatchObjectStatus, BatchValidationReport
from ..constants import MAX_UI_BATCH_ATTENTION_OBJECTS

_TRANSIENT_OPTIONS = {"SKIP_SAVE"}


class BAP_PG_batch_attention(bpy.types.PropertyGroup):
    """One bounded failing-object row shown in the sidebar."""

    object_name: StringProperty(options=_TRANSIENT_OPTIONS)
    warning_count: IntProperty(options=_TRANSIENT_OPTIONS)
    error_count: IntProperty(options=_TRANSIENT_OPTIONS)


class BAP_PG_batch_state(bpy.types.PropertyGroup):
    """Summary state corresponding to one cached batch report."""

    has_run: BoolProperty(default=False, options=_TRANSIENT_OPTIONS)
    run_id: StringProperty(options=_TRANSIENT_OPTIONS)
    scope: StringProperty(options=_TRANSIENT_OPTIONS)
    scene_names: StringProperty(options=_TRANSIENT_OPTIONS)
    objects_discovered: IntProperty(options=_TRANSIENT_OPTIONS)
    objects_validated: IntProperty(options=_TRANSIENT_OPTIONS)
    objects_skipped: IntProperty(options=_TRANSIENT_OPTIONS)
    checks_passed: IntProperty(options=_TRANSIENT_OPTIONS)
    checks_warning: IntProperty(options=_TRANSIENT_OPTIONS)
    checks_error: IntProperty(options=_TRANSIENT_OPTIONS)
    clean_objects: IntProperty(options=_TRANSIENT_OPTIONS)
    warning_objects: IntProperty(options=_TRANSIENT_OPTIONS)
    error_objects: IntProperty(options=_TRANSIENT_OPTIONS)
    total_vertices: IntProperty(options=_TRANSIENT_OPTIONS)
    total_polygons: IntProperty(options=_TRANSIENT_OPTIONS)
    total_triangles: IntProperty(options=_TRANSIENT_OPTIONS)
    largest_object_name: StringProperty(options=_TRANSIENT_OPTIONS)
    largest_triangle_count: IntProperty(options=_TRANSIENT_OPTIONS)
    average_triangle_count: FloatProperty(options=_TRANSIENT_OPTIONS)
    attention_object_count: IntProperty(options=_TRANSIENT_OPTIONS)
    attention_objects: CollectionProperty(
        type=BAP_PG_batch_attention,
        options=_TRANSIENT_OPTIONS,
    )


def clear_batch_state(state: BAP_PG_batch_state) -> None:
    """Invalidate displayed batch data without touching Blender assets."""
    state.attention_objects.clear()
    state.has_run = False
    state.run_id = ""
    state.scope = ""
    state.scene_names = ""
    state.objects_discovered = 0
    state.objects_validated = 0
    state.objects_skipped = 0
    state.checks_passed = 0
    state.checks_warning = 0
    state.checks_error = 0
    state.clean_objects = 0
    state.warning_objects = 0
    state.error_objects = 0
    state.total_vertices = 0
    state.total_polygons = 0
    state.total_triangles = 0
    state.largest_object_name = ""
    state.largest_triangle_count = 0
    state.average_triangle_count = 0.0
    state.attention_object_count = 0


def store_batch_report(
    state: BAP_PG_batch_state,
    run_id: str,
    report: BatchValidationReport,
) -> None:
    """Replace sidebar state with the matching latest batch summary."""
    clear_batch_state(state)
    summary = report.summary
    geometry = summary.geometry
    state.has_run = True
    state.run_id = run_id
    state.scope = report.scope.value
    state.scene_names = ", ".join(report.scene_names)
    state.objects_discovered = summary.objects_discovered
    state.objects_validated = summary.objects_validated
    state.objects_skipped = summary.objects_skipped
    state.checks_passed = summary.checks_passed
    state.checks_warning = summary.checks_warning
    state.checks_error = summary.checks_error
    state.clean_objects = summary.clean_objects
    state.warning_objects = summary.warning_objects
    state.error_objects = summary.error_objects
    state.total_vertices = geometry.total_vertices
    state.total_polygons = geometry.total_polygons
    state.total_triangles = geometry.total_triangles
    state.largest_object_name = geometry.largest_object_name or ""
    state.largest_triangle_count = geometry.largest_triangle_count
    state.average_triangle_count = geometry.average_triangle_count

    attention_objects = tuple(
        result
        for result in report.objects
        if result.status in {
            BatchObjectStatus.WARNING,
            BatchObjectStatus.ERROR,
        }
    )
    state.attention_object_count = len(attention_objects)
    for result in attention_objects[:MAX_UI_BATCH_ATTENTION_OBJECTS]:
        item = state.attention_objects.add()
        item.object_name = result.asset.name
        item.warning_count = result.validation.summary.warnings
        item.error_count = result.validation.summary.errors
