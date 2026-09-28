"""Minimal registration/operator smoke test intended to run inside Blender."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import bpy

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

bpy.ops.preferences.addon_enable(module="blender_asset_pipeline")

constants_module = importlib.import_module("blender_asset_pipeline.constants")
preferences_module = importlib.import_module("blender_asset_pipeline.preferences")
state_module = importlib.import_module("blender_asset_pipeline.ui.state")

addon_package_id = constants_module.ADDON_PACKAGE_ID
preferences_type = preferences_module.BAP_AddonPreferences
result_type = state_module.BAP_PG_validation_result
state_type = state_module.BAP_PG_validation_state

assert addon_package_id == "blender_asset_pipeline"
assert addon_package_id == preferences_module.__package__
assert preferences_type.bl_idname == addon_package_id
assert bpy.context.preferences.addons.get(addon_package_id) is not None

scene_state_property = bpy.types.Scene.bl_rna.properties["bap_validation_state"]
assert scene_state_property.is_skip_save
for property_name in (
    "has_run",
    "show_details",
    "object_count",
    "validated_count",
    "skipped_count",
    "passed_count",
    "warning_count",
    "error_count",
    "results",
):
    assert state_type.bl_rna.properties[property_name].is_skip_save
for property_name in ("object_name", "check_name", "severity", "message"):
    assert result_type.bl_rna.properties[property_name].is_skip_save

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
