"""Structured, Blender-independent models for fix planning and execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..models import AssetSnapshot


class FixRisk(str, Enum):
    """User-facing risk classification for a proposed fix."""

    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DESTRUCTIVE = "DESTRUCTIVE"


class FixCategory(str, Enum):
    """High-level category used to group fix actions."""

    NAMING = "NAMING"
    TRANSFORM = "TRANSFORM"
    MATERIAL = "MATERIAL"
    MANUAL = "MANUAL"


class FixKind(str, Enum):
    """Machine-readable operation represented by a fix action."""

    RENAME = "RENAME"
    APPLY_LOCATION = "APPLY_LOCATION"
    APPLY_ROTATION = "APPLY_ROTATION"
    APPLY_SCALE = "APPLY_SCALE"
    REMOVE_EMPTY_MATERIAL_SLOTS = "REMOVE_EMPTY_MATERIAL_SLOTS"
    CONSOLIDATE_DUPLICATE_MATERIAL_SLOTS = (
        "CONSOLIDATE_DUPLICATE_MATERIAL_SLOTS"
    )
    MANUAL_NAME = "MANUAL_NAME"
    MANUAL_MATERIAL = "MANUAL_MATERIAL"
    MANUAL_UV = "MANUAL_UV"
    MANUAL_GEOMETRY = "MANUAL_GEOMETRY"
    MANUAL_TRIANGLE_BUDGET = "MANUAL_TRIANGLE_BUDGET"
    MANUAL_TEXTURE = "MANUAL_TEXTURE"
    UNSUPPORTED_OBJECT = "UNSUPPORTED_OBJECT"
    MISSING_OBJECT = "MISSING_OBJECT"


class FixExecutionStatus(str, Enum):
    """Outcome of attempting one selected fix."""

    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    STALE = "STALE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class FixTargetSnapshot:
    """Asset state and Blender capabilities relevant to safe fixes."""

    object_key: str
    asset: AssetSnapshot
    object_is_editable: bool = True
    mesh_is_editable: bool = True
    is_library_linked: bool = False
    is_library_override: bool = False
    mesh_data_users: int = 1
    material_slot_usage: tuple[int, ...] = ()
    material_slots_are_data_linked: bool = True
    has_parent: bool = False
    has_children: bool = False
    has_constraints: bool = False
    has_modifiers: bool = False
    has_animation_data: bool = False
    has_shape_keys: bool = False
    has_delta_transforms: bool = False
    locked_transforms: tuple[str, ...] = ()


@dataclass(frozen=True)
class FixAction:
    """One previewable and individually selectable proposed fix."""

    fix_id: str
    object_key: str
    object_name: str
    category: FixCategory
    kind: FixKind
    title: str
    description: str
    risk: FixRisk
    selected: bool
    default_selected: bool
    supported: bool
    unsupported_reason: str
    expected_fingerprint: str
    target_name: str | None = None


@dataclass(frozen=True)
class FixPlan:
    """A complete preview generated for one or more objects."""

    actions: tuple[FixAction, ...]

    @property
    def object_count(self) -> int:
        """Return the number of unique objects represented by the plan."""
        return len({action.object_key for action in self.actions})


@dataclass(frozen=True)
class FixExecutionResult:
    """Structured execution result for one action."""

    fix_id: str
    object_key: str
    object_name: str
    title: str
    status: FixExecutionStatus
    message: str


@dataclass(frozen=True)
class FixExecutionReport:
    """Results and context warnings from an explicit apply operation."""

    results: tuple[FixExecutionResult, ...]
    context_warnings: tuple[str, ...] = ()

    @property
    def applied_count(self) -> int:
        """Return the number of successfully applied fixes."""
        return sum(
            result.status is FixExecutionStatus.APPLIED for result in self.results
        )

    @property
    def failed_count(self) -> int:
        """Return the number of failed fixes."""
        return sum(
            result.status is FixExecutionStatus.FAILED for result in self.results
        )
