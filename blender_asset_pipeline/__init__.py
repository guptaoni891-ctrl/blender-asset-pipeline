"""Blender Asset Pipeline add-on entry point."""

bl_info = {
    "name": "Asset Pipeline: Game Asset Validator & Fixer",
    "author": "Blender Asset Pipeline contributors",
    "version": (0, 3, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Asset Pipeline",
    "description": "Validate assets, export JSON reports, and preview safe fixes",
    "category": "Object",
}


def register() -> None:
    """Register add-on classes and Blender properties."""
    from .registration import register_addon

    register_addon()


def unregister() -> None:
    """Unregister add-on classes and Blender properties."""
    from .registration import unregister_addon

    unregister_addon()
