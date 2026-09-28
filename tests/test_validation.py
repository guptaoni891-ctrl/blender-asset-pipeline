"""Unit tests for Blender-independent validation behavior."""

from __future__ import annotations

import unittest

import blender_asset_pipeline
from blender_asset_pipeline.constants import ADDON_PACKAGE_ID, ADDON_VERSION
from blender_asset_pipeline.models import (
    AssetSnapshot,
    MaterialSlotSnapshot,
    NamingConvention,
    Severity,
    TextureReference,
    ValidationConfig,
)
from blender_asset_pipeline.validation import format_reports, validate_asset
from blender_asset_pipeline.validation.reporting import summarize_reports


def valid_asset(**overrides: object) -> AssetSnapshot:
    """Build a conforming mesh snapshot with selected fields overridden."""
    values: dict[str, object] = {
        "name": "environment_crate",
        "object_type": "MESH",
        "vertex_count": 24,
        "edge_count": 36,
        "polygon_count": 12,
        "triangle_count": 12,
        "uv_map_count": 1,
        "material_slots": (MaterialSlotSnapshot(0, "crate_material", "material-1"),),
        "texture_references": (
            TextureReference(
                "crate_material",
                "Base Color",
                "crate_albedo",
                "/textures/crate_albedo.png",
                True,
                "available",
            ),
        ),
    }
    values.update(overrides)
    return AssetSnapshot(**values)  # type: ignore[arg-type]


class ValidationTests(unittest.TestCase):
    """Exercise all Milestone 1 validation categories."""

    def test_addon_identifier_uses_package_identity(self) -> None:
        self.assertEqual(ADDON_PACKAGE_ID, blender_asset_pipeline.__name__)

    def test_version_metadata_is_consistent(self) -> None:
        self.assertEqual(ADDON_VERSION, (0, 2, 1))
        self.assertEqual(blender_asset_pipeline.bl_info["version"], ADDON_VERSION)

    def test_conforming_asset_passes_every_check(self) -> None:
        report = validate_asset(valid_asset(), ValidationConfig())

        self.assertTrue(report.was_validated)
        self.assertEqual(report.summary.errors, 0)
        self.assertEqual(report.summary.warnings, 0)
        self.assertGreaterEqual(report.summary.passed, 12)

    def test_non_mesh_is_skipped_with_warning(self) -> None:
        report = validate_asset(AssetSnapshot("key_light", "LIGHT"), ValidationConfig())

        self.assertFalse(report.was_validated)
        self.assertEqual(len(report.results), 1)
        self.assertEqual(report.results[0].severity, Severity.WARNING)
        self.assertIn("only meshes", report.results[0].message)

    def test_transform_tolerance_is_configurable(self) -> None:
        asset = valid_asset(location=(0.005, 0.0, 0.0))

        strict = validate_asset(asset, ValidationConfig(transform_tolerance=0.001))
        lenient = validate_asset(asset, ValidationConfig(transform_tolerance=0.01))

        strict_location = next(
            result for result in strict.results if result.check_id == "location"
        )
        lenient_location = next(
            result for result in lenient.results if result.check_id == "location"
        )
        self.assertEqual(strict_location.severity, Severity.ERROR)
        self.assertEqual(lenient_location.severity, Severity.PASS)

    def test_triangle_budget_is_configurable(self) -> None:
        report = validate_asset(
            valid_asset(triangle_count=501),
            ValidationConfig(max_triangle_count=500),
        )
        result = next(
            result for result in report.results if result.check_id == "triangle_count"
        )

        self.assertEqual(result.severity, Severity.ERROR)
        self.assertIn("501", result.message)
        self.assertIn("500", result.message)

    def test_naming_convention_and_prefix_are_enforced(self) -> None:
        config = ValidationConfig(
            naming_convention=NamingConvention.UPPER_CAMEL_CASE,
            required_prefix="SM_",
        )
        report = validate_asset(valid_asset(name="environment_crate"), config)
        results = {result.check_id: result for result in report.results}

        self.assertEqual(results["naming_convention"].severity, Severity.ERROR)
        self.assertEqual(results["name_prefix"].severity, Severity.ERROR)

    def test_naming_convention_applies_after_prefix(self) -> None:
        config = ValidationConfig(
            naming_convention=NamingConvention.UPPER_CAMEL_CASE,
            required_prefix="SM_",
        )
        report = validate_asset(valid_asset(name="SM_EnvironmentCrate"), config)
        results = {result.check_id: result for result in report.results}

        self.assertEqual(results["naming_convention"].severity, Severity.PASS)
        self.assertEqual(results["name_prefix"].severity, Severity.PASS)

    def test_empty_geometry_uvs_and_materials_are_reported(self) -> None:
        report = validate_asset(
            valid_asset(
                vertex_count=0,
                edge_count=0,
                polygon_count=0,
                triangle_count=0,
                uv_map_count=0,
                material_slots=(),
                texture_references=(),
            ),
            ValidationConfig(),
        )
        results = {result.check_id: result for result in report.results}

        self.assertEqual(results["geometry"].severity, Severity.ERROR)
        self.assertEqual(results["uv_maps"].severity, Severity.ERROR)
        self.assertEqual(results["material_slots"].severity, Severity.WARNING)

    def test_empty_and_duplicate_material_slots_are_reported(self) -> None:
        slots = (
            MaterialSlotSnapshot(0, "body", "material-1"),
            MaterialSlotSnapshot(1, None, None),
            MaterialSlotSnapshot(2, "body", "material-1"),
        )
        report = validate_asset(valid_asset(material_slots=slots), ValidationConfig())
        results = {result.check_id: result for result in report.results}

        self.assertEqual(results["empty_material_slots"].severity, Severity.ERROR)
        self.assertEqual(results["duplicate_materials"].severity, Severity.WARNING)
        self.assertIn("body", results["duplicate_materials"].message)

    def test_missing_texture_is_an_error(self) -> None:
        missing = TextureReference(
            "crate_material",
            "Base Color",
            "crate_albedo",
            "/missing/crate_albedo.png",
            False,
            "file not found",
        )
        report = validate_asset(
            valid_asset(texture_references=(missing,)),
            ValidationConfig(),
        )
        result = next(
            result for result in report.results if result.check_id == "image_textures"
        )

        self.assertEqual(result.severity, Severity.ERROR)
        self.assertIn("crate_material/Base Color", result.message)

    def test_summary_and_console_report_include_all_objects(self) -> None:
        reports = [
            validate_asset(valid_asset(), ValidationConfig()),
            validate_asset(AssetSnapshot("camera", "CAMERA"), ValidationConfig()),
        ]

        summary = summarize_reports(reports)
        text = format_reports(reports)

        self.assertEqual(summary.warnings, 1)
        self.assertIn("2 total, 1 validated, 1 skipped", text)
        self.assertIn("environment_crate [MESH] - VALIDATED", text)
        self.assertIn("camera [CAMERA] - SKIPPED", text)
        self.assertIn("RESULT: WARNING", text)

    def test_invalid_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ValidationConfig(max_triangle_count=-1)
        with self.assertRaises(ValueError):
            ValidationConfig(transform_tolerance=-0.1)


if __name__ == "__main__":
    unittest.main()
