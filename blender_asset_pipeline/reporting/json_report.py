"""Intentional schema-v1 JSON serialization for batch validation reports."""

from __future__ import annotations

import json
import math
from typing import Any

from ..batch.models import BatchObjectResult, BatchValidationReport
from ..constants import REPORT_SCHEMA_VERSION
from .models import ReportGenerator, ReportSource


def _finite_number(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _object_to_dict(result: BatchObjectResult) -> dict[str, Any]:
    asset = result.asset
    validation = result.validation
    summary = validation.summary
    geometry = None
    transform = None
    if validation.was_validated:
        geometry = {
            "vertices": asset.vertex_count,
            "edges": asset.edge_count,
            "polygons": asset.polygon_count,
            "triangles": asset.triangle_count,
            "uv_maps": asset.uv_map_count,
        }
        transform = {
            "location": [_finite_number(value) for value in asset.location],
            "rotation": [_finite_number(value) for value in asset.rotation],
            "scale": [_finite_number(value) for value in asset.scale],
        }

    return {
        "name": asset.name,
        "type": asset.object_type,
        "scene_memberships": list(result.scene_memberships),
        "state": "VALIDATED" if validation.was_validated else "SKIPPED",
        "status": result.status.value,
        "summary": {
            "pass": summary.passed,
            "warning": summary.warnings,
            "error": summary.errors,
        },
        "geometry": geometry,
        "transform": transform,
        "checks": [
            {
                "check_id": check.check_id,
                "check_name": check.check_name,
                "severity": check.severity.name,
                "message": check.message,
            }
            for check in validation.results
        ],
    }


def batch_report_to_dict(
    report: BatchValidationReport,
    generator: ReportGenerator,
    source: ReportSource,
    generated_at_utc: str,
) -> dict[str, Any]:
    """Map a batch report to the stable public JSON schema."""
    summary = report.summary
    geometry = summary.geometry
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at_utc": generated_at_utc,
        "generator": {
            "tool_name": generator.tool_name,
            "addon_version": generator.addon_version,
            "blender_version": generator.blender_version,
        },
        "source": {
            "blend_filepath": source.blend_filepath,
            "is_saved": source.is_saved,
        },
        "policy": {
            "max_triangle_count": report.policy.max_triangle_count,
            "naming_convention": report.policy.naming_convention.value,
            "required_prefix": report.policy.required_prefix,
            "transform_tolerance": report.policy.transform_tolerance,
        },
        "scope": {
            "type": report.scope.value,
            "scenes": list(report.scene_names),
        },
        "summary": {
            "objects": {
                "discovered": summary.objects_discovered,
                "validated": summary.objects_validated,
                "skipped": summary.objects_skipped,
                "clean": summary.clean_objects,
                "warnings_only": summary.warning_objects,
                "errors": summary.error_objects,
            },
            "checks": {
                "pass": summary.checks_passed,
                "warning": summary.checks_warning,
                "error": summary.checks_error,
            },
            "geometry": {
                "total_vertices": geometry.total_vertices,
                "total_polygons": geometry.total_polygons,
                "total_triangles": geometry.total_triangles,
                "largest_object_name": geometry.largest_object_name,
                "largest_triangle_count": geometry.largest_triangle_count,
                "average_triangle_count": geometry.average_triangle_count,
            },
        },
        "objects": [_object_to_dict(result) for result in report.objects],
    }


def batch_report_to_json(
    report: BatchValidationReport,
    generator: ReportGenerator,
    source: ReportSource,
    generated_at_utc: str,
) -> str:
    """Serialize a batch report as pretty UTF-8-compatible JSON with a newline."""
    payload = batch_report_to_dict(
        report,
        generator,
        source,
        generated_at_utc,
    )
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ) + "\n"
