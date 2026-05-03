"""
Scene Split UI Preview Test — 3-Tier Settings (Global > Video > Scene)
Layout: 
- Trái: Scene Split Panel
- Giữa: Video Preview
- Phải: Mock Edit Panel (Mô phỏng Edit Toolbar)
- Dưới: Timeline Table
"""
import sys, os, json

base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_path)
bins_path = os.path.join(base_path, "bins")
if os.path.exists(bins_path):
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(bins_path)
    os.environ["PATH"] = bins_path + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSplitter, QGraphicsOpacityEffect, QTextEdit
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from qfluentwidgets import (
    SwitchButton, Slider, PrimaryPushButton,
    TableWidget, CheckBox, IconWidget, SmoothScrollArea,
    SegmentedWidget, Theme, setTheme, setThemeColor
)
from ui.theme import Colors
from ui.preview_widget import PreviewWidget
from core.config import APP_ROOT

# ── Data & State ──
GLOBAL_SETTINGS = {
    "brightness": 0,
    "flip_h": False
}

VIDEO_DIR = os.path.join(base_path, "video_test", "demo")
DEMO_VIDEOS = []

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.webm', '.mov')
if os.path.isdir(VIDEO_DIR):
    for f in sorted(os.listdir(VIDEO_DIR)):
        if f.lower().endswith(VIDEO_EXTENSIONS):
            fp = os.path.join(VIDEO_DIR, f)
            sz = os.path.getsize(fp) / (1024 * 1024)
            DEMO_VIDEOS.append({
                "name": f,
                "path": fp,
                "size": f"{sz:.1f} MB",
                "duration": "...",
                "scenes": [],
                "scene_done": False,
                "settings": {}  # Video-level overrides
            })

# ══════════════════════════════════════════════════
# Scene Detect Worker
# ══════════════════════════════════════════════════
class SceneDetectWorker(QThread):
    finished = pyqtSignal(str, list)
    error = pyqtSignal(str, str)

    def __init__(self, video_path, threshold=30.0, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.threshold = threshold

    def run(self):
        try:
            from scenedetect import VideoManager, SceneManager
            from scenedetect.detectors import ContentDetector
            vm = VideoManager([self.video_path])
            sm = SceneManager()
            sm.add_detector(ContentDetector(threshold=self.threshold))
            vm.start()
            sm.detect_scenes(frame_source=vm)
            raw_scenes = sm.get_scene_list()

            scenes = []
            for i, (start, end) in enumerate(raw_scenes):
                s_sec = start.get_seconds()
                e_sec = end.get_seconds()
                dur = e_sec - s_sec
                scenes.append({
                    "idx": i + 1,
                    "start_sec": s_sec,
                    "end_sec": e_sec,
                    "start": start.get_timecode(),
                    "end": end.get_timecode(),
                    "dur": f"{dur:.1f}s",
                    "settings": {}  # Scene-level overrides
                })
            self.finished.emit(self.video_path, scenes)
        except Exception as e:
            self.error.emit(self.video_path, str(e))

# ══════════════════════════════════════════════════
# Mock Edit Panel (Right)
# ══════════════════════════════════════════════════
class MockEditPanel(QWidget):
    setting_changed = pyqtSignal(str, object)
    mode_changed = pyqtSignal(bool) # True = Sync, False = Individual

    def __init__(self):
        super().__init__()
        self.setFixedWidth(300)
        self.setStyleSheet(f"background-color: {Colors.BG_PANEL}; border-left: 1px solid {Colors.BORDER_DIVIDER};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        title = QLabel("MÔ PHỎNG EDIT SETTINGS")
        title.setStyleSheet(f"color: {Colors.TEXT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(title)
        
        # Mode Toggle
        self.btn_sync = SwitchButton()
        self.btn_sync.setOnText("Chế độ: ĐỒNG BỘ 🔗")
        self.btn_sync.setOffText("Chế độ: RIÊNG LẺ 👤")
        self.btn_sync.setChecked(False) # Default Riêng lẻ
        self.btn_sync.checkedChanged.connect(self.mode_changed.emit)
        layout.addWidget(self.btn_sync)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER_DIVIDER};")
        layout.addWidget(sep)
        
        # Brightness Slider
        layout.addWidget(QLabel("Brightness:"))
        self.sl_brightness = Slider(Qt.Orientation.Horizontal)
        self.sl_brightness.setRange(-50, 50)
        self.sl_brightness.setValue(0)
        self.sl_brightness.valueChanged.connect(lambda v: self.setting_changed.emit("brightness", v))
        layout.addWidget(self.sl_brightness)
        
        # Flip Checkbox
        self.cb_flip = CheckBox("Lật ngang (Flip H)")
        self.cb_flip.stateChanged.connect(lambda v: self.setting_changed.emit("flip_h", v == 2))
        layout.addWidget(self.cb_flip)

        layout.addSpacing(10)
        
        # Info: Lưu vào đâu
        layout.addWidget(QLabel("Đang lưu cài đặt vào:"))
        self.te_target = QTextEdit()
        self.te_target.setReadOnly(True)
        self.te_target.setFixedHeight(40)
        self.te_target.setStyleSheet(f"background-color: {Colors.BG_DARK}; color: {Colors.ACCENT_LIGHT}; font-family: Consolas; font-size: 11px;")
        layout.addWidget(self.te_target)
        
        # Info: Final Settings
        layout.addWidget(QLabel("Final Resolved Settings (Áp dụng FFmpeg):"))
        self.te_json = QTextEdit()
        self.te_json.setReadOnly(True)
        self.te_json.setStyleSheet(f"background-color: {Colors.BG_DARK}; color: #aaa; font-family: Consolas; font-size: 11px;")
        layout.addWidget(self.te_json)
        
        layout.addStretch()
        
    def set_ui_values(self, settings):
        """Update slider/switch without triggering signals."""
        self.sl_brightness.blockSignals(True)
        self.cb_flip.blockSignals(True)
        
        self.sl_brightness.setValue(settings.get("brightness", 0))
        self.cb_flip.setChecked(settings.get("flip_h", False))
        
        self.sl_brightness.blockSignals(False)
        self.cb_flip.blockSignals(False)


# ══════════════════════════════════════════════════
# Scene Split Panel (Left)
# ══════════════════════════════════════════════════
class SceneSplitPanel(QWidget):
    detect_requested = pyqtSignal(bool)
    view_scenes_clicked = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._viewing_scenes = False
        self.setStyleSheet(f"background-color: {Colors.BG_PANEL};")
        self.setFixedWidth(380)
        self._init_ui()

    def _init_ui(self):
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("PHÂN CẢNH TỰ ĐỘNG")
        title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 600; background: transparent;")
        layout.addWidget(title)

        act_card = QFrame()
        act_card.setStyleSheet(f"background-color: {Colors.ACCENT_BG}; border: 1px solid {Colors.ACCENT_BORDER}; border-radius: 8px;")
        act_layout = QHBoxLayout(act_card)
        act_layout.setContentsMargins(15, 12, 15, 12)
        ico = IconWidget(str(APP_ROOT / "assets/icons/split.svg"))
        ico.setFixedSize(24, 24)
        act_layout.addWidget(ico)
        txt = QVBoxLayout(); txt.setSpacing(2)
        t = QLabel("KÍCH HOẠT SCENE DETECT"); t.setStyleSheet("font-weight: bold; font-size: 12px; color: white; background: transparent;")
        s = QLabel("Tự động phát hiện phân cảnh"); s.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY}; background: transparent;")
        txt.addWidget(t); txt.addWidget(s)
        act_layout.addLayout(txt); act_layout.addStretch()

        self._scene_switch = SwitchButton()
        self._scene_switch.setOnText(""); self._scene_switch.setOffText("")
        self._scene_switch.checkedChanged.connect(self._on_switch_toggled)
        act_layout.addWidget(self._scene_switch)
        layout.addWidget(act_card)

        self._content = QWidget()
        cl = QVBoxLayout(self._content); cl.setContentsMargins(0, 4, 0, 0); cl.setSpacing(12)

        th_header = QHBoxLayout()
        th_lbl = QLabel("THRESHOLD (ĐỘ NHẠY)"); th_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; background: transparent;")
        self._th_val = QLabel("30"); self._th_val.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-weight: bold; background: transparent;")
        th_header.addWidget(th_lbl); th_header.addStretch(); th_header.addWidget(self._th_val)
        cl.addLayout(th_header)

        self._th_slider = Slider(Qt.Orientation.Horizontal)
        self._th_slider.setRange(10, 80); self._th_slider.setValue(30)
        self._th_slider.valueChanged.connect(lambda v: self._th_val.setText(str(v)))
        cl.addWidget(self._th_slider)

        self._scene_info = QLabel("Chưa phát hiện cảnh nào")
        self._scene_info.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; background: transparent; padding: 4px 0;")
        cl.addWidget(self._scene_info)

        self._btn_view = PrimaryPushButton("👁  XEM PHÂN CẢNH")
        self._btn_view.setFixedHeight(44)
        self._btn_view.clicked.connect(self._on_view_clicked)
        cl.addWidget(self._btn_view)

        layout.addWidget(self._content)
        self._opacity = QGraphicsOpacityEffect(self._content)
        self._opacity.setOpacity(0.4)
        self._content.setGraphicsEffect(self._opacity)
        self._content.setEnabled(False)

        scroll.setWidget(container)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(scroll)

    @property
    def threshold(self): return float(self._th_slider.value())

    def set_scene_info(self, text): self._scene_info.setText(text)

    def _on_switch_toggled(self, checked):
        self._content.setEnabled(checked)
        self._opacity.setOpacity(1.0 if checked else 0.4)
        self.detect_requested.emit(checked)

    def _on_view_clicked(self):
        self._viewing_scenes = not self._viewing_scenes
        self._btn_view.setText("↩  TRỞ VỀ DANH SÁCH VIDEO" if self._viewing_scenes else "👁  XEM PHÂN CẢNH")
        self.view_scenes_clicked.emit(self._viewing_scenes)

    def reset_view_button(self):
        self._viewing_scenes = False
        self._btn_view.setText("👁  XEM PHÂN CẢNH")

# ══════════════════════════════════════════════════
# Timeline Table (Bottom)
# ══════════════════════════════════════════════════
class DemoTimeline(QWidget):
    video_selected = pyqtSignal(int)
    scene_clicked = pyqtSignal(int, float, float) # (row, start_sec, end_sec)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {Colors.BG_MICA};")
        self._selected_idx = 0
        self._viewing_scenes = False
        self._init_ui()
        self.show_video_list()

    def _init_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        header = QWidget(); header.setFixedHeight(40); header.setStyleSheet(f"background-color: {Colors.BG_MICA}; border-bottom: 1px solid {Colors.BORDER_DIVIDER};")
        h_layout = QHBoxLayout(header); h_layout.setContentsMargins(12, 0, 12, 0)
        self._header_lbl = QLabel("📁 Click video để xem preview + phân cảnh")
        self._header_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; font-weight: 500; background: transparent;")
        h_layout.addWidget(self._header_lbl); h_layout.addStretch()
        layout.addWidget(header)

        self._table = TableWidget(self)
        self._table.setBorderRadius(8)
        self._table.setBorderVisible(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.itemClicked.connect(self._on_click)
        layout.addWidget(self._table)

    def show_video_list(self):
        self._viewing_scenes = False
        self._header_lbl.setText("📁 Danh sách Video (Click để chọn)")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["", "#", "Filename", "Duration", "Size", "Scenes", "Status"])
        self._table.setRowCount(len(DEMO_VIDEOS))
        for i, v in enumerate(DEMO_VIDEOS):
            cb = CheckBox(); cb.setChecked(True)
            self._table.setCellWidget(i, 0, cb)
            self._table.setItem(i, 1, QTableWidgetItem(str(i + 1)))
            self._table.setItem(i, 2, QTableWidgetItem(v["name"]))
            self._table.setItem(i, 3, QTableWidgetItem(v["duration"]))
            self._table.setItem(i, 4, QTableWidgetItem(v["size"]))
            sc = len(v["scenes"])
            si = QTableWidgetItem(f"{sc} cảnh" if sc else "—")
            si.setForeground(QColor(Colors.ACCENT_LIGHT if sc else Colors.TEXT_TERTIARY))
            self._table.setItem(i, 5, si)
            st = QTableWidgetItem("✅ Detected" if v.get("scene_done") else "Ready")
            st.setForeground(QColor(Colors.SUCCESS))
            self._table.setItem(i, 6, st)

    def show_scenes(self, viewing: bool):
        self._viewing_scenes = viewing
        if not viewing:
            self.show_video_list()
            return
        video = DEMO_VIDEOS[self._selected_idx]
        scenes = video["scenes"]
        self._header_lbl.setText(f"🎬 Scenes: {video['name']} — {len(scenes)} cảnh")
        
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["", "#", "Scene", "Start → End", "Duration", "Status"])
        if not scenes:
            self._table.setRowCount(1)
            self._table.setItem(0, 2, QTableWidgetItem("Chưa phát hiện cảnh"))
            return
        self._table.setRowCount(len(scenes))
        for i, sc in enumerate(scenes):
            cb = CheckBox(); cb.setChecked(True)
            self._table.setCellWidget(i, 0, cb)
            self._table.setItem(i, 1, QTableWidgetItem(str(sc["idx"])))
            ni = QTableWidgetItem(f"Scene {sc['idx']}")
            ni.setForeground(QColor(Colors.ACCENT_LIGHT))
            self._table.setItem(i, 2, ni)
            self._table.setItem(i, 3, QTableWidgetItem(f"{sc['start']}  →  {sc['end']}"))
            self._table.setItem(i, 4, QTableWidgetItem(sc["dur"]))
            self._table.setItem(i, 5, QTableWidgetItem("Ready"))

    def _on_click(self, item):
        row = item.row()
        if self._viewing_scenes:
            video = DEMO_VIDEOS[self._selected_idx]
            scenes = video.get("scenes", [])
            if row < len(scenes):
                sc = scenes[row]
                self.scene_clicked.emit(row, sc["start_sec"], sc["end_sec"])
        else:
            if row < len(DEMO_VIDEOS):
                self._selected_idx = row
                self.video_selected.emit(row)

# ══════════════════════════════════════════════════
# Main Test Window
# ══════════════════════════════════════════════════
class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scene Split UI Test — 3-Tier Settings Demo")
        self.resize(1400, 850)
        self.setStyleSheet(f"background-color: {Colors.BG_MICA};")

        self.sync_mode = False
        self._current_video_idx = 0
        self._selected_scene_idx = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        
        top = QWidget()
        top_layout = QHBoxLayout(top); top_layout.setContentsMargins(0, 0, 0, 0)
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self._panel = SceneSplitPanel()
        self._preview = PreviewWidget()
        self._edit_panel = MockEditPanel()

        h_splitter.addWidget(self._panel)
        h_splitter.addWidget(self._preview)
        h_splitter.addWidget(self._edit_panel)
        h_splitter.setSizes([380, 720, 300])

        top_layout.addWidget(h_splitter)
        v_splitter.addWidget(top)

        self._timeline = DemoTimeline()
        v_splitter.addWidget(self._timeline)
        v_splitter.setSizes([550, 250])
        layout.addWidget(v_splitter)

        # Connect signals
        self._timeline.video_selected.connect(self._on_video_selected)
        self._timeline.scene_clicked.connect(self._on_scene_clicked)
        self._panel.detect_requested.connect(self._on_detect_toggled)
        self._panel.view_scenes_clicked.connect(self._on_view_scenes)
        self._edit_panel.mode_changed.connect(self._on_edit_mode_changed)
        self._edit_panel.setting_changed.connect(self._on_setting_changed)

        if DEMO_VIDEOS:
            self._load_video(0)
            self._refresh_edit_ui()

    # ── Edit Settings Logic (3-Tier) ──
    def _get_resolved_settings(self):
        """Merge settings: Global + Video + Scene."""
        merged = dict(GLOBAL_SETTINGS)
        target_str = "Global Settings (ĐỒNG BỘ)"
        
        if self._current_video_idx >= 0 and self._current_video_idx < len(DEMO_VIDEOS):
            vid = DEMO_VIDEOS[self._current_video_idx]
            if not self.sync_mode:
                merged.update(vid.get("settings", {}))
                target_str = f"Video: {vid['name']}\n(RIÊNG LẺ)"
                
                if self._timeline._viewing_scenes and self._selected_scene_idx >= 0:
                    scenes = vid.get("scenes", [])
                    if self._selected_scene_idx < len(scenes):
                        sc = scenes[self._selected_scene_idx]
                        merged.update(sc.get("settings", {}))
                        target_str = f"Video: {vid['name']} \n↳ Scene {sc['idx']} (RIÊNG LẺ)"
        return merged, target_str

    def _refresh_edit_ui(self):
        merged, target_str = self._get_resolved_settings()
        self._edit_panel.set_ui_values(merged)
        self._edit_panel.te_json.setText(json.dumps(merged, indent=2))
        self._edit_panel.te_target.setText(target_str)

    def _on_edit_mode_changed(self, is_sync):
        self.sync_mode = is_sync
        self._refresh_edit_ui()

    def _on_setting_changed(self, key, value):
        if self.sync_mode:
            # 1. Update Global
            GLOBAL_SETTINGS[key] = value
            # 2. Clear overrides in all videos and scenes to enforce sync
            for v in DEMO_VIDEOS:
                v.get("settings", {}).pop(key, None)
                for sc in v.get("scenes", []):
                    sc.get("settings", {}).pop(key, None)
        else:
            if self._current_video_idx >= 0 and self._current_video_idx < len(DEMO_VIDEOS):
                vid = DEMO_VIDEOS[self._current_video_idx]
                if self._timeline._viewing_scenes and self._selected_scene_idx >= 0:
                    # Update Scene Override
                    scenes = vid.get("scenes", [])
                    if self._selected_scene_idx < len(scenes):
                        scenes[self._selected_scene_idx].setdefault("settings", {})[key] = value
                else:
                    # Update Video Override
                    vid.setdefault("settings", {})[key] = value
                    
        self._refresh_edit_ui()

    # ── Timeline & Video Logic ──
    def _load_video(self, idx):
        if idx < len(DEMO_VIDEOS):
            self._current_video_idx = idx
            self._preview.load_video(DEMO_VIDEOS[idx]["path"])
            self._panel.reset_view_button()
            v = DEMO_VIDEOS[idx]
            self._panel.set_scene_info(f"✅ {len(v['scenes'])} cảnh đã phát hiện" if v["scene_done"] else "Chưa phát hiện cảnh nào")

    def _on_video_selected(self, idx):
        self._selected_scene_idx = -1
        self._load_video(idx)
        self._refresh_edit_ui()

    def _on_scene_clicked(self, row, start_sec, end_sec):
        self._selected_scene_idx = row
        try:
            self._preview.player.command('seek', str(start_sec), 'absolute')
            self._preview.player.pause = True
        except: pass
        self._refresh_edit_ui()

    def _on_view_scenes(self, viewing):
        self._selected_scene_idx = -1 # Reset selection
        self._timeline.show_scenes(viewing)
        self._refresh_edit_ui()

    def _on_detect_toggled(self, enabled):
        if enabled:
            idx = self._current_video_idx
            if idx >= len(DEMO_VIDEOS): return
            if DEMO_VIDEOS[idx]["scene_done"]: return
            self._panel.set_scene_info("⏳ Đang phân tích video...")
            self._detect_worker = SceneDetectWorker(DEMO_VIDEOS[idx]["path"], self._panel.threshold)
            self._detect_worker.finished.connect(lambda p, s: self._on_detect_done(idx, s))
            self._detect_worker.start()
        else:
            self._panel.set_scene_info("Scene detect đã tắt")

    def _on_detect_done(self, idx, scenes):
        DEMO_VIDEOS[idx]["scenes"] = scenes
        DEMO_VIDEOS[idx]["scene_done"] = True
        self._panel.set_scene_info(f"✅ Phát hiện {len(scenes)} cảnh thành công!")
        if not self._timeline._viewing_scenes:
            self._timeline.show_video_list()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    setTheme(Theme.DARK)
    setThemeColor('#7c3aed')
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
