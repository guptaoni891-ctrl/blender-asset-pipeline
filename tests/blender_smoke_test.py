"""Minimal registration/operator smoke test intended to run inside Blender."""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
from pathlib import Path

import bpy

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

bpy.ops.preferences.addon_enable(module="blender_asset_pipeline")

constants_module = importlib.import_module("blender_asset_pipeline.constants")
preferences_module = importlib.import_module("blender_asset_pipeline.preferences")
state_module = importlib.import_module("blender_asset_pipeline.ui.state")
fix_state_module = importlib.import_module("blender_asset_pipeline.ui.fix_state")
planner_module = importlib.import_module("blender_asset_pipeline.fixing.planner")
batch_state_module = importlib.import_module("blender_asset_pipeline.ui.batch_state")

addon_package_id = constants_module.ADDON_PACKAGE_ID
preferences_type = preferences_module.BAP_AddonPreferences
result_type = state_module.BAP_PG_validation_result
state_type = state_module.BAP_PG_validation_state
target_type = state_module.BAP_PG_validation_target
fix_action_type = fix_state_module.BAP_PG_fix_action
fix_state_type = fix_state_module.BAP_PG_fix_state
batch_attention_type = batch_state_module.BAP_PG_batch_attention
batch_state_type = batch_state_module.BAP_PG_batch_state

assert addon_package_id == "blender_asset_pipeline"
assert addon_package_id == preferences_module.__package__
assert preferences_type.bl_idname == addon_package_id
assert bpy.context.preferences.addons.get(addon_package_id) is not None

scene_state_property = bpy.types.Scene.bl_rna.properties["bap_validation_state"]
assert scene_state_property.is_skip_save
scene_fix_property = bpy.types.Scene.bl_rna.properties["bap_fix_state"]
assert scene_fix_property.is_skip_save
scene_batch_property = bpy.types.Scene.bl_rna.properties["bap_batch_state"]
assert scene_batch_property.is_skip_save
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
    "targets",
):
    assert state_type.bl_rna.properties[property_name].is_skip_save
for property_name in ("object_name", "check_name", "severity", "message"):
    assert result_type.bl_rna.properties[property_name].is_skip_save
for property_name in ("object_key", "object_name", "target"):
    assert target_type.bl_rna.properties[property_name].is_skip_save
for property_name in ("has_plan", "object_count", "actions"):
    assert fix_state_type.bl_rna.properties[property_name].is_skip_save
for property_name in (
    "fix_id",
    "object_key",
    "object_name",
    "category",
    "kind",
    "title",
    "description",
    "risk",
    "selected",
    "default_selected",
    "supported",
    "unsupported_reason",
    "expected_fingerprint",
    "target_name",
    "target",
):
    assert fix_action_type.bl_rna.properties[property_name].is_skip_save
for property_name in (
    "has_run",
    "run_id",
    "scope",
    "scene_names",
    "objects_discovered",
    "objects_validated",
    "objects_skipped",
    "checks_passed",
    "checks_warning",
    "checks_error",
    "clean_objects",
    "warning_objects",
    "error_objects",
    "total_vertices",
    "total_polygons",
    "total_triangles",
    "largest_object_name",
    "largest_triangle_count",
    "average_triangle_count",
    "attention_object_count",
    "attention_objects",
):
    assert batch_state_type.bl_rna.properties[property_name].is_skip_save
for property_name in ("object_name", "warning_count", "error_count"):
    assert batch_attention_type.bl_rna.properties[property_name].is_skip_save

cube = bpy.context.active_object
assert cube is not None and cube.type == "MESH"
cube.name = "Bad Cube"
cube.scale = (2.0, 1.0, 1.0)

mesh = cube.data
mesh.materials.clear()
material = bpy.data.materials.new("smoke_material")
mesh.materials.append(material)
bpy.ops.object.material_slot_add()
mesh.materials.append(material)
assert len(cube.material_slots) == 3
assert cube.material_slots[1].material is None
assert cube.material_slots[2].material is material
mesh.polygons[0].material_index = 2
mesh.polygons[1].material_index = 2

result = bpy.ops.bap.validate_active()
assert result == {"FINISHED"}, result

state = bpy.context.scene.bap_validation_state
assert state.has_run
assert state.validated_count == 1
assert len(state.results) > 0
assert state.error_count > 0

result = bpy.ops.bap.generate_fix_plan()
assert result == {"FINISHED"}, result
fix_state = bpy.context.scene.bap_fix_state
assert fix_state.has_plan
actions_by_kind = {action.kind: action for action in fix_state.actions}
for expected_kind in (
    "RENAME",
    "APPLY_SCALE",
    "REMOVE_EMPTY_MATERIAL_SLOTS",
    "CONSOLIDATE_DUPLICATE_MATERIAL_SLOTS",
):
    assert expected_kind in actions_by_kind

assert actions_by_kind["RENAME"].selected
assert actions_by_kind["APPLY_SCALE"].selected
assert not actions_by_kind["REMOVE_EMPTY_MATERIAL_SLOTS"].selected
assert not actions_by_kind["CONSOLIDATE_DUPLICATE_MATERIAL_SLOTS"].selected

world_positions_before = [
    tuple(cube.matrix_world @ vertex.co) for vertex in cube.data.vertices
]
result = bpy.ops.bap.apply_selected_fixes("EXEC_DEFAULT")
assert result == {"FINISHED"}, result
assert cube.name == "bad_cube"
assert tuple(cube.scale) == (1.0, 1.0, 1.0)
world_positions_after = [
    tuple(cube.matrix_world @ vertex.co) for vertex in cube.data.vertices
]
for before, after in zip(world_positions_before, world_positions_after, strict=True):
    assert all(
        abs(before_component - after_component) < 1.0e-6
        for before_component, after_component in zip(before, after, strict=True)
    )
assert bpy.context.scene.bap_validation_state.error_count >= 1

result = bpy.ops.bap.generate_fix_plan()
assert result == {"FINISHED"}, result
fix_state = bpy.context.scene.bap_fix_state
material_fix_kinds = {
    "REMOVE_EMPTY_MATERIAL_SLOTS",
    "CONSOLIDATE_DUPLICATE_MATERIAL_SLOTS",
}
for action in fix_state.actions:
    action.selected = action.kind in material_fix_kinds
assert sum(action.selected for action in fix_state.actions) == 2

result = bpy.ops.bap.apply_selected_fixes("EXEC_DEFAULT")
assert result == {"FINISHED"}, result
assert len(cube.material_slots) == 1
assert all(polygon.material_index == 0 for polygon in mesh.polygons)
assert bpy.context.scene.bap_validation_state.error_count == 0

# Generate Fix Plan must refresh validation from the same snapshot it plans.
# A negative scale introduced after the clean validation is cautious and opt-in.
cube.scale = (-1.0, 1.0, 1.0)
assert bpy.context.scene.bap_validation_state.error_count == 0
result = bpy.ops.bap.generate_fix_plan()
assert result == {"FINISHED"}, result
assert bpy.context.scene.bap_validation_state.error_count > 0
negative_scale_action = next(
    action
    for action in bpy.context.scene.bap_fix_state.actions
    if action.kind == "APPLY_SCALE"
)
assert negative_scale_action.supported
assert negative_scale_action.risk == "CAUTION"
assert not negative_scale_action.selected
assert "mirrored/negative" in negative_scale_action.description
assert not bpy.ops.bap.apply_selected_fixes.poll()

# Zero and near-zero scales remain previewable but can never be auto-applied.
for unsafe_scale in (
    (0.0, 1.0, 1.0),
    (planner_module.SCALE_NEAR_ZERO_EPSILON / 2.0, 1.0, 1.0),
):
    cube.scale = unsafe_scale
    result = bpy.ops.bap.generate_fix_plan()
    assert result == {"FINISHED"}, result
    unsafe_scale_action = next(
        action
        for action in bpy.context.scene.bap_fix_state.actions
        if action.kind == "APPLY_SCALE"
    )
    assert not unsafe_scale_action.supported
    assert not unsafe_scale_action.selected
    assert "degenerate or collapsed geometry" in unsafe_scale_action.description
    assert not bpy.ops.bap.apply_selected_fixes.poll()

cube.scale = (1.0, 1.0, 1.0)
result = bpy.ops.bap.validate_active()
assert result == {"FINISHED"}, result
assert bpy.context.scene.bap_validation_state.error_count == 0

# A material state change after preview must stale the whole object plan.
cube.location = (1.0, 0.0, 0.0)
result = bpy.ops.bap.validate_active()
assert result == {"FINISHED"}, result
result = bpy.ops.bap.generate_fix_plan()
assert result == {"FINISHED"}, result
fix_state = bpy.context.scene.bap_fix_state
for action in fix_state.actions:
    action.selected = action.kind == "APPLY_LOCATION"
assert sum(action.selected for action in fix_state.actions) == 1
mesh.materials.append(material)
result = bpy.ops.bap.apply_selected_fixes("EXEC_DEFAULT")
assert result == {"FINISHED"}, result
assert tuple(cube.location) == (1.0, 0.0, 0.0)

# Restore the smoke-test scene explicitly and confirm validation is clean.
mesh.materials.pop(index=1)
cube.location = (0.0, 0.0, 0.0)
result = bpy.ops.bap.validate_active()
assert result == {"FINISHED"}, result
assert bpy.context.scene.bap_validation_state.error_count == 0

# Batch validation remains read-only and deduplicates shared objects by identity.
main_scene = bpy.context.scene
valid_mesh = mesh.copy()
valid_mesh.name = "batch_valid_mesh"
valid_object = bpy.data.objects.new("batch_valid", valid_mesh)
main_scene.collection.objects.link(valid_object)

invalid_mesh = mesh.copy()
invalid_mesh.name = "batch_invalid_mesh"
invalid_object = bpy.data.objects.new("Bad Batch Asset", invalid_mesh)
invalid_object.scale = (2.0, 1.0, 1.0)
main_scene.collection.objects.link(invalid_object)

unsupported_object = bpy.data.objects.new("batch_empty", None)
main_scene.collection.objects.link(unsupported_object)

second_scene = bpy.data.scenes.new("Batch Second")
second_scene.collection.objects.link(invalid_object)
second_mesh = mesh.copy()
second_mesh.name = "second_asset_mesh"
second_object = bpy.data.objects.new("second_asset", second_mesh)
second_scene.collection.objects.link(second_object)

main_scale_before = tuple(invalid_object.scale)
result = bpy.ops.bap.batch_validate_current_scene()
assert result == {"FINISHED"}, result
batch_state = main_scene.bap_batch_state
current_unique = {obj.as_pointer() for obj in main_scene.objects}
assert batch_state.has_run
assert batch_state.scope == "CURRENT_SCENE"
assert batch_state.objects_discovered == len(current_unique)
assert batch_state.objects_validated == sum(
    obj.type == "MESH" for obj in main_scene.objects
)
assert batch_state.objects_skipped == sum(
    obj.type != "MESH" for obj in main_scene.objects
)
assert tuple(invalid_object.scale) == main_scale_before

result = bpy.ops.bap.batch_validate_all_scenes()
assert result == {"FINISHED"}, result
batch_state = main_scene.bap_batch_state
all_unique = {
    obj.as_pointer()
    for scene in bpy.data.scenes
    for obj in scene.objects
}
assert batch_state.scope == "ALL_SCENES"
assert batch_state.objects_discovered == len(all_unique)
assert batch_state.objects_validated == sum(
    obj.type == "MESH" for obj in bpy.data.objects if obj.as_pointer() in all_unique
)
assert batch_state.objects_skipped == sum(
    obj.type != "MESH" for obj in bpy.data.objects if obj.as_pointer() in all_unique
)
assert batch_state.error_objects >= 1
assert len(batch_state.attention_objects) >= 1
assert tuple(invalid_object.scale) == main_scale_before

with tempfile.TemporaryDirectory() as temporary_directory:
    requested_path = Path(temporary_directory) / "batch-smoke-report"
    result = bpy.ops.bap.export_batch_json(filepath=str(requested_path))
    assert result == {"FINISHED"}, result
    report_path = requested_path.with_name(requested_path.name + ".json")
    report_text = report_path.read_text(encoding="utf-8")
    report_json = json.loads(report_text)

assert report_text.endswith("\n")
assert report_json["schema_version"] == "1.0"
assert report_json["scope"]["type"] == "ALL_SCENES"
assert not report_json["source"]["is_saved"]
assert report_json["source"]["blend_filepath"] is None
assert len(report_json["objects"]) == len(all_unique)
assert sum(
    item["name"] == invalid_object.name for item in report_json["objects"]
) == 1
invalid_json = next(
    item for item in report_json["objects"] if item["name"] == invalid_object.name
)
assert invalid_json["scene_memberships"] == ["Batch Second", main_scene.name]
assert any(
    check["check_id"] == "scale" and check["severity"] == "ERROR"
    for check in invalid_json["checks"]
)
unsupported_json = next(
    item
    for item in report_json["objects"]
    if item["name"] == unsupported_object.name
)
assert unsupported_json["state"] == "SKIPPED"
assert str(invalid_object.as_pointer()) not in report_text

bpy.ops.preferences.addon_disable(module="blender_asset_pipeline")
assert not hasattr(bpy.types.Scene, "bap_validation_state")
assert not hasattr(bpy.types.Scene, "bap_fix_state")
assert not hasattr(bpy.types.Scene, "bap_batch_state")
print("Blender Asset Pipeline smoke test passed")
