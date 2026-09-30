"""Shared constants for the add-on."""

ADDON_PACKAGE_ID = __package__
if not ADDON_PACKAGE_ID:
    raise RuntimeError("The add-on must be imported as a Python package")

ADDON_VERSION = (0, 3, 1)
REPORT_SCHEMA_VERSION = "1.0"
PANEL_CATEGORY = "Asset Pipeline"
MAX_UI_RESULTS = 50
MAX_UI_FIX_ACTIONS = 50
MAX_UI_BATCH_ATTENTION_OBJECTS = 8
