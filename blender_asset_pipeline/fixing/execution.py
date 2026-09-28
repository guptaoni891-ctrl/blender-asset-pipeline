"""Blender-specific execution of explicitly selected fix actions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping

import bpy

from ..utils.fixing_adapter import snapshot_fix_target
from .models import (
    FixAction,
    FixExecutionReport,
    FixExecutionResult,
    FixExecutionStatus,
    FixKind,
)
from .planner import fingerprint_target

_TRANSFORM_FLAGS = {
    FixKind.APPLY_LOCATION: {"location": True},
    FixKind.APPLY_ROTATION: {"rotation": True},
    FixKind.APPLY_SCALE: {"scale": True},
}


def _in_view_layer(context: bpy.types.Context, obj: bpy.types.Object) -> bool:
    return context.view_layer.objects.get(obj.name) is obj


def _set_only_active(context: bpy.types.Context, obj: bpy.types.Object) -> None:
    for candidate in context.view_layer.objects:
        candidate.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def _apply_transform(
    context: bpy.types.Context,
    obj: bpy.types.Object,
    kind: FixKind,
) -> str:
    if not _in_view_layer(context, obj):
        raise RuntimeError("Object is not present in the current view layer")
    _set_only_active(context, obj)
    flags = {
        "location": False,
        "rotation": False,
        "scale": False,
        **_TRANSFORM_FLAGS[kind],
    }
    result = bpy.ops.object.transform_apply(
        location=flags["location"],
        rotation=flags["rotation"],
        scale=flags["scale"],
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender transform operation returned {sorted(result)}")
    return f"{kind.value.removeprefix('APPLY_').title()} applied."


def _remove_slots(
    obj: bpy.types.Object,
    remove_indices: set[int],
    canonical_indices: Mapping[int, int] | None = None,
) -> None:
    mesh = obj.data
    kept_indices = [
        index for index in range(len(obj.material_slots)) if index not in remove_indices
    ]
    new_index = {old_index: index for index, old_index in enumerate(kept_indices)}
    canonical_indices = canonical_indices or {}

    polygon_assignments = []
    for polygon in mesh.polygons:
        old_index = polygon.material_index
        retained_index = canonical_indices.get(old_index, old_index)
        if retained_index not in new_index:
            raise RuntimeError(
                f"Material slot {old_index + 1} is used by geometry and "
                "cannot be removed"
            )
        polygon_assignments.append((polygon, new_index[retained_index]))

    for polygon, material_index in polygon_assignments:
        polygon.material_index = material_index

    for slot_index in sorted(remove_indices, reverse=True):
        mesh.materials.pop(index=slot_index)
    mesh.update()


def _remove_empty_material_slots(obj: bpy.types.Object) -> str:
    empty_indices = {
        index
        for index, slot in enumerate(obj.material_slots)
        if slot.material is None
    }
    if not empty_indices:
        return "No empty material slots remained."
    _remove_slots(obj, empty_indices)
    return f"Removed {len(empty_indices)} empty material slot(s)."


def _consolidate_duplicate_material_slots(obj: bpy.types.Object) -> str:
    first_by_material: dict[int, int] = {}
    canonical_indices: dict[int, int] = {}
    remove_indices: set[int] = set()
    for index, slot in enumerate(obj.material_slots):
        material = slot.material
        if material is None:
            continue
        material_key = material.as_pointer()
        first_index = first_by_material.setdefault(material_key, index)
        canonical_indices[index] = first_index
        if first_index != index:
            remove_indices.add(index)

    if not remove_indices:
        return "No duplicate material slots remained."
    _remove_slots(obj, remove_indices, canonical_indices)
    return f"Consolidated {len(remove_indices)} duplicate material slot(s)."


def _execute_action(
    context: bpy.types.Context,
    obj: bpy.types.Object,
    action: FixAction,
) -> str:
    if action.kind is FixKind.RENAME:
        if not action.target_name:
            raise ValueError("Rename action has no target name")
        occupied = bpy.data.objects.get(action.target_name)
        if occupied is not None and occupied is not obj:
            raise RuntimeError(
                f"Target name '{action.target_name}' is no longer available"
            )
        obj.name = action.target_name
        if obj.name != action.target_name:
            raise RuntimeError(f"Blender assigned unexpected name '{obj.name}'")
        return f"Renamed object to '{obj.name}'."

    if action.kind in _TRANSFORM_FLAGS:
        return _apply_transform(context, obj, action.kind)
    if action.kind is FixKind.REMOVE_EMPTY_MATERIAL_SLOTS:
        return _remove_empty_material_slots(obj)
    if action.kind is FixKind.CONSOLIDATE_DUPLICATE_MATERIAL_SLOTS:
        return _consolidate_duplicate_material_slots(obj)
    raise ValueError(f"Fix kind '{action.kind.value}' has no automatic executor")


def _mode_token(mode: str) -> str:
    if mode.startswith("EDIT_"):
        return "EDIT"
    return {
        "PAINT_VERTEX": "VERTEX_PAINT",
        "PAINT_WEIGHT": "WEIGHT_PAINT",
        "PAINT_TEXTURE": "TEXTURE_PAINT",
        "PARTICLE": "PARTICLE_EDIT",
    }.get(mode, mode)


def _enter_object_mode(context: bpy.types.Context) -> None:
    active = context.view_layer.objects.active
    if active is not None and active.mode != "OBJECT":
        result = bpy.ops.object.mode_set(mode="OBJECT")
        if "FINISHED" not in result:
            raise RuntimeError("Could not enter Object Mode before applying fixes")


def _restore_context(
    context: bpy.types.Context,
    selected_objects: list[bpy.types.Object],
    active_object: bpy.types.Object | None,
    active_mode: str,
) -> list[str]:
    warnings = []
    for candidate in context.view_layer.objects:
        candidate.select_set(False)
    for obj in selected_objects:
        if _in_view_layer(context, obj):
            obj.select_set(True)

    if active_object is None or not _in_view_layer(context, active_object):
        context.view_layer.objects.active = None
        if active_object is not None:
            warnings.append(
                "The previous active object is no longer in the view layer."
            )
        return warnings

    context.view_layer.objects.active = active_object
    if active_mode != "OBJECT":
        try:
            result = bpy.ops.object.mode_set(mode=_mode_token(active_mode))
            if "FINISHED" not in result:
                warnings.append(f"Could not restore mode '{active_mode}'.")
        except RuntimeError as error:
            warnings.append(f"Could not restore mode '{active_mode}': {error}")
    return warnings


def _result(
    action: FixAction,
    status: FixExecutionStatus,
    message: str,
) -> FixExecutionResult:
    return FixExecutionResult(
        fix_id=action.fix_id,
        object_key=action.object_key,
        object_name=action.object_name,
        title=action.title,
        status=status,
        message=message,
    )


def execute_fix_actions(
    context: bpy.types.Context,
    actions: Iterable[FixAction],
    objects_by_key: Mapping[str, bpy.types.Object | None],
) -> FixExecutionReport:
    """Execute selected actions with stale checks and context restoration."""
    grouped: dict[str, list[FixAction]] = defaultdict(list)
    for action in actions:
        grouped[action.object_key].append(action)

    previous_selected = list(context.selected_objects)
    previous_active = context.view_layer.objects.active
    previous_mode = previous_active.mode if previous_active is not None else "OBJECT"
    results: list[FixExecutionResult] = []
    context_warnings: list[str] = []

    try:
        try:
            _enter_object_mode(context)
        except RuntimeError as error:
            results.extend(
                _result(action, FixExecutionStatus.FAILED, str(error))
                for object_actions in grouped.values()
                for action in object_actions
            )
        else:
            for object_key, object_actions in grouped.items():
                obj = objects_by_key.get(object_key)
                if obj is None:
                    results.extend(
                        _result(
                            action,
                            FixExecutionStatus.STALE,
                            "Object no longer exists; regenerate the fix plan.",
                        )
                        for action in object_actions
                    )
                    continue

                current_fingerprint = fingerprint_target(snapshot_fix_target(obj))
                expected_fingerprint = object_actions[0].expected_fingerprint
                if current_fingerprint != expected_fingerprint:
                    results.extend(
                        _result(
                            action,
                            FixExecutionStatus.STALE,
                            (
                                "Object state changed after preview; regenerate "
                                "the fix plan."
                            ),
                        )
                        for action in object_actions
                    )
                    continue

                for action in object_actions:
                    if not action.supported:
                        results.append(
                            _result(
                                action,
                                FixExecutionStatus.SKIPPED,
                                action.unsupported_reason
                                or "Action is unsupported.",
                            )
                        )
                        continue
                    try:
                        message = _execute_action(context, obj, action)
                    except (IndexError, RuntimeError, ValueError) as error:
                        results.append(
                            _result(action, FixExecutionStatus.FAILED, str(error))
                        )
                    else:
                        results.append(
                            _result(action, FixExecutionStatus.APPLIED, message)
                        )
    finally:
        context_warnings.extend(
            _restore_context(
                context,
                previous_selected,
                previous_active,
                previous_mode,
            )
        )

    return FixExecutionReport(tuple(results), tuple(context_warnings))
