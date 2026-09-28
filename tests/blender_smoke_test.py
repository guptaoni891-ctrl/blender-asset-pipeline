"""Minimal registration/operator smoke test intended to run inside Blender."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

bpy.ops.preferences.addon_enable(module="blender_asset_pipeline")

cube = bpy.context.active_object
assert cube is not None and cube.type == "MESH"
cube.name = "environment_cube"
result = bpy.ops.bap.validate_active()
assert result == {"FINISHED"}, result

state = bpy.context.scene.bap_validation_state
assert state.has_run
assert state.validated_count == 1
assert len(state.results) > 0

bpy.ops.preferences.addon_disable(module="blender_asset_pipeline")
print("Blender Asset Pipeline smoke test passed")
