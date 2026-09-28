"""Unit tests for pure fix naming, planning, and fingerprints."""

from __future__ import annotations

import unittest
from dataclasses import replace

from blender_asset_pipeline.fixing import (
    FixKind,
    FixRisk,
    FixTargetSnapshot,
    collision_safe_name,
    fingerprint_target,
    normalize_object_name,
    plan_fixes,
)
from blender_asset_pipeline.models import (
    AssetSnapshot,
    MaterialSlotSnapshot,
    NamingConvention,
    TextureReference,
    ValidationConfig,
)
from blender_asset_pipeline.validation import validate_asset


def fixable_asset(**overrides: object) -> AssetSnapshot:
    """Build a valid mesh snapshot with optional fix-related problems."""
    values: dict[str, object] = {
        "name": "environment_crate",
        "object_type": "MESH",
        "vertex_count": 8,
        "edge_count": 12,
        "polygon_count": 6,
        "triangle_count": 12,
        "uv_map_count": 1,
        "material_slots": (MaterialSlotSnapshot(0, "body", "material-1"),),
    }
    values.update(overrides)
    return AssetSnapshot(**values)  # type: ignore[arg-type]


def plan_for(
    target: FixTargetSnapshot,
    config: ValidationConfig | None = None,
    existing_names: tuple[str, ...] = (),
):
    """Validate a target and produce its fix plan."""
    active_config = config or ValidationConfig()
    report = validate_asset(target.asset, active_config)
    return plan_fixes(
        ((target, report),),
        active_config,
        existing_names or (target.asset.name,),
    )


class NamingFixTests(unittest.TestCase):
    """Exercise deterministic naming behavior."""

    def test_lower_snake_case_normalization_and_prefix(self) -> None:
        config = ValidationConfig(required_prefix="sm_")

        self.assertEqual(
            normalize_object_name("Bad Asset.001", config),
            "sm_bad_asset",
        )
        self.assertEqual(
            normalize_object_name("sm_Already Prefixed", config),
            "sm_already_prefixed",
        )

    def test_upper_camel_case_normalization_and_prefix(self) -> None:
        config = ValidationConfig(
            naming_convention=NamingConvention.UPPER_CAMEL_CASE,
            required_prefix="SM_",
        )

        self.assertEqual(
            normalize_object_name("environment_crate", config),
            "SM_EnvironmentCrate",
        )

    def test_collision_names_are_clean_and_predictable(self) -> None:
        existing = ("environment_crate", "environment_crate_002")

        self.assertEqual(
            collision_safe_name(
                "environment_crate",
                existing,
                "Bad Name",
                NamingConvention.LOWER_SNAKE_CASE,
            ),
            "environment_crate_003",
        )
        self.assertEqual(
            collision_safe_name(
                "EnvironmentCrate",
                ("EnvironmentCrate",),
                "Bad Name",
                NamingConvention.UPPER_CAMEL_CASE,
            ),
            "EnvironmentCrate002",
        )


class FixPlannerTests(unittest.TestCase):
    """Exercise action support, risk, defaults, and stale fingerprints."""

    def test_safe_and_caution_actions_have_correct_defaults(self) -> None:
        slots = (
            MaterialSlotSnapshot(0, "body", "material-1"),
            MaterialSlotSnapshot(1, None, None),
            MaterialSlotSnapshot(2, "body", "material-1"),
        )
        target = FixTargetSnapshot(
            "object-1",
            fixable_asset(
                name="Bad Asset",
                location=(1.0, 0.0, 0.0),
                rotation=(0.0, 0.25, 0.0),
                scale=(2.0, 2.0, 2.0),
                material_slots=slots,
            ),
            material_slot_usage=(6, 0, 0),
        )

        actions = {action.kind: action for action in plan_for(target).actions}

        self.assertEqual(actions[FixKind.RENAME].risk, FixRisk.SAFE)
        self.assertTrue(actions[FixKind.RENAME].default_selected)
        self.assertTrue(actions[FixKind.APPLY_SCALE].selected)
        self.assertEqual(actions[FixKind.APPLY_LOCATION].risk, FixRisk.CAUTION)
        self.assertFalse(actions[FixKind.APPLY_LOCATION].selected)
        self.assertEqual(actions[FixKind.APPLY_ROTATION].risk, FixRisk.CAUTION)
        self.assertFalse(actions[FixKind.APPLY_ROTATION].selected)
        self.assertEqual(
            actions[FixKind.REMOVE_EMPTY_MATERIAL_SLOTS].risk,
            FixRisk.CAUTION,
        )
        self.assertFalse(
            actions[FixKind.REMOVE_EMPTY_MATERIAL_SLOTS].default_selected
        )
        self.assertFalse(
            actions[FixKind.CONSOLIDATE_DUPLICATE_MATERIAL_SLOTS].selected
        )

    def test_manual_categories_are_visible_but_unsupported(self) -> None:
        missing_texture = TextureReference(
            "body",
            "Base Color",
            "missing",
            "/missing.png",
            False,
            "file not found",
        )
        target = FixTargetSnapshot(
            "object-1",
            fixable_asset(
                triangle_count=200,
                uv_map_count=0,
                material_slots=(),
                texture_references=(missing_texture,),
            ),
        )
        config = ValidationConfig(max_triangle_count=100)

        actions = {action.kind: action for action in plan_for(target, config).actions}

        for kind in (
            FixKind.MANUAL_MATERIAL,
            FixKind.MANUAL_UV,
            FixKind.MANUAL_TRIANGLE_BUDGET,
            FixKind.MANUAL_TEXTURE,
        ):
            self.assertIn(kind, actions)
            self.assertFalse(actions[kind].supported)
            self.assertFalse(actions[kind].selected)
            self.assertTrue(actions[kind].unsupported_reason)

    def test_empty_geometry_is_visible_but_unsupported(self) -> None:
        target = FixTargetSnapshot(
            "object-1",
            fixable_asset(
                vertex_count=0,
                edge_count=0,
                polygon_count=0,
                triangle_count=0,
            ),
        )
        action = next(
            action
            for action in plan_for(target).actions
            if action.kind is FixKind.MANUAL_GEOMETRY
        )

        self.assertFalse(action.supported)
        self.assertIn("authoring", action.unsupported_reason)

    def test_non_mesh_object_produces_unsupported_action(self) -> None:
        target = FixTargetSnapshot(
            "object-1",
            AssetSnapshot("key_light", "LIGHT"),
        )
        plan = plan_for(target)

        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].kind, FixKind.UNSUPPORTED_OBJECT)
        self.assertFalse(plan.actions[0].supported)

    def test_generic_name_requires_user_description(self) -> None:
        target = FixTargetSnapshot("object-1", fixable_asset(name="Cube"))
        action = next(
            action
            for action in plan_for(target).actions
            if action.kind is FixKind.MANUAL_NAME
        )

        self.assertFalse(action.supported)
        self.assertIn("descriptive", action.unsupported_reason)

    def test_shared_mesh_transform_is_not_guessed_at(self) -> None:
        target = FixTargetSnapshot(
            "object-1",
            fixable_asset(scale=(2.0, 2.0, 2.0)),
            mesh_data_users=2,
        )
        action = next(
            action
            for action in plan_for(target).actions
            if action.kind is FixKind.APPLY_SCALE
        )

        self.assertFalse(action.supported)
        self.assertIn("shared", action.unsupported_reason.lower())

    def test_used_empty_material_slot_is_unsupported(self) -> None:
        target = FixTargetSnapshot(
            "object-1",
            fixable_asset(
                material_slots=(
                    MaterialSlotSnapshot(0, "body", "material-1"),
                    MaterialSlotSnapshot(1, None, None),
                )
            ),
            material_slot_usage=(0, 6),
        )
        action = next(
            action
            for action in plan_for(target).actions
            if action.kind is FixKind.REMOVE_EMPTY_MATERIAL_SLOTS
        )

        self.assertFalse(action.supported)
        self.assertIn("assigned to faces", action.unsupported_reason)

    def test_planner_uses_collision_safe_target_name(self) -> None:
        target = FixTargetSnapshot("object-1", fixable_asset(name="Bad Name"))
        action = next(
            action
            for action in plan_for(
                target,
                existing_names=("Bad Name", "bad_name"),
            ).actions
            if action.kind is FixKind.RENAME
        )

        self.assertEqual(action.target_name, "bad_name_002")

    def test_multi_object_planning_reserves_proposed_names(self) -> None:
        first = FixTargetSnapshot("object-1", fixable_asset(name="Bad Name"))
        second = FixTargetSnapshot("object-2", fixable_asset(name="Bad-Name"))
        config = ValidationConfig()
        pairs = (
            (first, validate_asset(first.asset, config)),
            (second, validate_asset(second.asset, config)),
        )

        plan = plan_fixes(pairs, config, ("Bad Name", "Bad-Name"))
        rename_targets = [
            action.target_name
            for action in plan.actions
            if action.kind is FixKind.RENAME
        ]

        self.assertEqual(rename_targets, ["bad_name", "bad_name_002"])

    def test_fingerprint_changes_when_relevant_state_changes(self) -> None:
        target = FixTargetSnapshot("object-1", fixable_asset())
        changed = replace(
            target,
            asset=replace(target.asset, scale=(2.0, 1.0, 1.0)),
        )

        self.assertNotEqual(
            fingerprint_target(target),
            fingerprint_target(changed),
        )


if __name__ == "__main__":
    unittest.main()
