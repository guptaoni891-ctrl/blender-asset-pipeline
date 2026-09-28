"""Read-only Blender capability snapshots used by fix planning."""

from __future__ import annotations

import bpy

from ..fixing.models import FixTargetSnapshot
from .blender_adapter import snapshot_object

_EPSILON = 1.0e-9


def _near(values: object, expected: tuple[float, ...]) -> bool:
    return all(
        abs(float(value) - target) <= _EPSILON
        for value, target in zip(values, expected, strict=True)
    )


def _has_delta_transforms(obj: bpy.types.Object) -> bool:
    if not _near(obj.delta_location, (0.0, 0.0, 0.0)):
        return True
    if not _near(obj.delta_scale, (1.0, 1.0, 1.0)):
        return True
    if obj.rotation_mode == "QUATERNION":
        return not _near(obj.delta_rotation_quaternion, (1.0, 0.0, 0.0, 0.0))
    return not _near(obj.delta_rotation_euler, (0.0, 0.0, 0.0))


def snapshot_fix_target(obj: bpy.types.Object) -> FixTargetSnapshot:
    """Capture fixability metadata without changing the Blender object."""
    asset = snapshot_object(obj)
    if obj.type != "MESH":
        return FixTargetSnapshot(
            object_key=str(obj.as_pointer()),
            asset=asset,
            object_is_editable=bool(getattr(obj, "is_editable", True)),
            is_library_linked=obj.library is not None,
            is_library_override=obj.override_library is not None,
        )

    mesh = obj.data
    usage = [0] * len(obj.material_slots)
    for polygon in mesh.polygons:
        if polygon.material_index < len(usage):
            usage[polygon.material_index] += 1

    locked_transforms = []
    if any(obj.lock_location):
        locked_transforms.append("LOCATION")
    if any(obj.lock_rotation):
        locked_transforms.append("ROTATION")
    if any(obj.lock_scale):
        locked_transforms.append("SCALE")

    return FixTargetSnapshot(
        object_key=str(obj.as_pointer()),
        asset=asset,
        object_is_editable=bool(getattr(obj, "is_editable", True)),
        mesh_is_editable=bool(getattr(mesh, "is_editable", True)),
        is_library_linked=obj.library is not None or mesh.library is not None,
        is_library_override=(
            obj.override_library is not None or mesh.override_library is not None
        ),
        mesh_data_users=mesh.users,
        material_slot_usage=tuple(usage),
        material_slots_are_data_linked=all(
            slot.link == "DATA" for slot in obj.material_slots
        ),
        has_parent=obj.parent is not None,
        has_children=bool(obj.children),
        has_constraints=bool(obj.constraints),
        has_modifiers=bool(obj.modifiers),
        has_animation_data=(
            obj.animation_data is not None or mesh.animation_data is not None
        ),
        has_shape_keys=mesh.shape_keys is not None,
        has_delta_transforms=_has_delta_transforms(obj),
        locked_transforms=tuple(locked_transforms),
    )
