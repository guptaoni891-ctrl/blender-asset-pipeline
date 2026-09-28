"""Structured, Blender-independent models for batch validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..models import AssetSnapshot, ObjectValidationReport, ValidationConfig


class BatchScope(str, Enum):
    """Object discovery scope for one batch run."""

    CURRENT_SCENE = "CURRENT_SCENE"
    ALL_SCENES = "ALL_SCENES"


class BatchObjectStatus(str, Enum):
    """Stable object-level classification used by summaries and JSON reports."""

    CLEAN = "CLEAN"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class BatchTarget:
    """One collected object snapshot and its scene memberships.

    ``target_key`` is an internal deduplication key. It is deliberately omitted
    from the public JSON schema.
    """

    target_key: str
    asset: AssetSnapshot
    scene_memberships: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.target_key:
            raise ValueError("target_key must not be empty")
        object.__setattr__(
            self,
            "scene_memberships",
            tuple(
                sorted(
                    set(self.scene_memberships),
                    key=lambda name: (name.casefold(), name),
                )
            ),
        )


@dataclass(frozen=True)
class BatchCollection:
    """Objects and scenes collected for a requested batch scope."""

    scope: BatchScope
    scene_names: tuple[str, ...]
    targets: tuple[BatchTarget, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scene_names",
            tuple(
                sorted(
                    set(self.scene_names),
                    key=lambda name: (name.casefold(), name),
                )
            ),
        )


@dataclass(frozen=True)
class BatchObjectResult:
    """Validation output for one unique collected object."""

    asset: AssetSnapshot
    scene_memberships: tuple[str, ...]
    validation: ObjectValidationReport

    @property
    def status(self) -> BatchObjectStatus:
        """Classify this object without treating skipped checks as asset issues."""
        if not self.validation.was_validated:
            return BatchObjectStatus.SKIPPED
        if self.validation.summary.errors:
            return BatchObjectStatus.ERROR
        if self.validation.summary.warnings:
            return BatchObjectStatus.WARNING
        return BatchObjectStatus.CLEAN


@dataclass(frozen=True)
class BatchGeometrySummary:
    """Aggregate geometry metrics for validated mesh objects."""

    total_vertices: int = 0
    total_polygons: int = 0
    total_triangles: int = 0
    largest_object_name: str | None = None
    largest_triangle_count: int = 0
    average_triangle_count: float = 0.0


@dataclass(frozen=True)
class BatchSummary:
    """Aggregate object, check, and geometry counts for a batch run."""

    objects_discovered: int
    objects_validated: int
    objects_skipped: int
    checks_passed: int
    checks_warning: int
    checks_error: int
    clean_objects: int
    warning_objects: int
    error_objects: int
    geometry: BatchGeometrySummary


@dataclass(frozen=True)
class BatchValidationReport:
    """Complete deterministic result of one batch validation run."""

    scope: BatchScope
    scene_names: tuple[str, ...]
    policy: ValidationConfig
    objects: tuple[BatchObjectResult, ...]
    summary: BatchSummary
