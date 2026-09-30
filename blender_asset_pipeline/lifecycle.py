"""Blender application lifecycle hooks for transient add-on state."""

from __future__ import annotations

from collections.abc import MutableSequence

import bpy
from bpy.app.handlers import persistent

from .reporting.runtime import clear_latest_batch_run

_HANDLER_TAG_ATTRIBUTE = "_bap_lifecycle_handler"
TRANSIENT_LOAD_HANDLER_ID = "blender_asset_pipeline.clear_transient_state_on_load"


@persistent
def clear_transient_state_on_load(*_args: object) -> None:
    """Discard cached report data before and after Blender loads a file."""
    clear_latest_batch_run()


setattr(
    clear_transient_state_on_load,
    _HANDLER_TAG_ATTRIBUTE,
    TRANSIENT_LOAD_HANDLER_ID,
)


def _remove_transient_load_handlers(handlers: MutableSequence[object]) -> None:
    for handler in tuple(handlers):
        if (
            getattr(handler, _HANDLER_TAG_ATTRIBUTE, None)
            == TRANSIENT_LOAD_HANDLER_ID
        ):
            handlers.remove(handler)


def _load_handler_collections() -> tuple[MutableSequence[object], ...]:
    handlers: list[MutableSequence[object]] = [
        bpy.app.handlers.load_pre,
        bpy.app.handlers.load_post,
    ]
    factory_startup_handlers = getattr(
        bpy.app.handlers,
        "load_factory_startup_post",
        None,
    )
    if factory_startup_handlers is not None:
        handlers.append(factory_startup_handlers)
    return tuple(handlers)


def register_load_handlers() -> None:
    """Install one callback for file-load boundaries and factory startup loads."""
    for handlers in _load_handler_collections():
        _remove_transient_load_handlers(handlers)
        handlers.append(clear_transient_state_on_load)


def unregister_load_handlers() -> None:
    """Remove every handler instance owned by this add-on."""
    for handlers in _load_handler_collections():
        _remove_transient_load_handlers(handlers)
