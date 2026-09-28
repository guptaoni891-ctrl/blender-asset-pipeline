"""User-configurable add-on preferences."""

import bpy
from bpy.props import EnumProperty, FloatProperty, IntProperty, StringProperty

from .constants import ADDON_PACKAGE_ID
from .models import NamingConvention, ValidationConfig


class BAP_AddonPreferences(bpy.types.AddonPreferences):
    """Persistent settings controlling validation policy."""

    bl_idname = ADDON_PACKAGE_ID

    max_triangle_count: IntProperty(
        name="Maximum Triangles",
        description="Maximum allowed triangulated face count per mesh",
        default=100_000,
        min=0,
        soft_max=1_000_000,
    )
    naming_convention: EnumProperty(
        name="Naming Convention",
        description="Naming convention required for object names",
        items=(
            (
                NamingConvention.LOWER_SNAKE_CASE.value,
                "lower_snake_case",
                "Example: environment_crate",
            ),
            (
                NamingConvention.UPPER_CAMEL_CASE.value,
                "UpperCamelCase",
                "Example: EnvironmentCrate",
            ),
            (
                NamingConvention.ANY.value,
                "Any Non-empty Name",
                "Do not enforce letter casing or separators",
            ),
        ),
        default=NamingConvention.LOWER_SNAKE_CASE.value,
    )
    required_prefix: StringProperty(
        name="Required Prefix",
        description=(
            "Optional case-sensitive prefix required on every validated object"
        ),
        default="",
        maxlen=64,
    )
    transform_tolerance: FloatProperty(
        name="Transform Tolerance",
        description="Maximum absolute difference accepted for applied transforms",
        default=0.0001,
        min=0.0,
        precision=6,
    )

    def draw(self, _context: bpy.types.Context) -> None:
        """Draw preferences in Blender's add-on settings."""
        layout = self.layout
        layout.prop(self, "max_triangle_count")
        layout.prop(self, "naming_convention")
        layout.prop(self, "required_prefix")
        layout.prop(self, "transform_tolerance")

    def to_validation_config(self) -> ValidationConfig:
        """Convert Blender properties to the core configuration model."""
        return ValidationConfig(
            max_triangle_count=self.max_triangle_count,
            naming_convention=NamingConvention(self.naming_convention),
            required_prefix=self.required_prefix,
            transform_tolerance=self.transform_tolerance,
        )


def get_preferences(context: bpy.types.Context) -> BAP_AddonPreferences:
    """Return this add-on's preferences or raise a clear configuration error."""
    addon = context.preferences.addons.get(ADDON_PACKAGE_ID)
    if addon is None:
        raise RuntimeError(
            f"Add-on preferences for '{ADDON_PACKAGE_ID}' are unavailable"
        )
    return addon.preferences
