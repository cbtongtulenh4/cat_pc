"""
Color theme constants — Windows 11 Fluent Design (Dark Mode).
All UI files import colors from here for consistency.
Palette follows Microsoft's WinUI 3 design tokens.
"""


class Colors:
    """Design tokens — Windows 11 Fluent Design Dark Theme."""

    # ── Backgrounds (Mica-inspired layered surfaces) ──
    BG_MICA = "#1C1C1C"         # Base mica background
    BG_DARK = "#202020"         # Slightly elevated from mica
    BG_PANEL = "#2D2D2D"        # Panel / sidebar background
    BG_CARD = "#323232"         # Card / elevated surface
    BG_CARD_HOVER = "#3A3A3A"   # Card hover state
    BG_SMOKE = "#1A1A1A"        # Overlay / smoke layer
    BG_SUBTLE = "#2A2A2A"       # Subtle background for inputs

    # ── Borders (WinUI 3 control strokes) ──
    BORDER = "rgba(255, 255, 255, 0.06)"      # Subtle border
    BORDER_CARD = "rgba(255, 255, 255, 0.08)"  # Card border
    BORDER_LIGHT = "rgba(255, 255, 255, 0.12)" # Focused/hover border
    BORDER_DIVIDER = "rgba(255, 255, 255, 0.04)" # Divider line

    # ── Text ──
    TEXT = "#FFFFFF"              # Primary text (high contrast)
    TEXT_SECONDARY = "#C5C5C5"   # Secondary text
    TEXT_TERTIARY = "#9B9B9B"    # Tertiary / placeholder
    TEXT_MUTED = "#6D6D6D"       # Disabled / muted

    # ── Accent (Purple — brand identity) ──
    ACCENT = "#7c3aed"
    ACCENT_HOVER = "#6D28D9"
    ACCENT_LIGHT = "#a78bfa"
    ACCENT_BG = "rgba(124, 58, 237, 0.12)"
    ACCENT_BORDER = "rgba(124, 58, 237, 0.25)"

    # ── Status ──
    SUCCESS = "#6CCB5F"
    ERROR = "#FF6B6B"
    WARNING = "#FCE100"

    # ── Elevation shadows (Win11 uses subtle shadows) ──
    SHADOW_4 = "rgba(0, 0, 0, 0.14)"
    SHADOW_8 = "rgba(0, 0, 0, 0.26)"


# ── Reusable stylesheet fragments (Win11 style) ──

PANEL_STYLE = f"""
    background-color: {Colors.BG_PANEL};
    border: none;
"""

CARD_STYLE = f"""
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER_CARD};
    border-radius: 8px;
"""

TITLE_STYLE = f"""
    color: {Colors.TEXT};
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: transparent;
"""

SECTION_STYLE = f"""
    color: {Colors.TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.3px;
    margin-top: 8px;
    background: transparent;
"""

VALUE_STYLE = f"""
    color: {Colors.ACCENT_LIGHT};
    font-size: 13px;
    font-weight: 600;
    background: {Colors.ACCENT_BG};
    padding: 2px 8px;
    border-radius: 4px;
"""

# ── Win11 Global Application Stylesheet ──
# Applied once in main.py to give all widgets a consistent Win11 feel

WIN11_GLOBAL_STYLE = f"""
    /* ── Base ── */
    QWidget {{
        font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
        font-size: 13px;
        color: {Colors.TEXT};
    }}

    /* ── Scroll Areas ── */
    QScrollArea {{
        border: none;
        background: transparent;
    }}

    /* ── Scrollbars (thin Win11 style) ── */
    QScrollBar:vertical {{
        width: 6px;
        background: transparent;
        margin: 4px 1px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 0.15);
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(255, 255, 255, 0.25);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        height: 6px;
        background: transparent;
        margin: 1px 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: rgba(255, 255, 255, 0.15);
        border-radius: 3px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: rgba(255, 255, 255, 0.25);
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    /* ── Tooltips ── */
    QToolTip {{
        background-color: {Colors.BG_CARD};
        color: {Colors.TEXT};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ── Splitter Handles ── */
    QSplitter::handle {{
        background-color: {Colors.BORDER_DIVIDER};
    }}
    QSplitter::handle:hover {{
        background-color: {Colors.ACCENT};
    }}
"""
