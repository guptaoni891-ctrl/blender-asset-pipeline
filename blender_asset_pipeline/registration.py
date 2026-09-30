"""Central, ordered Blender registration lifecycle."""

from __future__ import annotations

import bpy
from bpy.props import PointerProperty

from .lifecycle import register_load_handlers, unregister_load_handlers
from .operators import (
    BAP_OT_apply_selected_fixes,
    BAP_OT_batch_validate_all_scenes,
    BAP_OT_batch_validate_current_scene,
    BAP_OT_clear_fix_plan,
    BAP_OT_deselect_all_fixes,
    BAP_OT_export_batch_json,
    BAP_OT_generate_fix_plan,
    BAP_OT_select_all_safe_fixes,
    BAP_OT_validate_active,
    BAP_OT_validate_selected,
)
from .preferences import BAP_AddonPreferences
from .ui import (
    BAP_PG_batch_attention,
    BAP_PG_batch_state,
    BAP_PG_fix_action,
    BAP_PG_fix_state,
    BAP_PG_validation_result,
    BAP_PG_validation_state,
    BAP_PG_validation_target,
    BAP_PT_batch_panel,
    BAP_PT_fix_panel,
    BAP_PT_validation_panel,
)

_CLASSES = (
    BAP_AddonPreferences,
    BAP_PG_batch_attention,
    BAP_PG_batch_state,
    BAP_PG_validation_result,
    BAP_PG_validation_target,
    BAP_PG_validation_state,
    BAP_PG_fix_action,
    BAP_PG_fix_state,
    BAP_OT_validate_active,
    BAP_OT_validate_selected,
    BAP_OT_batch_validate_current_scene,
    BAP_OT_batch_validate_all_scenes,
    BAP_OT_export_batch_json,
    BAP_OT_generate_fix_plan,
    BAP_OT_select_all_safe_fixes,
    BAP_OT_deselect_all_fixes,
    BAP_OT_apply_selected_fixes,
    BAP_OT_clear_fix_plan,
    BAP_PT_validation_panel,
    BAP_PT_batch_panel,
    BAP_PT_fix_panel,
)


def register_addon() -> None:
    """Register classes and scene state in dependency order."""
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bap_validation_state = PointerProperty(
        type=BAP_PG_validation_state,
        options={"SKIP_SAVE"},
    )
    bpy.types.Scene.bap_fix_state = PointerProperty(
        type=BAP_PG_fix_state,
        options={"SKIP_SAVE"},
    )
    bpy.types.Scene.bap_batch_state = PointerProperty(
        type=BAP_PG_batch_state,
        options={"SKIP_SAVE"},
    )
    register_load_handlers()


def unregister_addon() -> None:
    """Remove scene state and unregister classes in reverse order."""
    from .reporting.runtime import clear_latest_batch_run

    unregister_load_handlers()
    clear_latest_batch_run()
    if hasattr(bpy.types.Scene, "bap_batch_state"):
        del bpy.types.Scene.bap_batch_state
    if hasattr(bpy.types.Scene, "bap_fix_state"):
        del bpy.types.Scene.bap_fix_state
    if hasattr(bpy.types.Scene, "bap_validation_state"):
        del bpy.types.Scene.bap_validation_state
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
