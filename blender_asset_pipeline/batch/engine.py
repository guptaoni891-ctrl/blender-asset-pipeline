"""Pure batch validation aggregation built on the individual validator."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import AssetSnapshot, ValidationConfig
from ..validation import validate_asset
from ..validation.reporting import summarize_reports
from .models import (
    BatchCollection,
    BatchGeometrySummary,
    BatchObjectResult,
    BatchObjectStatus,
    BatchSummary,
    BatchTarget,
    BatchValidationReport,
)


def _object_sort_key(result: BatchObjectResult) -> tuple[object, ...]:
    asset = result.asset
    return (
        asset.name.casefold(),
        asset.name,
        asset.object_type,
        result.scene_memberships,
        asset.vertex_count,
        asset.polygon_count,
        asset.triangle_count,
        tuple(repr(value) for value in asset.location),
        tuple(repr(value) for value in asset.rotation),
        tuple(repr(value) for value in asset.scale),
        tuple(
            (
                check.check_id,
                check.check_name,
                check.severity.name,
                check.message,
            )
            for check in result.validation.results
        ),
    )


def _deduplicate_targets(targets: Iterable[BatchTarget]) -> tuple[BatchTarget, ...]:
    assets_by_key: dict[str, AssetSnapshot] = {}
    scenes_by_key: dict[str, set[str]] = {}
    for target in targets:
        previous_asset = assets_by_key.setdefault(target.target_key, target.asset)
        if previous_asset != target.asset:
            raise ValueError(
                f"Conflicting snapshots supplied for target '{target.target_key}'"
            )
        scenes_by_key.setdefault(target.target_key, set()).update(
            target.scene_memberships
        )

    return tuple(
        BatchTarget(key, asset, tuple(scenes_by_key[key]))
        for key, asset in assets_by_key.items()
    )


def _geometry_summary(
    objects: tuple[BatchObjectResult, ...],
) -> BatchGeometrySummary:
    validated = tuple(result for result in objects if result.validation.was_validated)
    if not validated:
        return BatchGeometrySummary()

    total_triangles = sum(result.asset.triangle_count for result in validated)
    maximum = max(result.asset.triangle_count for result in validated)
    largest = min(
        (result for result in validated if result.asset.triangle_count == maximum),
        key=_object_sort_key,
    )
    return BatchGeometrySummary(
        total_vertices=sum(result.asset.vertex_count for result in validated),
        total_polygons=sum(result.asset.polygon_count for result in validated),
        total_triangles=total_triangles,
        largest_object_name=largest.asset.name,
        largest_triangle_count=maximum,
        average_triangle_count=total_triangles / len(validated),
    )


def validate_batch(
    collection: BatchCollection,
    config: ValidationConfig,
) -> BatchValidationReport:
    """Validate every unique target once and calculate aggregate statistics."""
    targets = _deduplicate_targets(collection.targets)
    objects = tuple(
        sorted(
            (
                BatchObjectResult(
                    asset=target.asset,
                    scene_memberships=target.scene_memberships,
                    validation=validate_asset(target.asset, config),
                )
                for target in targets
            ),
            key=_object_sort_key,
        )
    )
    validation_summary = summarize_reports(
        [result.validation for result in objects]
    )
    status_counts = {
        status: sum(result.status is status for result in objects)
        for status in BatchObjectStatus
    }
    validated_count = len(objects) - status_counts[BatchObjectStatus.SKIPPED]
    summary = BatchSummary(
        objects_discovered=len(objects),
        objects_validated=validated_count,
        objects_skipped=status_counts[BatchObjectStatus.SKIPPED],
        checks_passed=validation_summary.passed,
        checks_warning=validation_summary.warnings,
        checks_error=validation_summary.errors,
        clean_objects=status_counts[BatchObjectStatus.CLEAN],
        warning_objects=status_counts[BatchObjectStatus.WARNING],
        error_objects=status_counts[BatchObjectStatus.ERROR],
        geometry=_geometry_summary(objects),
    )
    return BatchValidationReport(
        scope=collection.scope,
        scene_names=collection.scene_names,
        policy=config,
        objects=objects,
        summary=summary,
    )
