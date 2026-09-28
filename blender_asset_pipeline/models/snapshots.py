"""Read-only snapshots passed from Blender into the validation core."""

from __future__ import annotations

from dataclasses import dataclass

Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class MaterialSlotSnapshot:
    """A material slot and its assigned material, if any."""

    slot_index: int
    material_name: str | None
    material_id: str | None


@dataclass(frozen=True)
class TextureReference:
    """An image texture node that can be checked for availability."""

    material_name: str
    node_name: str
    image_name: str | None
    filepath: str | None
    is_available: bool
    detail: str


@dataclass(frozen=True)
class AssetSnapshot:
    """The Blender data required by all Milestone 1 validation rules."""

    name: str
    object_type: str
    location: Vector3 = (0.0, 0.0, 0.0)
    rotation: Vector3 = (0.0, 0.0, 0.0)
    scale: Vector3 = (1.0, 1.0, 1.0)
    vertex_count: int = 0
    edge_count: int = 0
    polygon_count: int = 0
    triangle_count: int = 0
    uv_map_count: int = 0
    material_slots: tuple[MaterialSlotSnapshot, ...] = ()
    texture_references: tuple[TextureReference, ...] = ()
