"""
Custom Panel — 3x3 tool grid + stacked sub-panels for each tool.
Windows 11 Fluent Design style.
Contains all editing controls: Crop, Trim, Split, Speed, Flip, Blur, Watermark, Audio, Logo.
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QStackedWidget, QFileDialog, QButtonGroup, QFrame,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from qfluentwidgets import (
    PrimaryPushButton, SwitchButton, Slider, SpinBox,
    LineEdit, ComboBox, SmoothScrollArea, CaptionLabel, IconWidget, Icon, 
    FluentIcon as FIF, InfoBar, InfoBarPosition
)
from ui.theme import Colors, SECTION_STYLE, VALUE_STYLE
from ui.layouts import FlowLayout
from core.config import APP_ROOT

# Tool definitions with FluentIcons
TOOLS = [
    ("ratio",     FIF.LAYOUT, "RATIO"),
    ("bg",        FIF.PALETTE, "BACKGROUND"),
    ("color",     FIF.BRIGHTNESS, "MÀU SẮC"),
    ("crop",      str(APP_ROOT / "assets/icons/crop.svg"), "CROP"),
    ("zoom",      str(APP_ROOT / "assets/icons/magic_wand.svg"), "ZOOM"),
    ("trim",      str(APP_ROOT / "assets/icons/cut.svg"),  "TRIM"),
    ("split",     str(APP_ROOT / "assets/icons/split.svg"), "SPLIT"),
    ("scene_split", str(APP_ROOT / "assets/icons/split.svg"), "SCENE SPLIT"),
    ("speed",     str(APP_ROOT / "assets/icons/speed.svg"), "SPEED"),
    ("flip",      str(APP_ROOT / "assets/icons/flip.svg"),  "FLIP"),
    ("blur",      str(APP_ROOT / "assets/icons/blur.svg"),  "BLUR"),
    ("watermark", str(APP_ROOT / "assets/icons/watermark.svg"), "WMARK"),
    ("audio",     str(APP_ROOT / "assets/icons/audio.svg"),  "AUDIO"),
    ("logo",      str(APP_ROOT / "assets/icons/logo.svg"),   "LOGO"),
]

CROP_RATIOS = [
    ("original", "Original"),
    ("9:16", "9:16"),
    ("16:9", "16:9"),
    ("1:1", "1:1"),
    ("4:5", "4:5"),
    ("4:3", "4:3"),
]

ZOOM_RATIOS = [
    ("free", "Tự do"),
    ("9:16", "9:16"),
    ("16:9", "16:9"),
    ("1:1", "1:1"),
    ("4:5", "4:5"),
    ("4:3", "4:3"),
]

CANVAS_RATIOS = [
    ("Gốc", None),
    ("9:16", 9/16),
    ("16:9", 16/9),
    ("1:1", 1.0),
    ("4:5", 4/5),
    ("3:4", 3/4),
    ("2:3", 2/3),
    ("4:3", 4/3),
    ("21:9", 21/9),
    ("2.35:1", 2.35),
    ("18:9", 18/9)
]

POSITIONS = [
    ("top-left", "↖ Top Left"),
    ("top-right", "↗ Top Right"),
    ("bottom-left", "↙ Bottom Left"),
    ("bottom-right", "↘ Bottom Right"),
    ("center", "⊕ Center"),
]


class _ToolButton(QPushButton):
    """Styled tool selection button (card) for the flow layout."""

    def __init__(self, fluent_icon: FIF, label: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(130, 90) # Standard width from Next.js version
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 12, 5, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        self.icon_widget = IconWidget(fluent_icon)
        self.icon_widget.setFixedSize(26, 26)
        layout.addWidget(self.icon_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # Label
        self.text_label = QLabel(label)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet(
            f"font-size: 10px; font-weight: 700; background: transparent; color: {Colors.TEXT_SECONDARY};"
        )
        layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Active indicator dot (top-right)
        self.active_dot = QWidget(self)
        self.active_dot.setFixedSize(8, 8)
        self.active_dot.setStyleSheet(f"""
            background-color: {Colors.ACCENT};
            border-radius: 4px;
            border: 1.5px solid {Colors.BG_CARD};
        """)
        self.active_dot.move(110, 8)
        self.active_dot.hide()

        self._update_style()
        self.toggled.connect(self._update_style)

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                _ToolButton {{
                    background-color: {Colors.ACCENT_BG};
                    border: 1px solid {Colors.ACCENT_BORDER};
                    border-radius: 8px;
                }}
            """)
            self.text_label.setStyleSheet(f"font-size: 10px; font-weight: 600; background: transparent; color: {Colors.ACCENT_LIGHT};")
        else:
            self.setStyleSheet(f"""
                _ToolButton {{
                    background-color: {Colors.BG_CARD};
                    border: 1px solid {Colors.BORDER_CARD};
                    border-radius: 8px;
                }}
                _ToolButton:hover {{
                    background-color: {Colors.BG_CARD_HOVER};
                    border-color: {Colors.BORDER_LIGHT};
                }}
            """)
            self.text_label.setStyleSheet(f"font-size: 10px; font-weight: 500; background: transparent; color: {Colors.TEXT_SECONDARY};")

    def set_active(self, active: bool):
        """Show or hide the active indicator dot."""
        self.active_dot.setVisible(active)
        # Update dot border color based on background
        bg = Colors.ACCENT_BG if self.isChecked() else Colors.BG_CARD
        self.active_dot.setStyleSheet(f"""
            background-color: {Colors.ACCENT};
            border-radius: 4px;
            border: 1.5px solid {bg};
        """)


class CustomPanel(QWidget):
    """Custom tools panel with 3x3 grid and stacked sub-panels."""

    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {Colors.BG_PANEL}; border: none;")
        self._settings = self._default_settings()
        self._current_crop_box = None  # Free crop box from overlay
        self._current_zoom_box = None  # Zoom box from overlay

        # Debounce timer — coalesce rapid slider/toggle changes
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(120)  # 120 ms
        self._debounce.timeout.connect(self._do_emit)

        self._confirmed_settings = self._default_settings() # Finalized (global confirm)
        self._staged_settings = self._default_settings()    # Staged (tool apply)
        self._tool_btns: dict[str, _ToolButton] = {}
        self._init_ui()
        self._update_active_indicators()

        self._emit_settings()

        self.settings_changed.emit(self.get_settings())

    def _on_confirm_clicked(self):
        """Finalize changes: update confirmed settings and markers."""
        self._confirmed_settings = self.get_settings() # Save to ground truth
        self._staged_settings = dict(self._confirmed_settings) # Sync staged with confirmed
        InfoBar.success(
            title="Thành công",
            content="Đã lưu các tùy chỉnh chỉnh sửa.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self.window()
        )
        self._update_active_indicators()
        self.settings_changed.emit(self._confirmed_settings)

    def _update_active_indicators(self):
        """Analyze confirmed settings only and mark tools."""
        s = self._confirmed_settings
        
        # Mapping tool_id to 'is_active' logic
        active_map = {
            "ratio":     (s.get("canvas_ratio_val") is not None),
            "bg":        (s.get("bg_type") != "black"),
            "color":     (
                s.get("brightness", 0) != 0 or 
                s.get("saturation", 0) != 0 or
                s.get("red", 0) != 0 or
                s.get("green", 0) != 0 or
                s.get("blue", 0) != 0
            ),
            "crop":      (s.get("crop_ratio") != "original" or s.get("crop_box") is not None),
            "zoom":      (s.get("zoom_box") is not None),
            "trim":      bool(s.get("trimmer_enabled")),
            "split":     bool(s.get("split_enabled")),
            "scene_split": bool(s.get("scene_split_enabled")),
            "speed":     (s.get("speed_value") is not None and s.get("speed_value") != 1.0),
            "flip":      bool(s.get("flip_h") or s.get("flip_v")),
            "blur":      s.get("blur", 0) > 0,
            "watermark": bool(s.get("watermark_text")),
            "audio":     bool(s.get("remove_audio") or s.get("bg_audio_path")),
            "logo":      bool(s.get("logo_path")),
        }

        for tid, btn in self._tool_btns.items():
            is_active = active_map.get(tid, False)
            btn.set_active(is_active)

    def _default_settings(self) -> dict:
        return {
            "canvas_ratio_label": "Gốc", "canvas_ratio_val": None,
            "bg_type": "black", "bg_blur_strength": 5,
            "brightness": 0, "saturation": 0,
            "red": 0, "green": 0, "blue": 0,
            "crop_ratio": "original", "crop_box": None,
            "zoom_box": None,
            "speed_value": None,
            "flip_h": False, "flip_v": False,
            "blur": 0,
            "watermark_text": "", "watermark_position": "bottom-right",
            "logo_path": "", "logo_position": "top-right", "logo_size": 20,
            "remove_audio": False, "bg_audio_path": "",
            "bg_audio_volume": 100, "bg_audio_loop": False,
            "trimmer_enabled": False, "trimmer_start": 0, "trimmer_end": 0,
            "split_enabled": False, "split_count": 0,
            "scene_split_enabled": False, "scene_split_threshold": 30,
            "trim_start": "5", "trim_end": "30",
            "output_height": None,
        }

    def _init_ui(self):
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(12, 16, 12, 12)
        main_layout.setSpacing(10)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title — Win11 section header
        title = QLabel("Custom Tools")
        title.setStyleSheet(
            f"color: {Colors.TEXT}; font-size: 14px; "
            f"font-weight: 600; letter-spacing: 0.5px; background: transparent;"
        )
        main_layout.addWidget(title)

        # Tool flow layout
        tool_container = QWidget()
        tool_layout = FlowLayout(tool_container, spacing=8)
        tool_layout.setContentsMargins(0, 0, 0, 0)
        
        from core.auth import AuthService
        auth = AuthService.instance()
        is_admin = (auth.user == "admin")

        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)

        for i, (tid, icon, label) in enumerate(TOOLS):
            btn = _ToolButton(icon, label)
            self._tool_btns[tid] = btn
            self._tool_group.addButton(btn, i)
            tool_layout.addWidget(btn)
            
            # ── Permission Logic ──
            if not is_admin and tid not in ["ratio", "bg", "color", "crop", "zoom", "trim", "split", "scene_split", "speed"]:
                btn.hide()
                
            if i == 0:
                btn.setChecked(True)

        main_layout.addWidget(tool_container)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER_DIVIDER};")
        main_layout.addWidget(sep)

        # Stacked sub-panels
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_ratio_panel())
        self._stack.addWidget(self._create_bg_panel())
        self._stack.addWidget(self._create_color_panel())
        self._stack.addWidget(self._create_crop_panel())
        self._stack.addWidget(self._create_zoom_panel())
        self._stack.addWidget(self._create_trim_panel())
        self._stack.addWidget(self._create_split_panel())
        self._stack.addWidget(self._create_scene_split_panel())
        self._stack.addWidget(self._create_speed_panel())
        self._stack.addWidget(self._create_flip_panel())
        self._stack.addWidget(self._create_blur_panel())
        self._stack.addWidget(self._create_watermark_panel())
        self._stack.addWidget(self._create_audio_panel())
        self._stack.addWidget(self._create_logo_panel())
        main_layout.addWidget(self._stack)

        scroll.setWidget(container)

        # Main overall layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll)

        # Sticky Footer Section
        footer = QWidget()
        footer.setObjectName("footer")
        # Added a subtle top border to identify the footer area
        footer.setStyleSheet(f"""
            QWidget#footer {{ 
                background-color: {Colors.BG_PANEL}; 
                border-top: 1px solid {Colors.BORDER_DIVIDER}; 
            }}
        """)
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(14, 12, 14, 12)

        self._btn_apply = PrimaryPushButton("✨  CONFIRM CHANGES")
        self._btn_apply.setFixedHeight(44)
        self._btn_apply.clicked.connect(self._on_confirm_clicked)
        footer_layout.addWidget(self._btn_apply)

        outer.addWidget(footer)

        # Connect tool grid to stack + reset logic
        self._tool_group.idClicked.connect(self._on_tool_clicked)

    def _on_tool_clicked(self, index: int):
        """Discard unconfirmed changes and switch to new tool."""
        # 1. Revert UI to the last staged state (changes accepted in tool panels but not global)
        self.load_settings(self._staged_settings)
        # 2. Switch sub-panel
        self._stack.setCurrentIndex(index)
        # 3. Ensure preview matches the reverted state
        self.settings_changed.emit(self._staged_settings)

    # ═══════════════════════════════════════════════════════════
    #  Sub-panel builders
    # ═══════════════════════════════════════════════════════════

    def _create_ratio_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(self._section_label("CÀI ĐẶT KHUNG HÌNH (CANVAS)"))
        
        ratio_container = QWidget()
        row = FlowLayout(ratio_container, spacing=4)
        row.setContentsMargins(0, 0, 0, 0)

        self._canvas_ratio_group = QButtonGroup(self)
        self._canvas_ratio_group.setExclusive(True)
        self._canvas_ratio_btns: dict[str, QPushButton] = {}
        
        for label_text, val in CANVAS_RATIOS:
            short_label = label_text.split(" ")[0]
            if short_label == "Gốc":
                short_label = "Original"
                
            btn = QPushButton(short_label)
            btn.setCheckable(True)
            btn.setProperty("ratio_value", val)
            btn.setProperty("ratio_label", label_text)
            btn.setFixedSize(72, 35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.BG_CARD}; border: 1px solid {Colors.BORDER_CARD};
                    border-radius: 6px; color: {Colors.TEXT_SECONDARY};
                    font-size: 13px; font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {Colors.BG_CARD_HOVER};
                }}
                QPushButton:checked {{
                    background: {Colors.ACCENT}; border-color: {Colors.ACCENT}; color: white;
                }}
            """)
            if val is None:
                btn.setChecked(True)
            self._canvas_ratio_btns[label_text] = btn
            self._canvas_ratio_group.addButton(btn)
            row.addWidget(btn)
            
        self._canvas_ratio_group.buttonClicked.connect(lambda: self._emit_settings())
        layout.addWidget(ratio_container)
        
        # help_text = QLabel(
        #     "Cách hoạt động:\n\n"
        #     "1. Video gốc GIỮ NGUYÊN tỉ lệ, không bị méo.\n"
        #     "2. 'Ép' ở đây là đưa video vào một cái khung mới.\n"
        #     "3. Nếu video nhỏ hơn khung, phần thừa sẽ được lấp đầy bằng màu đen mặc định."
        # )
        # help_text.setWordWrap(True)
        # help_text.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; margin-top: 10px;")
        # layout.addWidget(help_text)
        
        return panel

    def _create_bg_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(self._section_label("KIỂU NỀN (BACKGROUND)"))
        
        # Grid cho loại nền
        bg_container = QWidget()
        row = FlowLayout(bg_container, spacing=8)
        row.setContentsMargins(0, 0, 0, 0)

        self._bg_type_group = QButtonGroup(self)
        self._bg_type_group.setExclusive(True)
        self._bg_btns: dict[str, QPushButton] = {}
        
        options = [("black", "Màu Đen"), ("blur", "Viền Mờ")]
        for val, label in options:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("bg_val", val)
            btn.setFixedSize(90, 38)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.BG_CARD}; border: 1px solid {Colors.BORDER_CARD};
                    border-radius: 8px; color: {Colors.TEXT_SECONDARY};
                    font-size: 13px; font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {Colors.BG_CARD_HOVER};
                }}
                QPushButton:checked {{
                    background: {Colors.ACCENT}; border-color: {Colors.ACCENT}; color: white;
                }}
            """)
            if val == "black":
                btn.setChecked(True)
            self._bg_btns[val] = btn
            self._bg_type_group.addButton(btn)
            row.addWidget(btn)
            
        layout.addWidget(bg_container)
        
        # Slider cho độ mờ (chỉ hiện khi chọn Viền Mờ)
        self._blur_slider_container = QWidget()
        slider_layout = QVBoxLayout(self._blur_slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(6)
        
        header = QHBoxLayout()
        lbl = self._field_label("ĐỘ MỜ (BLUR STRENGTH)")
        self._bg_blur_val = QLabel("5")
        self._bg_blur_val.setStyleSheet(VALUE_STYLE)
        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(self._bg_blur_val)
        slider_layout.addLayout(header)
        
        self._bg_blur_slider = Slider(Qt.Orientation.Horizontal)
        self._bg_blur_slider.setRange(0, 100)
        self._bg_blur_slider.setValue(5)
        slider_layout.addWidget(self._bg_blur_slider)
        
        self._blur_slider_container.hide()
        layout.addWidget(self._blur_slider_container)
        
        self._bg_type_group.buttonClicked.connect(self._on_bg_type_changed)
        self._bg_blur_slider.valueChanged.connect(self._on_bg_blur_slider_changed)
        
        return panel

    def _on_bg_type_changed(self):
        btn = self._bg_type_group.checkedButton()
        if btn and btn.property("bg_val") == "blur":
            self._blur_slider_container.show()
        else:
            self._blur_slider_container.hide()
        self._emit_settings()
        
    def _on_bg_blur_slider_changed(self, value):
        self._bg_blur_val.setText(str(value))
        self._emit_settings()

    def _create_color_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._section_label("ĐIỀU CHỈNH MÀU SẮC"))

        # Brightness slider
        b_container = QWidget()
        b_layout = QVBoxLayout(b_container)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(6)
        
        b_header = QHBoxLayout()
        b_header.addWidget(self._field_label("ĐỘ SÁNG (BRIGHTNESS)"))
        b_header.addStretch()
        
        self._brightness_input = LineEdit()
        self._brightness_input.setText("0")
        self._brightness_input.setFixedWidth(50)
        self._brightness_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._brightness_input.setStyleSheet(f"height: 24px; font-size: 11px; font-weight: 600; color: {Colors.ACCENT_LIGHT}; background: {Colors.BG_SUBTLE}; border: 1px solid {Colors.ACCENT_BORDER}; border-radius: 4px;")
        b_header.addWidget(self._brightness_input)
        b_layout.addLayout(b_header)
        
        self._brightness_slider = Slider(Qt.Orientation.Horizontal)
        self._brightness_slider.setRange(-50, 50)
        self._brightness_slider.setValue(0)
        self._brightness_slider.valueChanged.connect(self._on_brightness_slider_changed)
        self._brightness_input.editingFinished.connect(self._on_brightness_input_done)
        b_layout.addWidget(self._brightness_slider)
        layout.addWidget(b_container)

        # Saturation slider
        s_container = QWidget()
        s_layout = QVBoxLayout(s_container)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(6)
        
        s_header = QHBoxLayout()
        s_header.addWidget(self._field_label("ĐỘ BÃO HÒA (SATURATION)"))
        s_header.addStretch()
        
        self._saturation_input = LineEdit()
        self._saturation_input.setText("0")
        self._saturation_input.setFixedWidth(50)
        self._saturation_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._saturation_input.setStyleSheet(f"height: 24px; font-size: 11px; font-weight: 600; color: {Colors.ACCENT_LIGHT}; background: {Colors.BG_SUBTLE}; border: 1px solid {Colors.ACCENT_BORDER}; border-radius: 4px;")
        s_header.addWidget(self._saturation_input)
        s_layout.addLayout(s_header)
        
        self._saturation_slider = Slider(Qt.Orientation.Horizontal)
        self._saturation_slider.setRange(-50, 50)
        self._saturation_slider.setValue(0)
        self._saturation_slider.valueChanged.connect(self._on_saturation_slider_changed)
        self._saturation_input.editingFinished.connect(self._on_saturation_input_done)
        s_layout.addWidget(self._saturation_slider)
        layout.addWidget(s_container)

        # Red slider
        r_container = QWidget()
        r_layout = QVBoxLayout(r_container)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(6)
        r_header = QHBoxLayout()
        r_header.addWidget(self._field_label("RED (ĐỎ)"))
        r_header.addStretch()
        self._red_input = LineEdit()
        self._red_input.setText("0")
        self._red_input.setFixedWidth(50)
        self._red_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._red_input.setStyleSheet(f"height: 24px; font-size: 11px; font-weight: 600; color: #ff6b6b; background: {Colors.BG_SUBTLE}; border: 1px solid rgba(255, 107, 107, 0.3); border-radius: 4px;")
        r_header.addWidget(self._red_input)
        r_layout.addLayout(r_header)
        self._red_slider = Slider(Qt.Orientation.Horizontal)
        self._red_slider.setRange(-50, 50)
        self._red_slider.setValue(0)
        self._red_slider.valueChanged.connect(self._on_red_slider_changed)
        self._red_input.editingFinished.connect(self._on_red_input_done)
        r_layout.addWidget(self._red_slider)
        layout.addWidget(r_container)

        # Green slider
        g_container = QWidget()
        g_layout = QVBoxLayout(g_container)
        g_layout.setContentsMargins(0, 0, 0, 0)
        g_layout.setSpacing(6)
        g_header = QHBoxLayout()
        g_header.addWidget(self._field_label("GREEN (XANH LÁ)"))
        g_header.addStretch()
        self._green_input = LineEdit()
        self._green_input.setText("0")
        self._green_input.setFixedWidth(50)
        self._green_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._green_input.setStyleSheet(f"height: 24px; font-size: 11px; font-weight: 600; color: #6ccb5f; background: {Colors.BG_SUBTLE}; border: 1px solid rgba(108, 203, 95, 0.3); border-radius: 4px;")
        g_header.addWidget(self._green_input)
        g_layout.addLayout(g_header)
        self._green_slider = Slider(Qt.Orientation.Horizontal)
        self._green_slider.setRange(-50, 50)
        self._green_slider.setValue(0)
        self._green_slider.valueChanged.connect(self._on_green_slider_changed)
        self._green_input.editingFinished.connect(self._on_green_input_done)
        g_layout.addWidget(self._green_slider)
        layout.addWidget(g_container)

        # Blue slider
        bl_container = QWidget()
        bl_layout = QVBoxLayout(bl_container)
        bl_layout.setContentsMargins(0, 0, 0, 0)
        bl_layout.setSpacing(6)
        bl_header = QHBoxLayout()
        bl_header.addWidget(self._field_label("BLUE (XANH DƯƠNG)"))
        bl_header.addStretch()
        self._blue_input = LineEdit()
        self._blue_input.setText("0")
        self._blue_input.setFixedWidth(50)
        self._blue_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._blue_input.setStyleSheet(f"height: 24px; font-size: 11px; font-weight: 600; color: #4b9fff; background: {Colors.BG_SUBTLE}; border: 1px solid rgba(75, 159, 255, 0.3); border-radius: 4px;")
        bl_header.addWidget(self._blue_input)
        bl_layout.addLayout(bl_header)
        self._blue_slider = Slider(Qt.Orientation.Horizontal)
        self._blue_slider.setRange(-50, 50)
        self._blue_slider.setValue(0)
        self._blue_slider.valueChanged.connect(self._on_blue_slider_changed)
        self._blue_input.editingFinished.connect(self._on_blue_input_done)
        bl_layout.addWidget(self._blue_slider)
        layout.addWidget(bl_container)

        return panel

    def _on_red_slider_changed(self, value):
        self._red_input.setText(str(value))
        self._emit_settings()

    def _on_red_input_done(self):
        try:
            val = int(self._red_input.text())
            self._red_slider.setValue(max(-50, min(50, val)))
        except:
            self._red_input.setText(str(self._red_slider.value()))
        self._emit_settings()

    def _on_green_slider_changed(self, value):
        self._green_input.setText(str(value))
        self._emit_settings()

    def _on_green_input_done(self):
        try:
            val = int(self._green_input.text())
            self._green_slider.setValue(max(-50, min(50, val)))
        except:
            self._green_input.setText(str(self._green_slider.value()))
        self._emit_settings()

    def _on_blue_slider_changed(self, value):
        self._blue_input.setText(str(value))
        self._emit_settings()

    def _on_blue_input_done(self):
        try:
            val = int(self._blue_input.text())
            self._blue_slider.setValue(max(-50, min(50, val)))
        except:
            self._blue_input.setText(str(self._blue_slider.value()))
        self._emit_settings()

    def _on_brightness_slider_changed(self, value):
        self._brightness_input.setText(str(value))
        self._emit_settings()

    def _on_brightness_input_done(self):
        try:
            val = int(self._brightness_input.text())
            self._brightness_slider.setValue(max(-50, min(50, val)))
        except:
            self._brightness_input.setText(str(self._brightness_slider.value()))
        self._emit_settings()

    def _on_saturation_slider_changed(self, value):
        self._saturation_input.setText(str(value))
        self._emit_settings()

    def _on_saturation_input_done(self):
        try:
            val = int(self._saturation_input.text())
            self._saturation_slider.setValue(max(-50, min(50, val)))
        except:
            self._saturation_input.setText(str(self._saturation_slider.value()))
        self._emit_settings()

    crop_mode_requested = pyqtSignal(bool)  # True=enter, False=exit
    crop_apply_clicked = pyqtSignal()
    crop_reset_clicked = pyqtSignal()

    def _create_crop_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._section_label("ASPECT RATIO"))

        # Crop ratio flow layout
        ratio_container = QWidget()
        row = FlowLayout(ratio_container, spacing=4)
        row.setContentsMargins(0, 0, 0, 0)

        self._crop_group = QButtonGroup(self)
        self._crop_group.setExclusive(True)
        self._crop_btns: dict[str, QPushButton] = {}
        for val, label in CROP_RATIOS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("ratio_value", val)
            btn.setFixedSize(72, 35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.BG_CARD}; border: 1px solid {Colors.BORDER_CARD};
                    border-radius: 6px; color: {Colors.TEXT_SECONDARY};
                    font-size: 13px; font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {Colors.BG_CARD_HOVER};
                }}
                QPushButton:checked {{
                    background: {Colors.ACCENT}; border-color: {Colors.ACCENT}; color: white;
                }}
            """)
            if val == "original":
                btn.setChecked(True)
            self._crop_btns[val] = btn
            self._crop_group.addButton(btn)
            row.addWidget(btn)
        
        self._crop_group.buttonClicked.connect(lambda: self._emit_settings())
        layout.addWidget(ratio_container)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER_DIVIDER};")
        layout.addWidget(sep)

        # Free Crop section
        layout.addWidget(self._section_label("FREE CROP"))

        self._crop_toggle = QPushButton("✂  Kéo thả Crop trên Video")
        self._crop_toggle.setCheckable(True)
        self._crop_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._crop_toggle.setFixedHeight(44)
        self._crop_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_CARD};
                border-radius: 8px;
                color: {Colors.TEXT};
                font-size: 13px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_CARD_HOVER};
                border-color: {Colors.BORDER_LIGHT};
            }}
            QPushButton:checked {{
                background-color: {Colors.ACCENT_BG};
                border: 2px solid {Colors.ACCENT};
                color: {Colors.ACCENT_LIGHT};
            }}
        """)
        self._crop_toggle.toggled.connect(self._on_crop_toggle)
        layout.addWidget(self._crop_toggle)

        # Crop info label
        self._crop_info = QLabel("Chưa cắt (Original)")
        self._crop_info.setStyleSheet(
            f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; "
            f"font-weight: 500; background: transparent; padding: 4px 0;"
        )
        layout.addWidget(self._crop_info)

        # Apply / Reset Buttons (horizontal)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        self._btn_crop_apply = QPushButton("✔  XÁC NHẬN")
        self._btn_crop_apply.setFixedHeight(36)
        self._btn_crop_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_crop_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                border: none; border-radius: 6px;
                color: white; font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_LIGHT}; }}
            QPushButton:disabled {{ background-color: {Colors.BG_SUBTLE}; color: {Colors.TEXT_TERTIARY}; }}
        """)
        self._btn_crop_apply.setEnabled(False)
        self._btn_crop_apply.clicked.connect(self._on_crop_apply_clicked)
        
        self._btn_crop_reset = QPushButton("✖  XÓA CROP")
        self._btn_crop_reset.setFixedHeight(36)
        self._btn_crop_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_crop_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {Colors.BORDER_CARD}; border-radius: 6px;
                color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_CARD_HOVER}; color: {Colors.TEXT}; }}
        """)
        self._btn_crop_reset.clicked.connect(self._on_crop_reset_clicked)
        
        btn_row.addWidget(self._btn_crop_apply)
        btn_row.addWidget(self._btn_crop_reset)
        layout.addLayout(btn_row)

        return panel

    def _on_crop_apply_clicked(self):
        """Finalize the crop."""
        # Block signals để setChecked(False) KHÔNG trigger _on_crop_toggle
        # → tránh gọi exit_crop_mode(apply=False) trước khi apply=True kịp chạy
        self._crop_toggle.blockSignals(True)
        self._crop_toggle.setChecked(False)
        self._crop_toggle.blockSignals(False)
        self._btn_crop_apply.setEnabled(False)
        
        self._staged_settings = self.get_settings()
        self.settings_changed.emit(self._staged_settings)
        
        self.crop_apply_clicked.emit()

    def _on_crop_reset_clicked(self):
        """Reset the crop to original and update ground truth."""
        self._crop_toggle.blockSignals(True)
        self._crop_toggle.setChecked(False)
        self._crop_toggle.blockSignals(False)
        self._current_crop_box = None
        
        # Reset ratio buttons to 'original'
        if "original" in self._crop_btns:
            self._crop_btns["original"].setChecked(True)
            
        self._crop_info.setText("Chưa cắt (Original)")
        self._btn_crop_apply.setEnabled(False)
        
        # Sync to staged state and preview
        self._staged_settings = self.get_settings()
        self.settings_changed.emit(self._staged_settings)
        
        self.crop_reset_clicked.emit()

    def _on_crop_toggle(self, checked: bool):
        """Toggle interactive crop mode on the preview."""
        self.crop_mode_requested.emit(checked)
        self._btn_crop_apply.setEnabled(checked)
        if not checked:
            # User canceled by toggling off. Revert to confirmed state.
            self._current_crop_box = self._confirmed_settings.get("crop_box")
            self._emit_settings()

    def update_crop_box(self, box: dict):
        """Called from MainWindow when crop overlay sends new box values."""
        self._current_crop_box = box
        self._crop_info.setText(
            f"X: {box['x']:.1f}%  Y: {box['y']:.1f}%  "
            f"W: {box['width']:.1f}%  H: {box['height']:.1f}%"
        )

    def _reset_crop_toggle(self):
        """Reset crop toggle without emitting signal."""
        self._crop_toggle.blockSignals(True)
        self._crop_toggle.setChecked(False)
        self._crop_toggle.blockSignals(False)

    # ═══════════════════════════════════════════════════════════
    #  Zoom / Scale Panel
    # ═══════════════════════════════════════════════════════════

    zoom_mode_requested = pyqtSignal(bool)
    zoom_ratio_changed = pyqtSignal(object)  # float or None

    def _create_zoom_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._section_label("ZOOM & SCALE"))

        layout.addWidget(self._field_label("TỈ LỆ LƯỚI (ASPECT RATIO)"))
        
        # Zoom ratio flow layout
        ratio_container = QWidget()
        row = FlowLayout(ratio_container, spacing=4)
        row.setContentsMargins(0, 0, 0, 0)

        self._zoom_ratio_group = QButtonGroup(self)
        self._zoom_ratio_group.setExclusive(True)
        self._zoom_ratio_btns: dict[str, QPushButton] = {}
        for val, label in ZOOM_RATIOS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("ratio_value", val)
            btn.setFixedSize(72, 35)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.BG_CARD}; border: 1px solid {Colors.BORDER_CARD};
                    border-radius: 6px; color: {Colors.TEXT_SECONDARY};
                    font-size: 13px; font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {Colors.BG_CARD_HOVER};
                }}
                QPushButton:checked {{
                    background: {Colors.ACCENT}; border-color: {Colors.ACCENT}; color: white;
                }}
            """)
            if val == "free":
                btn.setChecked(True)
            self._zoom_ratio_btns[val] = btn
            self._zoom_ratio_group.addButton(btn)
            row.addWidget(btn)
        
        self._zoom_ratio_group.buttonClicked.connect(self._on_zoom_ratio_clicked)
        layout.addWidget(ratio_container)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER_DIVIDER};")
        layout.addWidget(sep)

        # Tương tác khung lưới
        self._zoom_toggle = QPushButton("🔍  Kéo thả Zoom trên Video")
        self._zoom_toggle.setCheckable(True)
        self._zoom_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._zoom_toggle.setFixedHeight(44)
        self._zoom_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_CARD};
                border-radius: 8px;
                color: {Colors.TEXT};
                font-size: 13px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_CARD_HOVER};
                border-color: {Colors.BORDER_LIGHT};
            }}
            QPushButton:checked {{
                background-color: {Colors.ACCENT_BG};
                border: 2px solid {Colors.ACCENT};
                color: {Colors.ACCENT_LIGHT};
            }}
        """)
        self._zoom_toggle.toggled.connect(self._on_zoom_toggle)
        layout.addWidget(self._zoom_toggle)

        # Zoom info label
        self._zoom_info = QLabel("Original Size & Position")
        self._zoom_info.setStyleSheet(
            f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; "
            f"font-weight: 500; background: transparent; padding: 4px 0;"
        )
        layout.addWidget(self._zoom_info)

        # Apply / Reset Buttons (horizontal)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        self._btn_zoom_apply = QPushButton("✔  XÁC NHẬN")
        self._btn_zoom_apply.setFixedHeight(36)
        self._btn_zoom_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_zoom_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                border: none; border-radius: 6px;
                color: white; font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_LIGHT}; }}
            QPushButton:disabled {{ background-color: {Colors.BG_SUBTLE}; color: {Colors.TEXT_TERTIARY}; }}
        """)
        self._btn_zoom_apply.setEnabled(False)
        self._btn_zoom_apply.clicked.connect(self._on_zoom_apply_clicked)
        
        self._btn_zoom_reset = QPushButton("✖  XÓA ZOOM")
        self._btn_zoom_reset.setFixedHeight(36)
        self._btn_zoom_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_zoom_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: 1px solid {Colors.ERROR};
                border-radius: 6px; color: {Colors.ERROR}; font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: rgba(255, 107, 107, 0.12); }}
            QPushButton:disabled {{ border-color: {Colors.BORDER_DIVIDER}; color: {Colors.TEXT_TERTIARY}; }}
        """)
        self._btn_zoom_reset.setEnabled(False)
        self._btn_zoom_reset.clicked.connect(self._on_zoom_reset_clicked)

        btn_row.addWidget(self._btn_zoom_apply)
        btn_row.addWidget(self._btn_zoom_reset)
        layout.addLayout(btn_row)

        return panel

    def _on_zoom_ratio_clicked(self, btn: QPushButton):
        """Handle zoom ratio button clicks."""
        val = btn.property("ratio_value")
        # If zoom mode is active, update the overlay ratio immediately
        if self._zoom_toggle.isChecked():
            ratio = None
            if val != "free":
                w, h = map(int, val.split(':'))
                ratio = w / h
            self.zoom_ratio_changed.emit(ratio)
        # self._emit_settings()

    def _on_zoom_toggle(self, checked: bool):
        self.zoom_mode_requested.emit(checked)
        if checked:
            self._btn_zoom_apply.setEnabled(True)
            self._btn_zoom_reset.setEnabled(True)
        if not checked:
            # User canceled by toggling off. Revert to confirmed state.
            self._current_zoom_box = self._confirmed_settings.get("zoom_box")
            self._zoom_info.setText("Original Size & Position" if not self._current_zoom_box else "Khung Zoom Tùy Chỉnh")
            self._emit_settings()

    zoom_apply_clicked = pyqtSignal()
    zoom_reset_clicked = pyqtSignal()

    def _on_zoom_apply_clicked(self):
        self._zoom_toggle.blockSignals(True)
        self._zoom_toggle.setChecked(False)
        self._zoom_toggle.blockSignals(False)
        self._btn_zoom_apply.setEnabled(False)
        
        self._staged_settings = self.get_settings()
        self.settings_changed.emit(self._staged_settings)
        
        self.zoom_apply_clicked.emit()

    def _on_zoom_reset_clicked(self):
        self._zoom_toggle.blockSignals(True)
        self._zoom_toggle.setChecked(False)
        self._zoom_toggle.blockSignals(False)
        self._current_zoom_box = None
        self._zoom_info.setText("Original Size & Position")
        self._btn_zoom_reset.setEnabled(False)
        
        # Sync to staged state and preview
        self._staged_settings = self.get_settings()
        self.settings_changed.emit(self._staged_settings)
        
        self.zoom_reset_clicked.emit()

    def update_zoom_box(self, info: str, box: dict):
        """Called from MainWindow when zoom overlay changes box."""
        self._zoom_info.setText(info)
        self._current_zoom_box = box


    def _format_time(self, seconds):
        """Format seconds into MM:SS"""
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def _parse_time(self, text):
        """Parse MM:SS or seconds into seconds"""
        try:
            if ":" in text:
                parts = text.split(":")
                return int(parts[0]) * 60 + int(parts[1])
            return int(text)
        except:
            return 0

    def _create_trim_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. ACTIVATION CARD
        act_card = QFrame(panel)
        act_card.setObjectName("act_card")
        act_card.setStyleSheet(f"""
            QFrame#act_card {{
                background-color: {Colors.ACCENT_BG};
                border: 1px solid {Colors.ACCENT_BORDER};
                border-radius: 8px;
            }}
        """)
        act_layout = QHBoxLayout(act_card)
        act_layout.setContentsMargins(15, 12, 15, 12)
        
        ico = IconWidget(str(APP_ROOT / "assets/icons/cut.svg"))
        ico.setFixedSize(24, 24)
        act_layout.addWidget(ico)
        
        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)
        title = QLabel("KÍCH HOẠT TRIMMER")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: white; background: transparent;")
        sub = QLabel("Bật để cắt bỏ đoạn đầu và đoạn cuối")
        sub.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY}; background: transparent;")
        txt_layout.addWidget(title)
        txt_layout.addWidget(sub)
        act_layout.addLayout(txt_layout)
        
        act_layout.addStretch()
        self._trim_switch = SwitchButton()
        self._trim_switch.setOnText("")
        self._trim_switch.setOffText("")
        self._trim_switch.checkedChanged.connect(self._emit_settings)
        act_layout.addWidget(self._trim_switch)
        
        layout.addWidget(act_card)

        # 2+3. CONTENT CONTAINER (To be enabled/disabled)
        self._trim_content = QWidget()
        content_layout = QVBoxLayout(self._trim_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)

        # TIME INPUTS (Editable)
        time_row = QHBoxLayout()
        time_row.setSpacing(10)
        
        # Start
        s_group = QVBoxLayout()
        s_lbl = QLabel("BỎ ĐOẠN ĐẦU (GIÂY)")
        s_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {Colors.TEXT_SECONDARY}; background: transparent;")
        self._trim_start_input = LineEdit()
        self._trim_start_input.setText("00:00")
        self._trim_start_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._trim_start_input.setStyleSheet(f"height: 42px; font-family: 'Consolas'; font-size: 16px; font-weight: 600; color: {Colors.ACCENT_LIGHT}; background: {Colors.BG_SUBTLE}; border-radius: 8px;")
        s_group.addWidget(s_lbl)
        s_group.addWidget(self._trim_start_input)
        time_row.addLayout(s_group)

        # End
        e_group = QVBoxLayout()
        e_lbl = QLabel("BỎ ĐOẠN CUỐI (GIÂY)")
        e_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {Colors.TEXT_SECONDARY}; background: transparent;")
        self._trim_end_input = LineEdit()
        self._trim_end_input.setText("00:00")
        self._trim_end_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._trim_end_input.setStyleSheet(f"height: 42px; font-family: 'Consolas'; font-size: 16px; font-weight: 600; color: {Colors.ACCENT_LIGHT}; background: {Colors.BG_SUBTLE}; border-radius: 8px;")
        e_group.addWidget(e_lbl)
        e_group.addWidget(self._trim_end_input)
        time_row.addLayout(e_group)
        content_layout.addLayout(time_row)

        # SLIDERS
        content_layout.addSpacing(10)
        
        # Start Slider Row
        s_head = QHBoxLayout()
        s_title = QLabel("CẮT ĐẦU")
        s_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        self._trim_start_val_lbl = QLabel("00:00")
        self._trim_start_val_lbl.setStyleSheet(f"color: {Colors.ACCENT}; font-weight: bold; font-family: 'Consolas'; background: transparent;")
        s_head.addWidget(s_title)
        s_head.addStretch()
        s_head.addWidget(self._trim_start_val_lbl)
        content_layout.addLayout(s_head)

        self._trim_start_slider = Slider(Qt.Orientation.Horizontal)
        self._trim_start_slider.setRange(0, 300)
        content_layout.addWidget(self._trim_start_slider)

        content_layout.addSpacing(5)

        # End Slider Row
        e_head = QHBoxLayout()
        e_title = QLabel("CẮT CUỐI")
        e_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        self._trim_end_val_lbl = QLabel("00:00")
        self._trim_end_val_lbl.setStyleSheet(f"color: {Colors.ACCENT}; font-weight: bold; font-family: 'Consolas'; background: transparent;")
        e_head.addWidget(e_title)
        e_head.addStretch()
        e_head.addWidget(self._trim_end_val_lbl)
        content_layout.addLayout(e_head)

        self._trim_end_slider = Slider(Qt.Orientation.Horizontal)
        self._trim_end_slider.setRange(0, 300)
        content_layout.addWidget(self._trim_end_slider)

        layout.addWidget(self._trim_content)

        # Opacity Effect for visual feedback
        self._trim_opacity = QGraphicsOpacityEffect(self._trim_content)
        self._trim_opacity.setOpacity(0.4)
        self._trim_content.setGraphicsEffect(self._trim_opacity)

        # Initial state
        self._trim_content.setEnabled(False)

        # Connect signals
        self._trim_switch.checkedChanged.connect(self._on_trim_switch_toggled)
        self._trim_start_slider.valueChanged.connect(self._on_trim_start_changed)
        self._trim_end_slider.valueChanged.connect(self._on_trim_end_changed)
        self._trim_start_input.editingFinished.connect(self._on_trim_start_input_done)
        self._trim_end_input.editingFinished.connect(self._on_trim_end_input_done)

        return panel

    def _on_trim_switch_toggled(self, checked):
        self._trim_content.setEnabled(checked)
        self._trim_opacity.setOpacity(1.0 if checked else 0.4)
        self._emit_settings()

    def _on_trim_start_changed(self, val):
        t = self._format_time(val)
        self._trim_start_val_lbl.setText(t)
        self._trim_start_input.setText(t)
        self._emit_settings()

    def _on_trim_end_changed(self, val):
        t = self._format_time(val)
        self._trim_end_val_lbl.setText(t)
        self._trim_end_input.setText(t)
        self._emit_settings()

    def _on_trim_start_input_done(self):
        val = self._parse_time(self._trim_start_input.text())
        self._trim_start_slider.setValue(val)
        self._emit_settings()

    def _on_trim_end_input_done(self):
        val = self._parse_time(self._trim_end_input.text())
        self._trim_end_slider.setValue(val)
        self._emit_settings()

    def _create_split_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title (CÀI ĐẶT)
        title = QLabel("CÀI ĐẶT")
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(title)

        # 1. ACTIVATION CARD
        act_card = QFrame(panel)
        act_card.setObjectName("act_card")
        act_card.setStyleSheet(f"""
            QFrame#act_card {{
                background-color: {Colors.ACCENT_BG};
                border: 1px solid {Colors.ACCENT_BORDER};
                border-radius: 8px;
            }}
        """)
        act_layout = QHBoxLayout(act_card)
        act_layout.setContentsMargins(15, 12, 15, 12)
        
        ico = IconWidget(FIF.SYNC) # Using Sync icon for Random
        ico.setFixedSize(24, 24)
        act_layout.addWidget(ico)
        
        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)
        act_title = QLabel("KÍCH HOẠT RANDOM")
        act_title.setStyleSheet("font-weight: bold; font-size: 12px; color: white; background: transparent;")
        sub = QLabel("Bật để cắt video ngẫu nhiên")
        sub.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY}; background: transparent;")
        txt_layout.addWidget(act_title)
        txt_layout.addWidget(sub)
        act_layout.addLayout(txt_layout)
        
        act_layout.addStretch()
        self._split_switch = SwitchButton()
        self._split_switch.setOnText("")
        self._split_switch.setOffText("")
        self._split_switch.checkedChanged.connect(self._emit_settings)
        act_layout.addWidget(self._split_switch)
        
        layout.addWidget(act_card)
        layout.addSpacing(10)

        # CONTENT CONTAINER
        self._split_content = QWidget()
        content_layout = QVBoxLayout(self._split_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)

        # 2. SỐ LƯỢNG PHẦN (N)
        n_head = QHBoxLayout()
        n_title = QLabel("SỐ LƯỢNG PHẦN (N)")
        n_title.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-size: 11px; font-weight: bold; background: transparent;")
        self._split_count_input = LineEdit()
        self._split_count_input.setText("0")
        self._split_count_input.setFixedWidth(70)
        self._split_count_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._split_count_input.setStyleSheet(f"height: 28px; font-size: 12px; font-weight: 600; color: {Colors.ACCENT_LIGHT}; background: {Colors.ACCENT_BG}; border: 1px solid {Colors.ACCENT_BORDER}; border-radius: 6px;")
        n_head.addWidget(n_title)
        n_head.addStretch()
        n_head.addWidget(self._split_count_input)
        content_layout.addLayout(n_head)

        self._split_count_slider = Slider(Qt.Orientation.Horizontal)
        self._split_count_slider.setRange(0, 50)
        content_layout.addWidget(self._split_count_slider)

        help_txt = QLabel("Để là 0 để tự động cắt theo độ dài Min/Max")
        help_txt.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; font-style: italic; background: transparent;")
        content_layout.addWidget(help_txt)

        # Divider
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER_DIVIDER}; margin: 5px 0;")
        content_layout.addWidget(sep)

        # 3. ĐỘ DÀI TỐI THIỂU
        min_head = QHBoxLayout()
        min_title = QLabel("ĐỘ DÀI TỐI THIỂU (GIÂY)")
        min_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        self._split_min_input = LineEdit()
        self._split_min_input.setText("5")
        self._split_min_input.setFixedWidth(50)
        self._split_min_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._split_min_input.setStyleSheet(f"height: 28px; font-size: 12px; font-weight: 600; color: {Colors.ACCENT_LIGHT}; background: {Colors.BG_SUBTLE}; border: 1px solid {Colors.ACCENT_BORDER}; border-radius: 6px;")
        min_head.addWidget(min_title)
        min_head.addStretch()
        min_head.addWidget(self._split_min_input)
        content_layout.addLayout(min_head)

        self._split_min_slider = Slider(Qt.Orientation.Horizontal)
        self._split_min_slider.setRange(1, 600)
        content_layout.addWidget(self._split_min_slider)

        content_layout.addSpacing(5)

        # 4. ĐỘ DÀI TỐI ĐA
        max_head = QHBoxLayout()
        max_title = QLabel("ĐỘ DÀI TỐI ĐA (GIÂY)")
        max_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        self._split_max_input = LineEdit()
        self._split_max_input.setText("30")
        self._split_max_input.setFixedWidth(50)
        self._split_max_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._split_max_input.setStyleSheet(f"height: 28px; font-size: 12px; font-weight: 600; color: {Colors.ACCENT_LIGHT}; background: {Colors.BG_SUBTLE}; border: 1px solid {Colors.ACCENT_BORDER}; border-radius: 6px;")
        max_head.addWidget(max_title)
        max_head.addStretch()
        max_head.addWidget(self._split_max_input)
        content_layout.addLayout(max_head)

        self._split_max_slider = Slider(Qt.Orientation.Horizontal)
        self._split_max_slider.setRange(1, 600)
        content_layout.addWidget(self._split_max_slider)

        layout.addWidget(self._split_content)

        # Opacity Effect
        self._split_opacity = QGraphicsOpacityEffect(self._split_content)
        self._split_opacity.setOpacity(0.4)
        self._split_content.setGraphicsEffect(self._split_opacity)

        # Initial State
        self._split_content.setEnabled(False)

        # Connect signals
        self._split_switch.checkedChanged.connect(self._on_split_switch_toggled)

        self._split_count_slider.valueChanged.connect(self._on_split_count_slider_changed)
        self._split_min_slider.valueChanged.connect(self._on_split_min_slider_changed)
        self._split_max_slider.valueChanged.connect(self._on_split_max_slider_changed)

        self._split_count_input.editingFinished.connect(self._on_split_count_input_done)
        self._split_min_input.editingFinished.connect(self._on_split_min_input_done)
        self._split_max_input.editingFinished.connect(self._on_split_max_input_done)

        return panel

    def _on_split_switch_toggled(self, checked):
        self._split_content.setEnabled(checked)
        self._split_opacity.setOpacity(1.0 if checked else 0.4)
        self._emit_settings()

    def _on_split_count_slider_changed(self, val):
        self._split_count_input.setText(f"{val} phần" if val > 0 else "0")
        self._emit_settings()

    def _on_split_min_slider_changed(self, val):
        self._split_min_input.setText(str(val))
        self._emit_settings()

    def _on_split_max_slider_changed(self, val):
        self._split_max_input.setText(str(val))
        self._emit_settings()

    def _on_split_count_input_done(self):
        text = self._split_count_input.text().replace(" phần", "")
        try:
            val = int(text)
            self._split_count_slider.setValue(val)
        except: pass
        self._emit_settings()

    def _on_split_min_input_done(self):
        try:
            val = int(self._split_min_input.text())
            self._split_min_slider.setValue(val)
        except: pass
        self._emit_settings()

    def _on_split_max_input_done(self):
        try:
            val = int(self._split_max_input.text())
            self._split_max_slider.setValue(val)
        except: pass
        self._emit_settings()

    scene_detect_requested = pyqtSignal(bool)
    view_scenes_clicked = pyqtSignal(bool)

    def _create_scene_split_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._section_label("PHÂN CẢNH TỰ ĐỘNG"))

        # Activation Card
        act_card = QFrame(panel)
        act_card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.ACCENT_BG};
                border: 1px solid {Colors.ACCENT_BORDER};
                border-radius: 8px;
            }}
        """)
        act_layout = QHBoxLayout(act_card)
        act_layout.setContentsMargins(15, 12, 15, 12)
        
        ico = IconWidget(str(APP_ROOT / "assets/icons/split.svg"))
        ico.setFixedSize(24, 24)
        act_layout.addWidget(ico)
        
        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)
        act_title = QLabel("KÍCH HOẠT SCENE DETECT")
        act_title.setStyleSheet("font-weight: bold; font-size: 12px; color: white; background: transparent;")
        sub = QLabel("Tự động phát hiện phân cảnh")
        sub.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY}; background: transparent;")
        txt_layout.addWidget(act_title)
        txt_layout.addWidget(sub)
        act_layout.addLayout(txt_layout)
        
        act_layout.addStretch()
        self._scene_split_switch = SwitchButton()
        self._scene_split_switch.setOnText("")
        self._scene_split_switch.setOffText("")
        self._scene_split_switch.checkedChanged.connect(self._on_scene_split_switch_toggled)
        act_layout.addWidget(self._scene_split_switch)
        
        layout.addWidget(act_card)
        layout.addSpacing(10)

        # Content
        self._scene_split_content = QWidget()
        content_layout = QVBoxLayout(self._scene_split_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)

        th_head = QHBoxLayout()
        th_title = QLabel("THRESHOLD (ĐỘ NHẠY)")
        th_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        self._scene_th_val = QLabel("30")
        self._scene_th_val.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-weight: bold; background: transparent;")
        th_head.addWidget(th_title)
        th_head.addStretch()
        th_head.addWidget(self._scene_th_val)
        content_layout.addLayout(th_head)

        self._scene_th_slider = Slider(Qt.Orientation.Horizontal)
        self._scene_th_slider.setRange(10, 80)
        self._scene_th_slider.setValue(30)
        self._scene_th_slider.valueChanged.connect(self._on_scene_th_changed)
        content_layout.addWidget(self._scene_th_slider)

        self._scene_info = QLabel("Chưa phát hiện cảnh nào")
        self._scene_info.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; background: transparent; padding: 4px 0;")
        content_layout.addWidget(self._scene_info)

        self._btn_view_scenes = PrimaryPushButton("👁  XEM PHÂN CẢNH")
        self._btn_view_scenes.setFixedHeight(44)
        self._btn_view_scenes.clicked.connect(self._on_view_scenes_clicked)
        content_layout.addWidget(self._btn_view_scenes)

        # Merge Switch
        merge_layout = QHBoxLayout()
        merge_lbl = QLabel("Gộp thành 1 video duy nhất sau khi xử lý")
        merge_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; background: transparent;")
        merge_layout.addWidget(merge_lbl)
        merge_layout.addStretch()
        self._scene_merge_switch = SwitchButton()
        self._scene_merge_switch.setOnText("")
        self._scene_merge_switch.setOffText("")
        self._scene_merge_switch.setChecked(True)
        self._scene_merge_switch.checkedChanged.connect(self._emit_settings)
        merge_layout.addWidget(self._scene_merge_switch)
        content_layout.addLayout(merge_layout)

        layout.addWidget(self._scene_split_content)

        self._scene_split_opacity = QGraphicsOpacityEffect(self._scene_split_content)
        self._scene_split_opacity.setOpacity(0.4)
        self._scene_split_content.setGraphicsEffect(self._scene_split_opacity)

        self._scene_split_content.setEnabled(False)
        self._viewing_scenes = False

        return panel

    def _on_scene_split_switch_toggled(self, checked):
        self._scene_split_content.setEnabled(checked)
        self._scene_split_opacity.setOpacity(1.0 if checked else 0.4)
        self._emit_settings()
        # Removed automatic scene detection on toggle

    def _on_scene_th_changed(self, val):
        self._scene_th_val.setText(str(val))
        self._emit_settings()

    def set_detecting_state(self, is_detecting: bool):
        if is_detecting:
            self._btn_view_scenes.setText("⏳ Đang phân tách...")
            self._btn_view_scenes.setEnabled(False)
        else:
            self._btn_view_scenes.setEnabled(True)
            if self._viewing_scenes:
                self._btn_view_scenes.setText("↩  TRỞ VỀ DANH SÁCH VIDEO")
            else:
                self._btn_view_scenes.setText("👁  XEM PHÂN CẢNH")

    def _on_view_scenes_clicked(self):
        if not self._viewing_scenes:
            self.view_scenes_clicked.emit(True)
        else:
            self._viewing_scenes = False
            self.set_detecting_state(False)
            self.view_scenes_clicked.emit(False)

    def set_scene_info(self, text):
        self._scene_info.setText(text)

    def reset_view_button(self):
        self._viewing_scenes = False
        self.set_detecting_state(False)

    def _create_speed_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Section Label
        layout.addWidget(self._section_label("TỐC ĐỘ PHÁT"))

        # 1. HEADER ROW (Icon + Label + Input Badge)
        head = QHBoxLayout()
        head.setSpacing(10)
        
        ico = IconWidget(str(APP_ROOT / "assets/icons/speed.svg"))
        ico.setFixedSize(22, 22)
        head.addWidget(ico)
        
        title = QLabel("TỐC ĐỘ XỬ LÝ")
        title.setStyleSheet(f"color: {Colors.TEXT}; font-size: 13px; font-weight: bold; background: transparent;")
        head.addWidget(title)
        
        head.addStretch()
        
        self._speed_input = LineEdit()
        self._speed_input.setText("1.00x")
        self._speed_input.setFixedWidth(70)
        self._speed_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._speed_input.setStyleSheet(f"height: 28px; font-size: 12px; font-weight: 600; color: {Colors.ACCENT_LIGHT}; background: {Colors.ACCENT_BG}; border: 1px solid {Colors.ACCENT_BORDER}; border-radius: 6px;")
        head.addWidget(self._speed_input)
        layout.addLayout(head)

        # 2. MAIN SLIDER
        self._speed_slider = Slider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 400)
        self._speed_slider.setValue(100)
        layout.addWidget(self._speed_slider)
        
        # 3. MARKERS ROW (0.5x | RESET | 4.0x)
        markers = QHBoxLayout()
        
        lbl_min = QLabel("0.5x")
        lbl_min.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        markers.addWidget(lbl_min)
        
        markers.addStretch()
        
        self._btn_speed_reset = QPushButton("ĐẶT LẠI 1.0X")
        self._btn_speed_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_speed_reset.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-size: 11px; font-weight: 800; border: none; background: transparent;")
        self._btn_speed_reset.clicked.connect(lambda: self._set_speed(1.0))
        markers.addWidget(self._btn_speed_reset)
        
        markers.addStretch()
        
        lbl_max = QLabel("4.0x")
        lbl_max.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        markers.addWidget(lbl_max)
        
        layout.addLayout(markers)

        # Signals
        self._speed_slider.valueChanged.connect(self._on_speed_slider_changed)
        self._speed_input.editingFinished.connect(self._on_speed_input_done)

        return panel

    def _on_speed_slider_changed(self, val):
        speed = val / 100.0
        if speed.is_integer():
            self._speed_input.setText(f"{int(speed)}x")
        else:
            self._speed_input.setText(f"{speed:.2f}x")
        self._emit_settings()

    def _on_speed_input_done(self):
        text = self._speed_input.text().replace("x", "")
        try:
            val = float(text)
            self._speed_slider.setValue(int(val * 100))
        except: pass
        self._emit_settings()

    def _create_flip_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._section_label("HƯỚNG LẬT"))

        row = QHBoxLayout()
        row.setSpacing(10)

        style = f"""
            QPushButton {{
                background-color: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER_CARD};
                border-radius: 8px;
                color: {Colors.TEXT_SECONDARY};
                font-size: 16px;
                font-weight: 600;
                padding: 15px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_CARD_HOVER};
                border-color: {Colors.BORDER_LIGHT};
            }}
            QPushButton:checked {{
                background-color: {Colors.ACCENT_BG};
                border: 1px solid {Colors.ACCENT_BORDER};
                color: white;
            }}
        """

        # Horizontal Flip Button
        self._flip_h_btn = QPushButton(" ↔  Ngang")
        self._flip_h_btn.setCheckable(True)
        self._flip_h_btn.setFixedHeight(55)
        self._flip_h_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._flip_h_btn.setStyleSheet(style)
        self._flip_h_btn.clicked.connect(lambda: self._emit_settings())
        row.addWidget(self._flip_h_btn, 1)

        # Vertical Flip Button
        self._flip_v_btn = QPushButton(" ↕  Dọc")
        self._flip_v_btn.setCheckable(True)
        self._flip_v_btn.setFixedHeight(55)
        self._flip_v_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._flip_v_btn.setStyleSheet(style)
        self._flip_v_btn.clicked.connect(lambda: self._emit_settings())
        row.addWidget(self._flip_v_btn, 1)

        layout.addLayout(row)
        return panel

    def _create_blur_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. HEADER ROW (Icon + Label)
        head = QHBoxLayout()
        head.setSpacing(10)
        
        ico = IconWidget(str(APP_ROOT / "assets/icons/blur.svg"))
        ico.setFixedSize(22, 22)
        head.addWidget(ico)
        
        title = QLabel("MỨC ĐỘ BLUR")
        title.setStyleSheet(f"color: {Colors.TEXT}; font-size: 13px; font-weight: bold; background: transparent;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        # 2. MAIN SLIDER
        self._blur_slider = Slider(Qt.Orientation.Horizontal)
        self._blur_slider.setRange(0, 20)
        self._blur_slider.setValue(0)
        layout.addWidget(self._blur_slider)

        # 3. MARKERS ROW (0% | value | 20px)
        markers = QHBoxLayout()
        
        lbl_min = QLabel("0% (None)")
        lbl_min.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        markers.addWidget(lbl_min)
        
        markers.addStretch()
        
        self._blur_val_lbl = QLabel("0px")
        self._blur_val_lbl.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-size: 11px; font-weight: 800; background: transparent;")
        markers.addWidget(self._blur_val_lbl)
        
        markers.addStretch()
        
        lbl_max = QLabel("20px (Max)")
        lbl_max.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        markers.addWidget(lbl_max)
        
        layout.addLayout(markers)

        self._blur_slider.valueChanged.connect(self._on_blur_changed)

        return panel

    def _on_blur_changed(self, value):
        self._blur_val_lbl.setText(f"{value}px")
        self._emit_settings()

    def _create_watermark_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._section_label("TEXT WATERMARK"))

        self._wm_text = LineEdit()
        self._wm_text.setPlaceholderText("Enter watermark text...")
        self._wm_text.setFixedHeight(40)
        self._wm_text.textChanged.connect(lambda: self._emit_settings())
        layout.addWidget(self._wm_text)

        layout.addWidget(self._field_label("POSITION"))
        self._wm_pos = ComboBox()
        for val, lbl in POSITIONS:
            self._wm_pos.addItem(lbl, val)
        self._wm_pos.setCurrentIndex(3)  # bottom-right
        self._wm_pos.setFixedHeight(40)
        self._wm_pos.currentIndexChanged.connect(lambda: self._emit_settings())
        layout.addWidget(self._wm_pos)

        return panel

    def _create_audio_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._section_label("AUDIO SETTINGS"))

        # Mute switch
        mute_row = QHBoxLayout()
        mute_lbl = QLabel("Mute Original Audio")
        mute_lbl.setStyleSheet(f"color: {Colors.TEXT}; font-size: 14px; background: transparent;")
        mute_row.addWidget(mute_lbl)
        mute_row.addStretch()
        self._mute_switch = SwitchButton()
        self._mute_switch.setOnText("")
        self._mute_switch.setOffText("")
        self._mute_switch.checkedChanged.connect(lambda: self._emit_settings())
        mute_row.addWidget(self._mute_switch)
        layout.addLayout(mute_row)

        # Background music
        layout.addWidget(self._field_label("BACKGROUND MUSIC"))
        bg_row = QHBoxLayout()
        self._bg_audio_path = LineEdit()
        self._bg_audio_path.setPlaceholderText("Select audio file...")
        self._bg_audio_path.setReadOnly(True)
        self._bg_audio_path.setFixedHeight(40)
        bg_row.addWidget(self._bg_audio_path, 1)
        btn_bg = PrimaryPushButton("Browse")
        btn_bg.setFixedHeight(40)
        btn_bg.setFixedWidth(80)
        btn_bg.clicked.connect(self._choose_bg_audio)
        bg_row.addWidget(btn_bg)
        layout.addLayout(bg_row)

        # Volume
        vol_row = QHBoxLayout()
        vol_row.addWidget(self._field_label("VOLUME"))
        self._bg_vol_label = QLabel("100%")
        self._bg_vol_label.setStyleSheet(VALUE_STYLE)
        self._bg_vol_label.setFixedWidth(44)
        self._bg_vol_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vol_row.addWidget(self._bg_vol_label)
        layout.addLayout(vol_row)

        self._bg_vol_slider = Slider(Qt.Orientation.Horizontal)
        self._bg_vol_slider.setRange(0, 200)
        self._bg_vol_slider.setValue(100)
        self._bg_vol_slider.valueChanged.connect(self._on_bg_vol_changed)
        layout.addWidget(self._bg_vol_slider)

        # Loop switch
        loop_row = QHBoxLayout()
        loop_lbl = QLabel("Loop Background Music")
        loop_lbl.setStyleSheet(f"color: {Colors.TEXT}; font-size: 14px; background: transparent;")
        loop_row.addWidget(loop_lbl)
        loop_row.addStretch()
        self._bg_loop = SwitchButton()
        self._bg_loop.setOnText("")
        self._bg_loop.setOffText("")
        self._bg_loop.checkedChanged.connect(lambda: self._emit_settings())
        loop_row.addWidget(self._bg_loop)
        layout.addLayout(loop_row)

        return panel

    def _create_logo_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self._section_label("LOGO OVERLAY"))

        # File picker
        logo_row = QHBoxLayout()
        self._logo_path = LineEdit()
        self._logo_path.setPlaceholderText("Select logo image...")
        self._logo_path.setReadOnly(True)
        self._logo_path.setFixedHeight(40)
        logo_row.addWidget(self._logo_path, 1)
        btn_logo = PrimaryPushButton("Browse")
        btn_logo.setFixedHeight(40)
        btn_logo.setFixedWidth(80)
        btn_logo.clicked.connect(self._choose_logo)
        logo_row.addWidget(btn_logo)
        layout.addLayout(logo_row)

        # Position
        layout.addWidget(self._field_label("POSITION"))
        self._logo_pos = ComboBox()
        for val, lbl in POSITIONS[:4]:  # no center for logo
            self._logo_pos.addItem(lbl, val)
        self._logo_pos.setCurrentIndex(1)  # top-right
        self._logo_pos.setFixedHeight(40)
        self._logo_pos.currentIndexChanged.connect(lambda: self._emit_settings())
        layout.addWidget(self._logo_pos)

        # Size slider
        size_row = QHBoxLayout()
        size_row.addWidget(self._field_label("SIZE"))
        self._logo_size_label = QLabel("20%")
        self._logo_size_label.setStyleSheet(VALUE_STYLE)
        self._logo_size_label.setFixedWidth(40)
        self._logo_size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        size_row.addWidget(self._logo_size_label)
        layout.addLayout(size_row)

        self._logo_size = Slider(Qt.Orientation.Horizontal)
        self._logo_size.setRange(5, 100)
        self._logo_size.setValue(20)
        self._logo_size.valueChanged.connect(self._on_logo_size_changed)
        layout.addWidget(self._logo_size)

        return panel

    # ═══════════════════════════════════════════════════════════
    #  Event handlers
    # ═══════════════════════════════════════════════════════════

    def _on_speed_changed(self, value):
        speed = value / 100.0
        self._speed_label.setText(f"{speed:.2f}x")
        self._emit_settings()

    def _set_speed(self, speed: float):
        self._speed_slider.setValue(int(speed * 100))



    def _on_bg_vol_changed(self, value):
        self._bg_vol_label.setText(f"{value}%")
        self._emit_settings()

    def _on_logo_size_changed(self, value):
        self._logo_size_label.setText(f"{value}%")
        self._emit_settings()

    def _choose_bg_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select audio file", "",
            "Audio Files (*.mp3 *.wav *.m4a *.ogg *.flac);;All Files (*.*)"
        )
        if path:
            self._bg_audio_path.setText(path)
            self._emit_settings()

    def _choose_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select logo image", "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.webp);;All Files (*.*)"
        )
        if path:
            self._logo_path.setText(path)
            self._emit_settings()

    # ═══════════════════════════════════════════════════════════
    #  Settings get/set
    # ═══════════════════════════════════════════════════════════

    def _emit_settings(self):
        """Schedule a debounced emission of settings."""
        if getattr(self, '_is_loading', False):
            return
        self._debounce.start()

    def _do_emit(self):
        """Actually emit settings (called after debounce timer fires)."""
        # We emit current UI state for preview, but DO NOT update dots or confirmed settings.
        self.settings_changed.emit(self.get_settings())

    def get_settings(self) -> dict:
        checked_btn = self._crop_group.checkedButton()
        crop_ratio = checked_btn.property("ratio_value") if checked_btn else "original"

        speed_raw = self._speed_slider.value() / 100.0
        speed_value = speed_raw if speed_raw != 1.0 else None

        canvas_btn = self._canvas_ratio_group.checkedButton()
        canvas_ratio_label = canvas_btn.property("ratio_label") if canvas_btn else "Gốc (Original)"
        canvas_ratio_val = canvas_btn.property("ratio_value") if canvas_btn else None
        
        bg_btn = self._bg_type_group.checkedButton()
        bg_type = bg_btn.property("bg_val") if bg_btn else "black"

        return {
            "canvas_ratio_label": canvas_ratio_label,
            "canvas_ratio_val": canvas_ratio_val,
            "bg_type": bg_type,
            "bg_blur_strength": self._bg_blur_slider.value(),
            "brightness": self._brightness_slider.value(),
            "saturation": self._saturation_slider.value(),
            "red": self._red_slider.value(),
            "green": self._green_slider.value(),
            "blue": self._blue_slider.value(),
            "crop_ratio": crop_ratio,
            "crop_box": self._current_crop_box,
            "zoom_box": self._current_zoom_box,
            "speed_value": speed_value,
            "flip_h": self._flip_h_btn.isChecked(),
            "flip_v": self._flip_v_btn.isChecked(),
            "blur": self._blur_slider.value(),
            "watermark_text": self._wm_text.text().strip() or None,
            "watermark_position": self._wm_pos.currentData() or "bottom-right",
            "logo_path": self._logo_path.text().strip() or None,
            "logo_position": self._logo_pos.currentData() or "top-right",
            "logo_size": self._logo_size.value(),
            "remove_audio": self._mute_switch.isChecked(),
            "bg_audio_path": self._bg_audio_path.text().strip() or None,
            "bg_audio_volume": self._bg_vol_slider.value(),
            "bg_audio_loop": self._bg_loop.isChecked(),
            "output_height": None,
            "trimmer_enabled": self._trim_switch.isChecked(),
            "trimmer_start": self._trim_start_slider.value(),
            "trimmer_end": self._trim_end_slider.value(),
            "split_enabled": self._split_switch.isChecked(),
            "split_count": self._split_count_slider.value(),
            "scene_split_enabled": self._scene_split_switch.isChecked(),
            "scene_split_threshold": self._scene_th_slider.value(),
            "scene_merge_enabled": getattr(self, "_scene_merge_switch", SwitchButton()).isChecked() if hasattr(self, "_scene_merge_switch") else True,
            "trim_start": str(self._split_min_slider.value()),
            "trim_end": str(self._split_max_slider.value()),
        }

    def load_settings(self, settings: dict):
        """Restore UI state from settings dict (e.g. when loading a template)."""
        self._is_loading = True
        self._confirmed_settings = settings.copy()
        self._staged_settings = settings.copy()  # Sync staged settings to avoid reset on tool click
        self.blockSignals(True)

        # Ratio
        cr_label = settings.get("canvas_ratio_label", "Gốc (Original)")
        if cr_label in self._canvas_ratio_btns:
            self._canvas_ratio_btns[cr_label].setChecked(True)

        # Background
        bg_type = settings.get("bg_type", "black")
        if bg_type in self._bg_btns:
            self._bg_btns[bg_type].setChecked(True)
            if bg_type == "blur":
                self._blur_slider_container.show()
            else:
                self._blur_slider_container.hide()
                
        self._bg_blur_slider.setValue(int(settings.get("bg_blur_strength", 40)))
        self._bg_blur_val.setText(str(int(settings.get("bg_blur_strength", 40))))

        # Color
        br = settings.get("brightness", 0)
        self._brightness_slider.setValue(br)
        self._brightness_input.setText(str(br))
        
        sa = settings.get("saturation", 0)
        self._saturation_slider.setValue(sa)
        self._saturation_input.setText(str(sa))

        r = settings.get("red", 0)
        self._red_slider.setValue(r)
        self._red_input.setText(str(r))

        g = settings.get("green", 0)
        self._green_slider.setValue(g)
        self._green_input.setText(str(g))

        b = settings.get("blue", 0)
        self._blue_slider.setValue(b)
        self._blue_input.setText(str(b))

        # Crop
        cr = settings.get("crop_ratio", "original")
        if cr in self._crop_btns:
            self._crop_btns[cr].setChecked(True)
        self._current_crop_box = settings.get("crop_box")

        # Zoom
        self._current_zoom_box = settings.get("zoom_box")
        if self._current_zoom_box:
            cw = self._current_zoom_box.get('width', 0)
            ch = self._current_zoom_box.get('height', 0)
            cx = self._current_zoom_box.get('x', 0)
            cy = self._current_zoom_box.get('y', 0)
            self._zoom_info.setText(f"Video Pos: {int(cw)}x{int(ch)} tại X:{int(cx)}, Y:{int(cy)}")
        else:
            self._zoom_info.setText("Original Size & Position")

        # Speed
        spd = settings.get("speed_value")
        self._speed_slider.setValue(int((spd or 1.0) * 100))

        # Flip
        self._flip_h_btn.setChecked(settings.get("flip_h", False))
        self._flip_v_btn.setChecked(settings.get("flip_v", False))

        # Blur
        self._blur_slider.setValue(settings.get("blur", 0))

        # Watermark
        self._wm_text.setText(settings.get("watermark_text", "") or "")
        wm_pos = settings.get("watermark_position", "bottom-right")
        for i in range(self._wm_pos.count()):
            if self._wm_pos.itemData(i) == wm_pos:
                self._wm_pos.setCurrentIndex(i)
                break

        # Logo
        self._logo_path.setText(settings.get("logo_path", "") or "")
        logo_pos = settings.get("logo_position", "top-right")
        for i in range(self._logo_pos.count()):
            if self._logo_pos.itemData(i) == logo_pos:
                self._logo_pos.setCurrentIndex(i)
                break
        self._logo_size.setValue(int(settings.get("logo_size", 20)))

        # Audio
        self._mute_switch.setChecked(settings.get("remove_audio", False))
        self._bg_audio_path.setText(settings.get("bg_audio_path", "") or "")
        self._bg_vol_slider.setValue(int(settings.get("bg_audio_volume", 100)))
        self._bg_loop.setChecked(settings.get("bg_audio_loop", False))

        # Trim
        self._trim_switch.setChecked(settings.get("trimmer_enabled", False))
        self._trim_start_slider.setValue(int(settings.get("trimmer_start", 0)))
        self._trim_end_slider.setValue(int(settings.get("trimmer_end", 0)))

        # Split
        self._split_switch.setChecked(settings.get("split_enabled", False))
        self._split_count_slider.setValue(int(settings.get("split_count", 0)))
        self._split_min_slider.setValue(int(settings.get("trim_start", 5)))
        self._split_max_slider.setValue(int(settings.get("trim_end", 30)))

        # Scene Split
        self._scene_split_switch.setChecked(settings.get("scene_split_enabled", False))
        self._scene_th_slider.setValue(int(settings.get("scene_split_threshold", 30)))
        if hasattr(self, "_scene_merge_switch"):
            self._scene_merge_switch.setChecked(settings.get("scene_merge_enabled", True))

        self.blockSignals(False)
        self._update_active_indicators()
        self._is_loading = False
        # Note: We do NOT emit here to avoid circular feedback during tool switching

    def select_tool(self, tool_id: str):
        """Programmatically select a tool (used when Nav Rail redirects)."""
        for i, (tid, _, _) in enumerate(TOOLS):
            if tid == tool_id:
                btn = self._tool_group.button(i)
                if btn:
                    btn.setChecked(True)
                    self._stack.setCurrentIndex(i)
                break

    # ═══════════════════════════════════════════════════════════
    #  UI helpers
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(SECTION_STYLE + "; background: transparent;")
        return lbl

    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; "
            f"font-weight: 600; letter-spacing: 1px; background: transparent;"
        )
        return lbl
