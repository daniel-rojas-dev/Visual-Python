"""
config.py — Global configuration, theme management, and constants.
Optimized: All values are lightweight dicts, no heavy objects at import time.
"""
import customtkinter as ctk


# ─── Geometry & Layout ────────────────────────────────────────────────
DEFAULT_GEOMETRY = "1280x720"
MIN_WIDTH = 960
MIN_HEIGHT = 600

# Sidebar / panel proportions (relative widths)
PALETTE_WIDTH = 200
PROPERTY_WIDTH = 240
BOTTOM_PANEL_HEIGHT = 250

# ─── Font Defaults ────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"
FONT_CODE = "Consolas"
FONT_SIZE_NORMAL = 13
FONT_SIZE_SMALL = 11
FONT_SIZE_HEADING = 16

# ─── Color Palettes ──────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_panel": "#0f3460",
        "bg_canvas": "#1a1a2e",
        "fg_text": "#e0e0e0",
        "fg_accent": "#00d4ff",
        "fg_accent2": "#7c3aed",
        "border": "#2a2a4a",
        "node_event": "#e74c3c",
        "node_action": "#2ecc71",
        "node_script": "#3498db",
        "node_math": "#f39c12",
        "node_validate": "#9b59b6",
        "node_decision": "#8e44ad",
        "selection": "#1c2e3d",
        "error": "#ff4757",
        "success": "#2ed573",
    }
}

# ─── Supported widget types (for palette) ─────────────────────────────
WIDGET_TYPES = [
    {"type": "CTkLabel", "icon": "🏷️", "display": "Label"},
    {"type": "CTkButton", "icon": "🔘", "display": "Button"},
    {"type": "CTkEntry", "icon": "🔤", "display": "Text Entry"},
    {"type": "CTkEntryNum", "icon": "🔢", "display": "Number Entry"},
]

# ─── Node Event Triggers ──────────────────────────────────────────────
EVENT_TRIGGERS = [
    "Click", "Hover", "FocusIn", "FocusOut", "KeyPress", "ValueChange",
]

# ─── Node Action Types ────────────────────────────────────────────────
ACTION_TYPES = [
    "change_text", "change_color", "change_view", "save_variable", "print_variable"
]

# ─── Project File Extension ──────────────────────────────────────────
PROJECT_EXTENSION = ".vpy"
VP_REGION_START = "# [VP_REGION_CONFIG]"
VP_REGION_END = "# [VP_END_REGION]"


class ThemeManager:
    """Manages IDE theme switching. Lightweight — stores only the mode string."""

    _current_mode: str = "dark"

    @classmethod
    def set_mode(cls, mode: str) -> None:
        """Switch theme. Hardcoded to dark."""
        cls._current_mode = "dark"
        ctk.set_appearance_mode("dark")

    @classmethod
    def get_mode(cls) -> str:
        return cls._current_mode

    @classmethod
    def colors(cls) -> dict:
        """Return the current palette dict."""
        return THEMES["dark"]
