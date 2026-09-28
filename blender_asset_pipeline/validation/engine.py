"""Game-ready asset validation rules."""

from __future__ import annotations

import re
from collections import Counter

from ..models import (
    AssetSnapshot,
    CheckResult,
    NamingConvention,
    ObjectValidationReport,
    Severity,
    ValidationConfig,
)

_NAME_PATTERNS = {
    NamingConvention.LOWER_SNAKE_CASE: re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"),
    NamingConvention.UPPER_CAMEL_CASE: re.compile(r"^[A-Z][A-Za-z0-9]*$"),
}
_GENERIC_NAMES = {
    "cone",
    "cube",
    "cylinder",
    "mesh",
    "object",
    "plane",
    "sphere",
    "suzanne",
}


def _result(check_id: str, name: str, severity: Severity, message: str) -> CheckResult:
    return CheckResult(check_id, name, severity, message)


def _vector_near(
    actual: tuple[float, float, float],
    expected: tuple[float, float, float],
    tolerance: float,
) -> bool:
    return all(
        abs(value - target) <= tolerance
        for value, target in zip(actual, expected, strict=True)
    )


def _format_vector(value: tuple[float, float, float]) -> str:
    return f"({value[0]:.6g}, {value[1]:.6g}, {value[2]:.6g})"


def _name_results(asset: AssetSnapshot, config: ValidationConfig) -> list[CheckResult]:
    results: list[CheckResult] = []
    stripped_name = asset.name.strip()
    prefix = config.required_prefix.strip()
    has_prefix = bool(prefix) and asset.name.startswith(prefix)
    convention_candidate = asset.name[len(prefix) :] if has_prefix else asset.name
    if not stripped_name:
        results.append(
            _result(
                "object_name",
                "Object Name",
                Severity.ERROR,
                "Object name is empty.",
            )
        )
    elif any(character.isspace() for character in asset.name):
        results.append(
            _result(
                "object_name",
                "Object Name",
                Severity.WARNING,
                (
                    f"'{asset.name}' contains whitespace, which is fragile in "
                    "asset pipelines."
                ),
            )
        )
    elif re.sub(r"\.\d{3}$", "", stripped_name).lower() in _GENERIC_NAMES:
        results.append(
            _result(
                "object_name",
                "Object Name",
                Severity.WARNING,
                (
                    f"'{asset.name}' looks like a generic/default name; use a "
                    "descriptive asset name."
                ),
            )
        )
    else:
        results.append(
            _result(
                "object_name",
                "Object Name",
                Severity.PASS,
                f"'{asset.name}' is non-empty and descriptive.",
            )
        )

    if config.naming_convention is NamingConvention.ANY:
        convention_matches = bool(convention_candidate.strip())
        convention_description = "a non-empty name"
    else:
        convention_matches = bool(
            _NAME_PATTERNS[config.naming_convention].fullmatch(convention_candidate)
        )
        convention_description = {
            NamingConvention.LOWER_SNAKE_CASE: "lower_snake_case",
            NamingConvention.UPPER_CAMEL_CASE: "UpperCamelCase",
        }[config.naming_convention]

    results.append(
        _result(
            "naming_convention",
            "Naming Convention",
            Severity.PASS if convention_matches else Severity.ERROR,
            (
                f"'{convention_candidate}' matches {convention_description}."
                if convention_matches
                else (
                    f"The name portion '{convention_candidate}' must use "
                    f"{convention_description}."
                )
            ),
        )
    )

    if prefix:
        results.append(
            _result(
                "name_prefix",
                "Name Prefix",
                Severity.PASS if has_prefix else Severity.ERROR,
                (
                    f"Object name starts with required prefix '{prefix}'."
                    if has_prefix
                    else f"Object name must start with required prefix '{prefix}'."
                ),
            )
        )
    return results


def _transform_results(asset: AssetSnapshot, tolerance: float) -> list[CheckResult]:
    checks = (
        ("location", "Location", asset.location, (0.0, 0.0, 0.0)),
        ("rotation", "Rotation", asset.rotation, (0.0, 0.0, 0.0)),
        ("scale", "Scale", asset.scale, (1.0, 1.0, 1.0)),
    )
    results = []
    for check_id, name, actual, expected in checks:
        applied = _vector_near(actual, expected, tolerance)
        results.append(
            _result(
                check_id,
                name,
                Severity.PASS if applied else Severity.ERROR,
                (
                    f"{name} is applied ({_format_vector(actual)})."
                    if applied
                    else (
                        f"{name} is not applied: {_format_vector(actual)}; expected "
                        f"{_format_vector(expected)} within {tolerance:g}."
                    )
                ),
            )
        )
    return results


def _geometry_results(asset: AssetSnapshot, max_triangles: int) -> list[CheckResult]:
    has_geometry = asset.vertex_count > 0 and asset.polygon_count > 0
    results = [
        _result(
            "geometry",
            "Mesh Geometry",
            Severity.PASS if has_geometry else Severity.ERROR,
            (
                (
                    f"Mesh has {asset.vertex_count:,} vertices and "
                    f"{asset.polygon_count:,} polygons."
                )
                if has_geometry
                else (
                    "Mesh has no renderable geometry "
                    f"({asset.vertex_count:,} vertices, {asset.edge_count:,} edges, "
                    f"{asset.polygon_count:,} polygons)."
                )
            ),
        ),
        _result(
            "polygon_count",
            "Polygon Count",
            Severity.PASS,
            f"Polygon count: {asset.polygon_count:,}.",
        ),
    ]
    within_budget = asset.triangle_count <= max_triangles
    results.append(
        _result(
            "triangle_count",
            "Triangle Count",
            Severity.PASS if within_budget else Severity.ERROR,
            (
                f"Triangle count: {asset.triangle_count:,} (budget: {max_triangles:,})."
                if within_budget
                else (
                    f"Triangle count {asset.triangle_count:,} exceeds the "
                    f"{max_triangles:,} triangle budget."
                )
            ),
        )
    )
    return results


def _material_results(asset: AssetSnapshot) -> list[CheckResult]:
    if not asset.material_slots:
        slots_result = _result(
            "material_slots",
            "Material Slots",
            Severity.WARNING,
            "Mesh has no material slots.",
        )
    else:
        slots_result = _result(
            "material_slots",
            "Material Slots",
            Severity.PASS,
            f"Mesh has {len(asset.material_slots)} material slot(s).",
        )

    empty_slots = [
        str(slot.slot_index + 1)
        for slot in asset.material_slots
        if slot.material_id is None
    ]
    empty_result = _result(
        "empty_material_slots",
        "Empty Material Slots",
        Severity.ERROR if empty_slots else Severity.PASS,
        (
            f"Material slot(s) {', '.join(empty_slots)} are empty."
            if empty_slots
            else "No empty material slots found."
        ),
    )

    assigned_ids = [
        slot.material_id
        for slot in asset.material_slots
        if slot.material_id is not None
    ]
    duplicate_ids = {
        material_id
        for material_id, count in Counter(assigned_ids).items()
        if count > 1
    }
    duplicate_names = sorted(
        {
            slot.material_name or "<unnamed>"
            for slot in asset.material_slots
            if slot.material_id in duplicate_ids
        }
    )
    duplicate_result = _result(
        "duplicate_materials",
        "Duplicate Material Assignments",
        Severity.WARNING if duplicate_names else Severity.PASS,
        (
            "The same material is assigned to multiple slots: "
            + ", ".join(duplicate_names)
            + "."
            if duplicate_names
            else "No duplicate material assignments found."
        ),
    )
    return [slots_result, empty_result, duplicate_result]


def _uv_result(asset: AssetSnapshot) -> CheckResult:
    has_uvs = asset.uv_map_count > 0
    return _result(
        "uv_maps",
        "UV Maps",
        Severity.PASS if has_uvs else Severity.ERROR,
        (
            f"Mesh has {asset.uv_map_count} UV map(s)."
            if has_uvs
            else "Mesh has no UV maps."
        ),
    )


def _texture_result(asset: AssetSnapshot) -> CheckResult:
    missing = [
        reference
        for reference in asset.texture_references
        if not reference.is_available
    ]
    if not missing:
        count = len(asset.texture_references)
        message = (
            f"All {count} image texture reference(s) are available."
            if count
            else "No image texture nodes require file validation."
        )
        return _result("image_textures", "Image Textures", Severity.PASS, message)

    descriptions = [
        f"{reference.material_name}/{reference.node_name}: {reference.detail}"
        for reference in missing
    ]
    return _result(
        "image_textures",
        "Image Textures",
        Severity.ERROR,
        "Missing image texture reference(s): " + "; ".join(descriptions),
    )


def validate_asset(
    asset: AssetSnapshot,
    config: ValidationConfig,
) -> ObjectValidationReport:
    """Validate one asset snapshot without modifying it."""
    if asset.object_type != "MESH":
        return ObjectValidationReport(
            object_name=asset.name,
            object_type=asset.object_type,
            was_validated=False,
            results=(
                _result(
                    "object_type",
                    "Object Type",
                    Severity.WARNING,
                    (
                        f"Skipped unsupported object type '{asset.object_type}'; "
                        "only meshes are validated."
                    ),
                ),
            ),
        )

    results: list[CheckResult] = []
    results.extend(_name_results(asset, config))
    results.extend(_transform_results(asset, config.transform_tolerance))
    results.extend(_geometry_results(asset, config.max_triangle_count))
    results.extend(_material_results(asset))
    results.append(_uv_result(asset))
    results.append(_texture_result(asset))
    return ObjectValidationReport(asset.name, asset.object_type, tuple(results))
