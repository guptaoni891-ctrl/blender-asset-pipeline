"""Read-only conversion from Blender objects to core validation snapshots."""

from __future__ import annotations

import glob
import os
from collections.abc import Iterator

import bpy

from ..models import AssetSnapshot, MaterialSlotSnapshot, TextureReference


def _iter_image_nodes(
    node_tree: bpy.types.NodeTree,
    visited: set[int] | None = None,
) -> Iterator[bpy.types.Node]:
    """Yield image texture nodes, including nodes inside nested node groups."""
    visited = visited or set()
    tree_id = node_tree.as_pointer()
    if tree_id in visited:
        return
    visited.add(tree_id)

    for node in node_tree.nodes:
        if node.type == "TEX_IMAGE":
            yield node
        elif node.type == "GROUP" and node.node_tree is not None:
            yield from _iter_image_nodes(node.node_tree, visited)


def _resolved_image_path(image: bpy.types.Image) -> str:
    filepath = image.filepath
    if not filepath:
        return ""
    return bpy.path.abspath(filepath, library=image.library)


def _image_is_available(image: bpy.types.Image, resolved_path: str) -> bool:
    packed_files = getattr(image, "packed_files", ())
    if image.packed_file is not None or bool(packed_files):
        return True
    if image.source in {"GENERATED", "VIEWER"}:
        return True
    if not resolved_path:
        return False
    if image.source == "TILED" and "<UDIM>" in resolved_path:
        return bool(glob.glob(resolved_path.replace("<UDIM>", "*")))
    return os.path.isfile(resolved_path)


def _texture_references(obj: bpy.types.Object) -> tuple[TextureReference, ...]:
    references: list[TextureReference] = []
    seen_materials: set[int] = set()
    for slot in obj.material_slots:
        material = slot.material
        if material is None or not material.use_nodes or material.node_tree is None:
            continue
        material_id = material.as_pointer()
        if material_id in seen_materials:
            continue
        seen_materials.add(material_id)

        for node in _iter_image_nodes(material.node_tree):
            image = node.image
            if image is None:
                references.append(
                    TextureReference(
                        material_name=material.name,
                        node_name=node.name,
                        image_name=None,
                        filepath=None,
                        is_available=False,
                        detail="image texture node has no image assigned",
                    )
                )
                continue

            resolved_path = _resolved_image_path(image)
            available = _image_is_available(image, resolved_path)
            references.append(
                TextureReference(
                    material_name=material.name,
                    node_name=node.name,
                    image_name=image.name,
                    filepath=resolved_path or None,
                    is_available=available,
                    detail=(
                        f"'{image.name}' is available"
                        if available
                        else (
                            f"'{image.name}' file not found at "
                            f"'{resolved_path or image.filepath}'"
                        )
                    ),
                )
            )
    return tuple(references)


def snapshot_object(obj: bpy.types.Object) -> AssetSnapshot:
    """Create a validation snapshot without changing the Blender object."""
    if obj.type != "MESH":
        return AssetSnapshot(name=obj.name, object_type=obj.type)

    mesh = obj.data
    basis_location, basis_rotation, basis_scale = obj.matrix_basis.decompose()
    # Populate Blender's read-only triangulation cache; geometry remains unchanged.
    mesh.calc_loop_triangles()
    material_slots = tuple(
        MaterialSlotSnapshot(
            slot_index=index,
            material_name=slot.material.name if slot.material else None,
            material_id=str(slot.material.as_pointer()) if slot.material else None,
        )
        for index, slot in enumerate(obj.material_slots)
    )
    return AssetSnapshot(
        name=obj.name,
        object_type=obj.type,
        location=tuple(basis_location),
        rotation=tuple(basis_rotation.to_euler()),
        scale=tuple(basis_scale),
        vertex_count=len(mesh.vertices),
        edge_count=len(mesh.edges),
        polygon_count=len(mesh.polygons),
        triangle_count=len(mesh.loop_triangles),
        uv_map_count=len(mesh.uv_layers),
        material_slots=material_slots,
        texture_references=_texture_references(obj),
    )
