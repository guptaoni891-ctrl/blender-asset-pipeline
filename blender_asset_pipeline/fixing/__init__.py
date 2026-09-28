"""Public API for preview-first asset fixing."""

from .models import (
    FixAction,
    FixCategory,
    FixExecutionReport,
    FixExecutionResult,
    FixExecutionStatus,
    FixKind,
    FixPlan,
    FixRisk,
    FixTargetSnapshot,
)
from .planner import (
    SCALE_NEAR_ZERO_EPSILON,
    collision_safe_name,
    fingerprint_target,
    normalize_object_name,
    plan_fixes,
)

__all__ = [
    "FixAction",
    "FixCategory",
    "FixExecutionReport",
    "FixExecutionResult",
    "FixExecutionStatus",
    "FixKind",
    "FixPlan",
    "FixRisk",
    "FixTargetSnapshot",
    "SCALE_NEAR_ZERO_EPSILON",
    "collision_safe_name",
    "fingerprint_target",
    "normalize_object_name",
    "plan_fixes",
]
