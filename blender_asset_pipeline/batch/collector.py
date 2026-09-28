"""Blender object discovery and snapshot collection for batch validation."""

from __future__ import annotations

from collections.abc import Iterable

import bpy

from ..utils.blender_adapter import snapshot_object
from .models import BatchCollection, BatchScope, BatchTarget


def _collect_scenes(
    scope: BatchScope,
    scenes: Iterable[bpy.types.Scene],
) -> BatchCollection:
    ordered_scenes = tuple(
        sorted(scenes, key=lambda scene: (scene.name.casefold(), scene.name))
    )
    objects_by_key: dict[str, bpy.types.Object] = {}
    memberships: dict[str, set[str]] = {}

    for scene in ordered_scenes:
        for obj in scene.objects:
            key = str(obj.as_pointer())
            objects_by_key.setdefault(key, obj)
            memberships.setdefault(key, set()).add(scene.name)

    targets = tuple(
        BatchTarget(
            target_key=key,
            asset=snapshot_object(obj),
            scene_memberships=tuple(memberships[key]),
        )
        for key, obj in objects_by_key.items()
    )
    return BatchCollection(
        scope=scope,
        scene_names=tuple(scene.name for scene in ordered_scenes),
        targets=targets,
    )


def collect_current_scene(scene: bpy.types.Scene) -> BatchCollection:
    """Collect every object belonging to the active scene."""
    return _collect_scenes(BatchScope.CURRENT_SCENE, (scene,))


def collect_all_scenes(
    scenes: Iterable[bpy.types.Scene],
) -> BatchCollection:
    """Collect unique objects and memberships across all supplied scenes."""
    return _collect_scenes(BatchScope.ALL_SCENES, scenes)
