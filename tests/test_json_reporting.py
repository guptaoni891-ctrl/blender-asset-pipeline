"""Tests for stable JSON serialization and atomic report writing."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from blender_asset_pipeline.batch import (
    BatchCollection,
    BatchScope,
    BatchTarget,
    BatchValidationReport,
    validate_batch,
)
from blender_asset_pipeline.constants import REPORT_SCHEMA_VERSION
from blender_asset_pipeline.models import (
    AssetSnapshot,
    MaterialSlotSnapshot,
    ValidationConfig,
)
from blender_asset_pipeline.reporting import (
    LatestBatchRun,
    ReportGenerator,
    ReportSource,
    batch_report_to_dict,
    batch_report_to_json,
    ensure_json_extension,
    write_json_report,
)
from blender_asset_pipeline.reporting.runtime import (
    clear_latest_batch_run,
    get_latest_batch_run,
    set_latest_batch_run,
)

FIXED_TIMESTAMP = "2026-09-28T12:00:00Z"


def report_asset(name: str = "café_crate") -> AssetSnapshot:
    """Return a mesh snapshot containing useful serialization characters."""
    return AssetSnapshot(
        name=name,
        object_type="MESH",
        vertex_count=8,
        edge_count=12,
        polygon_count=6,
        triangle_count=12,
        uv_map_count=1,
        material_slots=(
            MaterialSlotSnapshot(0, 'body "quoted" \\ material', "pointer-like-123"),
        ),
    )


def build_report(name: str = "café_crate") -> BatchValidationReport:
    """Create a deterministic one-object batch report."""
    collection = BatchCollection(
        BatchScope.ALL_SCENES,
        ("Scene Ω", "Main"),
        (
            BatchTarget(
                "0xDEADBEEF-internal-key",
                report_asset(name),
                ("Scene Ω", "Main"),
            ),
        ),
    )
    return validate_batch(collection, ValidationConfig(max_triangle_count=500))


GENERATOR = ReportGenerator(
    "Blender Asset Pipeline",
    "0.3.0",
    "5.2.2 LTS",
)


class JsonSerializationTests(unittest.TestCase):
    """Treat the versioned JSON structure as an intentional public API."""

    def test_schema_and_top_level_structure_are_explicit(self) -> None:
        payload = batch_report_to_dict(
            build_report(),
            GENERATOR,
            ReportSource(None, False),
            FIXED_TIMESTAMP,
        )

        self.assertEqual(REPORT_SCHEMA_VERSION, "1.0")
        self.assertEqual(
            list(payload),
            [
                "schema_version",
                "generated_at_utc",
                "generator",
                "source",
                "policy",
                "scope",
                "summary",
                "objects",
            ],
        )
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["scope"]["type"], "ALL_SCENES")
        self.assertEqual(payload["scope"]["scenes"], ["Main", "Scene Ω"])

    def test_object_schema_has_stable_severity_and_memberships(self) -> None:
        payload = batch_report_to_dict(
            build_report(),
            GENERATOR,
            ReportSource("C:/assets/source.blend", True),
            FIXED_TIMESTAMP,
        )
        object_data = payload["objects"][0]

        self.assertEqual(
            list(object_data),
            [
                "name",
                "type",
                "scene_memberships",
                "state",
                "status",
                "summary",
                "geometry",
                "transform",
                "checks",
            ],
        )
        self.assertEqual(object_data["scene_memberships"], ["Main", "Scene Ω"])
        self.assertTrue(
            {check["severity"] for check in object_data["checks"]}
            <= {"PASS", "WARNING", "ERROR"}
        )
        self.assertEqual(
            [check["check_id"] for check in object_data["checks"]],
            [
                "object_name",
                "naming_convention",
                "location",
                "rotation",
                "scale",
                "geometry",
                "polygon_count",
                "triangle_count",
                "material_slots",
                "empty_material_slots",
                "duplicate_materials",
                "uv_maps",
                "image_textures",
            ],
        )

    def test_json_round_trip_preserves_unicode_and_special_characters(self) -> None:
        name = 'café_箱_"quoted"_\\asset'
        text = batch_report_to_json(
            build_report(name),
            GENERATOR,
            ReportSource(None, False),
            FIXED_TIMESTAMP,
        )
        parsed = json.loads(text)

        self.assertTrue(text.endswith("\n"))
        self.assertIn("café_箱", text)
        self.assertEqual(parsed["objects"][0]["name"], name)
        self.assertFalse(parsed["source"]["is_saved"])
        self.assertIsNone(parsed["source"]["blend_filepath"])

    def test_internal_deduplication_key_is_not_public(self) -> None:
        text = batch_report_to_json(
            build_report(),
            GENERATOR,
            ReportSource(None, False),
            FIXED_TIMESTAMP,
        )

        self.assertNotIn("0xDEADBEEF", text)
        self.assertNotIn("target_key", text)
        self.assertNotIn("pointer-like-123", text)

    def test_serialization_is_deterministic_for_fixed_metadata(self) -> None:
        report = build_report()
        arguments = (
            report,
            GENERATOR,
            ReportSource(None, False),
            FIXED_TIMESTAMP,
        )

        self.assertEqual(
            batch_report_to_json(*arguments),
            batch_report_to_json(*arguments),
        )

        first = batch_report_to_dict(*arguments)
        second = batch_report_to_dict(
            report,
            GENERATOR,
            ReportSource(None, False),
            "2026-09-29T12:00:00Z",
        )
        first.pop("generated_at_utc")
        second.pop("generated_at_utc")
        self.assertEqual(first, second)

    def test_non_finite_transform_components_serialize_as_null(self) -> None:
        asset = replace(
            report_asset("finite_guard"),
            scale=(float("inf"), 1.0, 1.0),
        )
        report = validate_batch(
            BatchCollection(
                BatchScope.CURRENT_SCENE,
                ("Main",),
                (BatchTarget("key", asset, ("Main",)),),
            ),
            ValidationConfig(),
        )
        text = batch_report_to_json(
            report,
            GENERATOR,
            ReportSource(None, False),
            FIXED_TIMESTAMP,
        )

        self.assertIsNone(json.loads(text)["objects"][0]["transform"]["scale"][0])
        self.assertNotIn("Infinity", text)


class JsonWriterTests(unittest.TestCase):
    """Exercise extension handling, UTF-8 output, and atomic failure behavior."""

    def test_extension_handling(self) -> None:
        self.assertEqual(ensure_json_extension("report"), Path("report.json"))
        self.assertEqual(ensure_json_extension("report.JSON"), Path("report.JSON"))
        self.assertEqual(
            ensure_json_extension("report.txt"),
            Path("report.txt.json"),
        )

    def test_writer_outputs_utf8_with_final_newline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = write_json_report(
                Path(directory) / "résultat",
                '{"name": "café"}',
            )

            self.assertEqual(destination.suffix, ".json")
            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                '{"name": "café"}\n',
            )

    def test_replace_failure_preserves_existing_report_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "report.json"
            destination.write_text("old report\n", encoding="utf-8")

            with patch(
                "blender_asset_pipeline.reporting.writer.os.replace",
                side_effect=PermissionError("denied"),
            ):
                with self.assertRaises(PermissionError):
                    write_json_report(destination, "new report")

            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "old report\n",
            )
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])


class RuntimeCacheTests(unittest.TestCase):
    """Ensure an export can only resolve the report matching displayed state."""

    def tearDown(self) -> None:
        clear_latest_batch_run()

    def test_cache_requires_matching_run_id_and_can_be_cleared(self) -> None:
        run = LatestBatchRun(
            run_id="run-1",
            report=build_report(),
            generator=GENERATOR,
            source=ReportSource(None, False),
            generated_at_utc=FIXED_TIMESTAMP,
        )

        set_latest_batch_run(run)
        self.assertIs(get_latest_batch_run("run-1"), run)
        self.assertIsNone(get_latest_batch_run("stale-run"))
        clear_latest_batch_run()
        self.assertIsNone(get_latest_batch_run("run-1"))


if __name__ == "__main__":
    unittest.main()
