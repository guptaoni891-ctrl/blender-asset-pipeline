"""Unit tests for Blender-independent batch validation aggregation."""

from __future__ import annotations

import unittest

from blender_asset_pipeline.batch import (
    BatchCollection,
    BatchObjectStatus,
    BatchScope,
    BatchTarget,
    validate_batch,
)
from blender_asset_pipeline.models import (
    AssetSnapshot,
    MaterialSlotSnapshot,
    ValidationConfig,
)


def clean_asset(name: str, **overrides: object) -> AssetSnapshot:
    """Create a mesh snapshot that passes the default validation policy."""
    values: dict[str, object] = {
        "name": name,
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


def collection(*targets: BatchTarget) -> BatchCollection:
    """Build a current-scene test collection."""
    return BatchCollection(BatchScope.CURRENT_SCENE, ("Main",), targets)


class BatchValidationTests(unittest.TestCase):
    """Exercise batch deduplication, classification, and summary metrics."""

    def test_zero_object_batch_has_zero_safe_averages(self) -> None:
        report = validate_batch(collection(), ValidationConfig())

        self.assertEqual(report.summary.objects_discovered, 0)
        self.assertEqual(report.summary.objects_validated, 0)
        self.assertEqual(report.summary.geometry.average_triangle_count, 0.0)
        self.assertIsNone(report.summary.geometry.largest_object_name)

    def test_unsupported_only_batch_is_counted_as_skipped(self) -> None:
        target = BatchTarget(
            "light-key",
            AssetSnapshot("key_light", "LIGHT"),
            ("Main",),
        )
        report = validate_batch(collection(target), ValidationConfig())

        self.assertEqual(report.summary.objects_discovered, 1)
        self.assertEqual(report.summary.objects_validated, 0)
        self.assertEqual(report.summary.objects_skipped, 1)
        self.assertEqual(report.objects[0].status, BatchObjectStatus.SKIPPED)
        self.assertEqual(report.summary.warning_objects, 0)

    def test_mixed_object_statuses_are_classified(self) -> None:
        targets = (
            BatchTarget("clean", clean_asset("clean_asset"), ("Main",)),
            BatchTarget(
                "warning",
                clean_asset("warning_asset", material_slots=()),
                ("Main",),
            ),
            BatchTarget(
                "error",
                clean_asset("Bad Asset", scale=(2.0, 1.0, 1.0)),
                ("Main",),
            ),
        )
        report = validate_batch(collection(*targets), ValidationConfig())
        statuses = {result.asset.name: result.status for result in report.objects}

        self.assertEqual(statuses["clean_asset"], BatchObjectStatus.CLEAN)
        self.assertEqual(statuses["warning_asset"], BatchObjectStatus.WARNING)
        self.assertEqual(statuses["Bad Asset"], BatchObjectStatus.ERROR)
        self.assertEqual(report.summary.clean_objects, 1)
        self.assertEqual(report.summary.warning_objects, 1)
        self.assertEqual(report.summary.error_objects, 1)
        self.assertGreater(report.summary.checks_passed, 0)
        self.assertGreater(report.summary.checks_warning, 0)
        self.assertGreater(report.summary.checks_error, 0)

    def test_geometry_statistics_cover_validated_meshes_only(self) -> None:
        targets = (
            BatchTarget(
                "small",
                clean_asset(
                    "small_asset",
                    vertex_count=4,
                    polygon_count=2,
                    triangle_count=3,
                ),
                ("Main",),
            ),
            BatchTarget(
                "large",
                clean_asset(
                    "large_asset",
                    vertex_count=20,
                    polygon_count=10,
                    triangle_count=21,
                ),
                ("Main",),
            ),
            BatchTarget("camera", AssetSnapshot("camera", "CAMERA"), ("Main",)),
        )
        geometry = validate_batch(
            collection(*targets), ValidationConfig()
        ).summary.geometry

        self.assertEqual(geometry.total_vertices, 24)
        self.assertEqual(geometry.total_polygons, 12)
        self.assertEqual(geometry.total_triangles, 24)
        self.assertEqual(geometry.largest_object_name, "large_asset")
        self.assertEqual(geometry.largest_triangle_count, 21)
        self.assertEqual(geometry.average_triangle_count, 12.0)

    def test_duplicate_is_validated_once_with_merged_memberships(self) -> None:
        asset = clean_asset("shared_asset")
        batch = BatchCollection(
            BatchScope.ALL_SCENES,
            ("Second", "Main"),
            (
                BatchTarget("same-object", asset, ("Main",)),
                BatchTarget("same-object", asset, ("Second",)),
            ),
        )
        report = validate_batch(batch, ValidationConfig())

        self.assertEqual(report.summary.objects_discovered, 1)
        self.assertEqual(len(report.objects), 1)
        self.assertEqual(report.objects[0].scene_memberships, ("Main", "Second"))
        self.assertEqual(report.scene_names, ("Main", "Second"))

    def test_conflicting_duplicate_snapshots_are_rejected(self) -> None:
        batch = BatchCollection(
            BatchScope.ALL_SCENES,
            ("Main",),
            (
                BatchTarget("same", clean_asset("first_asset"), ("Main",)),
                BatchTarget("same", clean_asset("second_asset"), ("Main",)),
            ),
        )

        with self.assertRaises(ValueError):
            validate_batch(batch, ValidationConfig())

    def test_result_order_is_deterministic(self) -> None:
        first = BatchTarget("z", clean_asset("zebra_asset"), ("Main",))
        second = BatchTarget("a", clean_asset("alpha_asset"), ("Main",))

        forward = validate_batch(collection(first, second), ValidationConfig())
        reversed_report = validate_batch(
            collection(second, first), ValidationConfig()
        )

        expected = ["alpha_asset", "zebra_asset"]
        self.assertEqual([item.asset.name for item in forward.objects], expected)
        self.assertEqual(
            [item.asset.name for item in reversed_report.objects],
            expected,
        )


if __name__ == "__main__":
    unittest.main()
