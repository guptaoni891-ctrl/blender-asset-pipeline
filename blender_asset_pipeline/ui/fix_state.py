"""Transient Blender UI state for previewed fix plans."""

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from ..fixing.models import (
    FixAction,
    FixCategory,
    FixKind,
    FixPlan,
    FixRisk,
)

_TRANSIENT_OPTIONS = {"SKIP_SAVE"}


class BAP_PG_fix_action(bpy.types.PropertyGroup):
    """One selectable action in the current preview."""

    fix_id: StringProperty(options=_TRANSIENT_OPTIONS)
    object_key: StringProperty(options=_TRANSIENT_OPTIONS)
    object_name: StringProperty(options=_TRANSIENT_OPTIONS)
    category: StringProperty(options=_TRANSIENT_OPTIONS)
    kind: StringProperty(options=_TRANSIENT_OPTIONS)
    title: StringProperty(options=_TRANSIENT_OPTIONS)
    description: StringProperty(options=_TRANSIENT_OPTIONS)
    risk: StringProperty(options=_TRANSIENT_OPTIONS)
    selected: BoolProperty(default=False, options=_TRANSIENT_OPTIONS)
    default_selected: BoolProperty(default=False, options=_TRANSIENT_OPTIONS)
    supported: BoolProperty(default=False, options=_TRANSIENT_OPTIONS)
    unsupported_reason: StringProperty(options=_TRANSIENT_OPTIONS)
    expected_fingerprint: StringProperty(options=_TRANSIENT_OPTIONS)
    target_name: StringProperty(options=_TRANSIENT_OPTIONS)
    target: PointerProperty(type=bpy.types.Object, options=_TRANSIENT_OPTIONS)


class BAP_PG_fix_state(bpy.types.PropertyGroup):
    """The current transient fix preview."""

    has_plan: BoolProperty(default=False, options=_TRANSIENT_OPTIONS)
    object_count: IntProperty(default=0, options=_TRANSIENT_OPTIONS)
    actions: CollectionProperty(
        type=BAP_PG_fix_action,
        options=_TRANSIENT_OPTIONS,
    )


def clear_fix_plan(state: BAP_PG_fix_state) -> None:
    """Discard the current preview without modifying any assets."""
    state.actions.clear()
    state.has_plan = False
    state.object_count = 0


def store_fix_plan(
    state: BAP_PG_fix_state,
    plan: FixPlan,
    objects_by_key: dict[str, bpy.types.Object],
) -> None:
    """Replace the current preview with a pure fix plan."""
    clear_fix_plan(state)
    state.has_plan = True
    state.object_count = plan.object_count
    for action in plan.actions:
        item = state.actions.add()
        item.fix_id = action.fix_id
        item.object_key = action.object_key
        item.object_name = action.object_name
        item.category = action.category.value
        item.kind = action.kind.value
        item.title = action.title
        item.description = action.description
        item.risk = action.risk.value
        item.selected = action.selected
        item.default_selected = action.default_selected
        item.supported = action.supported
        item.unsupported_reason = action.unsupported_reason
        item.expected_fingerprint = action.expected_fingerprint
        item.target_name = action.target_name or ""
        item.target = objects_by_key.get(action.object_key)


def action_from_state(item: BAP_PG_fix_action) -> FixAction:
    """Convert one Blender UI row back to the pure action model."""
    return FixAction(
        fix_id=item.fix_id,
        object_key=item.object_key,
        object_name=item.object_name,
        category=FixCategory(item.category),
        kind=FixKind(item.kind),
        title=item.title,
        description=item.description,
        risk=FixRisk(item.risk),
        selected=item.selected,
        default_selected=item.default_selected,
        supported=item.supported,
        unsupported_reason=item.unsupported_reason,
        expected_fingerprint=item.expected_fingerprint,
        target_name=item.target_name or None,
    )
