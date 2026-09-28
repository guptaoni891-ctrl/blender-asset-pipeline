"""Pure fix planning, naming, and stale-plan fingerprint logic."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from dataclasses import asdict, replace

from ..models import (
    AssetSnapshot,
    NamingConvention,
    ObjectValidationReport,
    Severity,
    ValidationConfig,
)
from ..validation.engine import validate_asset
from .models import (
    FixAction,
    FixCategory,
    FixKind,
    FixPlan,
    FixRisk,
    FixTargetSnapshot,
)

_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALPHANUMERIC = re.compile(r"[^A-Za-z0-9]+")
_BLENDER_NUMERIC_SUFFIX = re.compile(r"\.\d{3}$")

# Applying scale at or below this magnitude can collapse mesh coordinates. This
# is intentionally independent of the user-facing validation tolerance because
# it is an execution safety boundary rather than a validation policy setting.
SCALE_NEAR_ZERO_EPSILON = 1.0e-6


def _name_words(value: str) -> list[str]:
    without_blender_suffix = _BLENDER_NUMERIC_SUFFIX.sub("", value.strip())
    separated = _WORD_BOUNDARY.sub("_", without_blender_suffix)
    return [word for word in _NON_ALPHANUMERIC.split(separated) if word]


def normalize_object_name(name: str, config: ValidationConfig) -> str:
    """Normalize an object name according to the configured style and prefix."""
    prefix = config.required_prefix.strip()
    body = name[len(prefix) :] if prefix and name.startswith(prefix) else name
    words = _name_words(body)

    if config.naming_convention is NamingConvention.LOWER_SNAKE_CASE:
        normalized_body = "_".join(word.lower() for word in words)
    elif config.naming_convention is NamingConvention.UPPER_CAMEL_CASE:
        normalized_body = "".join(
            word[:1].upper() + word[1:].lower() for word in words
        )
    else:
        normalized_body = body.strip()

    if not normalized_body:
        return ""
    return f"{prefix}{normalized_body}"


def collision_safe_name(
    ideal_name: str,
    existing_names: Iterable[str],
    current_name: str,
    convention: NamingConvention,
) -> str:
    """Return a predictable available name without Blender's dotted suffixes."""
    occupied = set(existing_names)
    occupied.discard(current_name)
    if ideal_name not in occupied:
        return ideal_name

    separator = "" if convention is NamingConvention.UPPER_CAMEL_CASE else "_"
    sequence = 2
    while True:
        candidate = f"{ideal_name}{separator}{sequence:03d}"
        if candidate not in occupied:
            return candidate
        sequence += 1


def fingerprint_target(target: FixTargetSnapshot) -> str:
    """Create a stable digest of all state relevant to the current fix plan."""
    payload = json.dumps(
        asdict(target),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _action(
    target: FixTargetSnapshot,
    kind: FixKind,
    category: FixCategory,
    title: str,
    description: str,
    risk: FixRisk,
    supported: bool,
    reason: str = "",
    target_name: str | None = None,
) -> FixAction:
    default_selected = supported and risk is FixRisk.SAFE
    return FixAction(
        fix_id=f"{target.object_key}:{kind.value}",
        object_key=target.object_key,
        object_name=target.asset.name,
        category=category,
        kind=kind,
        title=title,
        description=description,
        risk=risk,
        selected=default_selected,
        default_selected=default_selected,
        supported=supported,
        unsupported_reason=reason,
        expected_fingerprint=fingerprint_target(target),
        target_name=target_name,
    )


def _base_mutation_blocker(target: FixTargetSnapshot) -> str:
    if target.is_library_linked:
        return "Linked library data cannot be modified safely."
    if target.is_library_override:
        return "Library overrides require manual review."
    if not target.object_is_editable:
        return "The object is not editable in the current Blender context."
    return ""


def _mesh_mutation_blocker(target: FixTargetSnapshot) -> str:
    blocker = _base_mutation_blocker(target)
    if blocker:
        return blocker
    if not target.mesh_is_editable:
        return "The mesh datablock is not editable."
    if target.mesh_data_users > 1:
        return "The mesh datablock is shared by multiple objects."
    return ""


def _transform_blocker(target: FixTargetSnapshot, transform: str) -> str:
    blocker = _mesh_mutation_blocker(target)
    if blocker:
        return blocker
    if transform in target.locked_transforms:
        return f"The object's {transform.lower()} channels are locked."
    if target.has_parent or target.has_children:
        return "Parented object hierarchies require manual transform review."
    if target.has_constraints:
        return "Constrained objects require manual transform review."
    if target.has_modifiers:
        return "Modifier-dependent transforms require manual review."
    if target.has_animation_data:
        return "Animated transforms cannot be applied automatically."
    if target.has_shape_keys:
        return "Meshes with shape keys require manual transform review."
    if target.has_delta_transforms:
        return "Delta transforms require manual review."
    return ""


def _combined_blocker(*reasons: str) -> str:
    return " ".join(reason for reason in reasons if reason)


def _non_finite_transform_blocker(
    transform_name: str,
    values: tuple[float, float, float],
) -> str:
    if all(math.isfinite(value) for value in values):
        return ""
    return (
        f"The object's {transform_name.lower()} contains non-finite values and "
        "cannot be applied automatically."
    )


def _material_blocker(target: FixTargetSnapshot) -> str:
    blocker = _mesh_mutation_blocker(target)
    if blocker:
        return blocker
    if not target.material_slots_are_data_linked:
        return "Object-linked material slots require manual cleanup."
    return ""


def _result_map(report: ObjectValidationReport) -> dict[str, Severity]:
    return {result.check_id: result.severity for result in report.results}


def _plan_name(
    target: FixTargetSnapshot,
    results: dict[str, Severity],
    config: ValidationConfig,
    reserved_names: set[str],
) -> FixAction | None:
    needs_name_fix = any(
        results.get(check_id, Severity.PASS) is not Severity.PASS
        for check_id in ("object_name", "naming_convention", "name_prefix")
    )
    if not needs_name_fix:
        return None

    ideal_name = normalize_object_name(target.asset.name, config)
    proposed_name = (
        collision_safe_name(
            ideal_name,
            reserved_names,
            target.asset.name,
            config.naming_convention,
        )
        if ideal_name
        else ""
    )
    blocker = _base_mutation_blocker(target)
    if proposed_name:
        proposed_report = validate_asset(
            replace(target.asset, name=proposed_name),
            config,
        )
        proposed_results = _result_map(proposed_report)
        if any(
            proposed_results.get(check_id, Severity.PASS) is not Severity.PASS
            for check_id in ("object_name", "naming_convention", "name_prefix")
        ):
            proposed_name = ""
    if not proposed_name or proposed_name == target.asset.name:
        blocker = blocker or (
            "Automatic normalization cannot choose a descriptive replacement name."
        )
        return _action(
            target,
            FixKind.MANUAL_NAME,
            FixCategory.NAMING,
            "Choose Descriptive Name",
            "Rename the object to a descriptive pipeline-compatible name.",
            FixRisk.CAUTION,
            False,
            blocker,
        )

    supported = not blocker
    if supported:
        reserved_names.add(proposed_name)
    return _action(
        target,
        FixKind.RENAME,
        FixCategory.NAMING,
        f"Rename to {proposed_name}",
        "Normalize the name using the current naming convention and prefix.",
        FixRisk.SAFE,
        supported,
        blocker,
        proposed_name,
    )


def _plan_transforms(
    target: FixTargetSnapshot,
    results: dict[str, Severity],
) -> list[FixAction]:
    specifications = (
        (
            "location",
            FixKind.APPLY_LOCATION,
            "Apply Location",
            FixRisk.CAUTION,
            (
                "Bake the current location into mesh coordinates while preserving "
                "appearance."
            ),
        ),
        (
            "rotation",
            FixKind.APPLY_ROTATION,
            "Apply Rotation",
            FixRisk.CAUTION,
            "Bake the current rotation into the mesh while preserving appearance.",
        ),
    )
    actions = []
    for check_id, kind, title, risk, description in specifications:
        if results.get(check_id) is not Severity.ERROR:
            continue
        values = getattr(target.asset, check_id)
        blocker = _combined_blocker(
            _transform_blocker(target, check_id.upper()),
            _non_finite_transform_blocker(check_id, values),
        )
        actions.append(
            _action(
                target,
                kind,
                FixCategory.TRANSFORM,
                title,
                description,
                risk,
                not blocker,
                blocker,
            )
        )

    if results.get("scale") is Severity.ERROR:
        scale = target.asset.scale
        blocker = _transform_blocker(target, "SCALE")
        non_finite_blocker = _non_finite_transform_blocker("scale", scale)

        if non_finite_blocker:
            description = (
                "Scale contains non-finite values and cannot be safely baked into "
                "mesh data."
            )
            risk = FixRisk.CAUTION
            blocker = _combined_blocker(blocker, non_finite_blocker)
        elif any(abs(component) <= SCALE_NEAR_ZERO_EPSILON for component in scale):
            description = (
                "Applying a zero or near-zero scale could bake degenerate or "
                "collapsed geometry into the mesh."
            )
            risk = FixRisk.CAUTION
            blocker = _combined_blocker(
                blocker,
                "Zero or near-zero scale cannot be applied automatically because "
                "it could bake degenerate or collapsed geometry into the mesh.",
            )
        elif any(component < 0.0 for component in scale):
            description = (
                "This mirrored/negative scale requires review because applying it "
                "bakes the mirrored transform into mesh data."
            )
            risk = FixRisk.CAUTION
        else:
            description = (
                "Bake the current positive scale into the mesh while preserving "
                "appearance."
            )
            risk = FixRisk.SAFE

        actions.append(
            _action(
                target,
                FixKind.APPLY_SCALE,
                FixCategory.TRANSFORM,
                "Apply Scale",
                description,
                risk,
                not blocker,
                blocker,
            )
        )
    return actions


def _plan_materials(
    target: FixTargetSnapshot,
    results: dict[str, Severity],
) -> list[FixAction]:
    actions = []
    if results.get("empty_material_slots") is Severity.ERROR:
        blocker = _material_blocker(target)
        empty_indices = {
            slot.slot_index
            for slot in target.asset.material_slots
            if slot.material_id is None
        }
        used_empty = sorted(
            index + 1
            for index in empty_indices
            if index < len(target.material_slot_usage)
            and target.material_slot_usage[index] > 0
        )
        if used_empty:
            blocker = (
                "Empty slot(s) "
                + ", ".join(str(index) for index in used_empty)
                + " are assigned to faces and need a user-chosen replacement material."
            )
        actions.append(
            _action(
                target,
                FixKind.REMOVE_EMPTY_MATERIAL_SLOTS,
                FixCategory.MATERIAL,
                "Remove Empty Material Slots",
                "Remove unused empty slots and remap later polygon material indices.",
                FixRisk.CAUTION,
                not blocker,
                blocker,
            )
        )

    if results.get("duplicate_materials") is Severity.WARNING:
        blocker = _material_blocker(target)
        actions.append(
            _action(
                target,
                FixKind.CONSOLIDATE_DUPLICATE_MATERIAL_SLOTS,
                FixCategory.MATERIAL,
                "Consolidate Duplicate Material Slots",
                "Keep the first exact material datablock and remap polygons to it.",
                FixRisk.CAUTION,
                not blocker,
                blocker,
            )
        )

    if results.get("material_slots") is Severity.WARNING:
        actions.append(
            _action(
                target,
                FixKind.MANUAL_MATERIAL,
                FixCategory.MANUAL,
                "Assign a Material",
                "Choose and assign an appropriate game-ready material.",
                FixRisk.CAUTION,
                False,
                "Selecting or creating a material requires user intent.",
            )
        )
    return actions


def _plan_manual_checks(
    target: FixTargetSnapshot,
    results: dict[str, Severity],
) -> list[FixAction]:
    specifications = (
        (
            "uv_maps",
            FixKind.MANUAL_UV,
            "Create UV Map",
            "UV generation requires intentional seams and projection choices.",
        ),
        (
            "geometry",
            FixKind.MANUAL_GEOMETRY,
            "Create Mesh Geometry",
            "Empty geometry cannot be repaired without authoring the asset.",
        ),
        (
            "triangle_count",
            FixKind.MANUAL_TRIANGLE_BUDGET,
            "Reduce Triangle Count",
            "Mesh optimization and decimation are deferred to a later milestone.",
        ),
        (
            "image_textures",
            FixKind.MANUAL_TEXTURE,
            "Resolve Missing Image Textures",
            "A user-provided image or corrected texture path is required.",
        ),
    )
    actions = []
    for check_id, kind, title, reason in specifications:
        if results.get(check_id) is not Severity.ERROR:
            continue
        actions.append(
            _action(
                target,
                kind,
                FixCategory.MANUAL,
                title,
                reason,
                FixRisk.CAUTION,
                False,
                reason,
            )
        )
    return actions


def plan_fixes(
    targets_and_reports: Iterable[
        tuple[FixTargetSnapshot, ObjectValidationReport]
    ],
    config: ValidationConfig,
    existing_names: Iterable[str],
) -> FixPlan:
    """Convert fresh validation reports and target snapshots into a fix plan."""
    reserved_names = set(existing_names)
    actions: list[FixAction] = []
    for target, report in targets_and_reports:
        if not report.was_validated:
            actions.append(
                _action(
                    target,
                    FixKind.UNSUPPORTED_OBJECT,
                    FixCategory.MANUAL,
                    "Unsupported Object Type",
                    "Only mesh objects can be fixed by this milestone.",
                    FixRisk.CAUTION,
                    False,
                    f"Object type '{target.asset.object_type}' is unsupported.",
                )
            )
            continue

        results = _result_map(report)
        name_action = _plan_name(target, results, config, reserved_names)
        if name_action is not None:
            actions.append(name_action)
        actions.extend(_plan_transforms(target, results))
        actions.extend(_plan_materials(target, results))
        actions.extend(_plan_manual_checks(target, results))
    return FixPlan(tuple(actions))


def missing_object_action(object_key: str, object_name: str) -> FixAction:
    """Create an unsupported plan row for an object deleted after validation."""
    placeholder = FixTargetSnapshot(
        object_key=object_key,
        asset=AssetSnapshot(object_name, "MISSING"),
    )
    return _action(
        placeholder,
        FixKind.MISSING_OBJECT,
        FixCategory.MANUAL,
        "Object No Longer Exists",
        "The validated object was deleted before the fix plan was generated.",
        FixRisk.CAUTION,
        False,
        "Revalidate the current scene selection.",
    )
