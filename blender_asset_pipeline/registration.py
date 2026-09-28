"""Central, ordered Blender registration lifecycle."""

from __future__ import annotations

import bpy
from bpy.props import PointerProperty

from .operators import BAP_OT_validate_active, BAP_OT_validate_selected
from .preferences import BAP_AddonPreferences
from .ui import (
    BAP_PG_validation_result,
    BAP_PG_validation_state,
    BAP_PT_validation_panel,
)

_CLASSES = (
    BAP_AddonPreferences,
    BAP_PG_validation_result,
    BAP_PG_validation_state,
    BAP_OT_validate_active,
    BAP_OT_validate_selected,
    BAP_PT_validation_panel,
)


def register_addon() -> None:
    """Register classes and scene state in dependency order."""
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bap_validation_state = PointerProperty(type=BAP_PG_validation_state)


def unregister_addon() -> None:
    """Remove scene state and unregister classes in reverse order."""
    if hasattr(bpy.types.Scene, "bap_validation_state"):
        del bpy.types.Scene.bap_validation_state
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
