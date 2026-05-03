"""
Main Window — Assembles all UI components into the final layout.
Layout matches the Next.js UI: Header | NavRail+EditPanel+Preview | RenderToolbar | Timeline
Windows 11 Fluent Design style.
"""
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFileDialog, QStackedWidget
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
from core.config import APP_ROOT
import time
import json
from qfluentwidgets import InfoBar, InfoBarPosition

from ui.header_bar import HeaderBar
from ui.nav_rail import NavRail
from ui.preview_widget import PreviewWidget
from ui.render_toolbar import RenderToolbar
from ui.timeline_widget import TimelineWidget
from ui.panels.auto_panel import AutoPanel
from ui.panels.custom_panel import CustomPanel
from ui.panels.template_panel import TemplatePanel
from batch.batch_processor import BatchProcessor
from batch.scene_detect_worker import SceneDetectWorker
from ui.theme import Colors


class MainWindow(QMainWindow):
    """Main application window — ToolHub Video Editor (Win11 Fluent Design)."""

    def __init__(self):
        super().__init__()
        self._batch_processor: BatchProcessor | None = None
        self._global_settings: dict = {}      # Tier 1: Global (template/default)
        self._current_settings: dict = {}      # Resolved cache (read-only mirror)
        self._current_video_path: str = ""
        self._selected_scene_idx: int = -1     # -1 = no scene selected
        self._scene_detect_worker = None

        self.setWindowTitle("ToolHub — Video Editor Pro")
        self.setMinimumSize(1280, 720)
        self.resize(1800, 1000)
        self._center_on_screen()
        
        self.setWindowIcon(QIcon(str(APP_ROOT / "assets/logo.png")))
        self.setStyleSheet(f"background-color: {Colors.BG_MICA};")

        self._init_ui()
        self._connect_signals()

        # Force sync the UI panel with the currently selected nav tab
        # (Fixes issue where QStackedWidget defaults to index 0 / AutoPanel)
        active_id = self._nav_rail._btn_group.checkedId()
        if active_id >= 0:
            self._on_tab_changed(active_id)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ═══ 1. HEADER BAR ═══
        self._header = HeaderBar()
        root.addWidget(self._header)

        # ═══ 2. MAIN CONTENT (vertical splitter: workspace | bottom area) ═══
        self._v_splitter = QSplitter(Qt.Orientation.Vertical)
        self._v_splitter.setHandleWidth(1)
        self._v_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BORDER_DIVIDER};
            }}
            QSplitter::handle:hover {{
                background-color: {Colors.ACCENT};
            }}
        """)

        # ──── 2a. TOP WORKSPACE (NavRail + EditPanel + Preview) ────
        top_workspace = QWidget()
        top_layout = QHBoxLayout(top_workspace)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        # Nav Rail (72px fixed)
        self._nav_rail = NavRail()
        top_layout.addWidget(self._nav_rail)

        # Horizontal splitter: Edit Panel | Preview
        self._h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._h_splitter.setHandleWidth(1)
        self._h_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BORDER_DIVIDER};
            }}
            QSplitter::handle:hover {{
                background-color: {Colors.ACCENT};
            }}
        """)

        # Edit Panel (stacked — switches based on nav rail tab)
        self._panel_stack = QStackedWidget()
        self._panel_stack.setMinimumWidth(435)
        self._panel_stack.setMaximumWidth(600)
        self._panel_stack.setStyleSheet(f"background-color: {Colors.BG_PANEL};")

        self._auto_panel = AutoPanel()
        self._custom_panel = CustomPanel()
        self._template_panel = TemplatePanel()

        # Stack order must match NavRail tab indices:
        # 0=Auto, 1=Custom, 2=Media→Custom, 3=Text→Custom, 4=Audio→Custom, 5=Templates
        self._panel_stack.addWidget(self._auto_panel)    # index 0
        self._panel_stack.addWidget(self._custom_panel)  # index 1
        self._panel_stack.addWidget(self._template_panel)  # index 2

        self._h_splitter.addWidget(self._panel_stack)

        # Preview Widget (expanding)
        self._preview = PreviewWidget()
        self._h_splitter.addWidget(self._preview)

        self._h_splitter.setStretchFactor(0, 0)  # Edit panel: no auto-stretch
        self._h_splitter.setStretchFactor(1, 1)  # Preview: takes all remaining space
        self._h_splitter.setSizes([350, 800])

        top_layout.addWidget(self._h_splitter)

        self._v_splitter.addWidget(top_workspace)

        # ──── 2b. BOTTOM AREA (RenderToolbar + Timeline) ────
        bottom_area = QWidget()
        bottom_layout = QVBoxLayout(bottom_area)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        # Render Toolbar (full width)
        self._render_toolbar = RenderToolbar()
        bottom_layout.addWidget(self._render_toolbar)

        # Timeline (full width)
        self._timeline = TimelineWidget()
        bottom_layout.addWidget(self._timeline)

        self._v_splitter.addWidget(bottom_area)

        # Splitter proportions: top=75%, bottom=25%
        self._v_splitter.setStretchFactor(0, 3)
        self._v_splitter.setStretchFactor(1, 1)
        self._v_splitter.setSizes([600, 200])

        root.addWidget(self._v_splitter)

    def _connect_signals(self):
        # Nav Rail → Switch panel
        self._nav_rail.tab_changed.connect(self._on_tab_changed)

        # Timeline → Video selected → Preview
        self._timeline.video_selected.connect(self._on_video_selected)
        self._timeline.scene_clicked.connect(self._on_scene_clicked)
        # self._timeline.folder_loaded.connect(self._on_folder_loaded)
        self._timeline.files_changed.connect(self._render_toolbar.set_file_count)

        # Render toolbar → Output folder changed
        self._render_toolbar.clear_clicked.connect(self._timeline.clear_all)
        self._render_toolbar.edit_mode_changed.connect(self._on_edit_mode_changed)

        # Edit panels → Settings changed → Preview
        self._auto_panel.settings_changed.connect(self._on_auto_settings_changed)
        self._custom_panel.settings_changed.connect(self._on_custom_settings_changed)

        # Template panel → Load template → Custom panel
        self._template_panel.template_loaded.connect(self._on_template_loaded)

        # Render toolbar → Start/Stop batch
        self._render_toolbar.check_clicked.connect(self._check_batch_settings)
        self._render_toolbar.render_clicked.connect(self._start_batch)
        self._render_toolbar.stop_clicked.connect(self._cancel_batch)

        # Crop mode: Panel toggle → Preview overlay; Preview overlay → Panel info
        self._custom_panel.crop_mode_requested.connect(self._on_crop_mode_requested)
        self._custom_panel.crop_apply_clicked.connect(self._on_crop_apply)
        self._custom_panel.crop_reset_clicked.connect(self._on_crop_reset)
        self._preview.crop_box_changed.connect(self._on_crop_box_from_overlay)

        # Zoom mode
        self._custom_panel.zoom_mode_requested.connect(self._on_zoom_mode_requested)
        self._custom_panel.zoom_apply_clicked.connect(self._on_zoom_apply)
        self._custom_panel.zoom_reset_clicked.connect(self._on_zoom_reset)
        self._preview.zoom_box_changed.connect(self._on_zoom_box_from_overlay)

        # Scene Split
        self._custom_panel.view_scenes_clicked.connect(self._on_view_scenes_clicked)

        # Initialize global settings from CustomPanel defaults
        self._global_settings = self._custom_panel.get_settings()
        self._current_settings = dict(self._global_settings)

    # ═══════════════════════════════════════════════════════════
    #  3-Tier Settings Helpers
    # ═══════════════════════════════════════════════════════════

    def _get_selected_file_info(self):
        """Get the file_info dict for the currently selected video."""
        if not self._current_video_path:
            return None
        for f in self._timeline.all_files:
            if f['path'] == self._current_video_path:
                return f
        return None

    def _get_selected_scene(self):
        """Get the scene dict for the currently selected scene."""
        fi = self._get_selected_file_info()
        if fi and self._selected_scene_idx >= 0:
            scenes = fi.get('scenes', [])
            if self._selected_scene_idx < len(scenes):
                return scenes[self._selected_scene_idx]
        return None

    def _refresh_resolved_settings(self):
        """Recompute _current_settings from the 3-tier hierarchy."""
        resolved = dict(self._global_settings)
        if not self._render_toolbar.is_sync_mode:
            fi = self._get_selected_file_info()
            if fi:
                resolved.update(fi.get('settings_override', {}))
                if self._selected_scene_idx >= 0:
                    scenes = fi.get('scenes', [])
                    if self._selected_scene_idx < len(scenes):
                        resolved.update(scenes[self._selected_scene_idx].get('settings_override', {}))
        self._current_settings = resolved

    def _save_settings_to_tier(self, new_settings: dict):
        """Route settings to the correct tier based on edit mode and selection."""
        if self._render_toolbar.is_sync_mode:
            # Sync mode: save to global, clear overrides for changed keys
            changed_keys = [k for k, v in new_settings.items()
                            if v != self._global_settings.get(k)]
            self._global_settings.update(new_settings)
            if changed_keys:
                for f in self._timeline.all_files:
                    ovr = f.get('settings_override', {})
                    for k in changed_keys:
                        ovr.pop(k, None)
                    for sc in f.get('scenes', []):
                        sc_ovr = sc.get('settings_override', {})
                        for k in changed_keys:
                            sc_ovr.pop(k, None)
        else:
            # Individual mode
            sc = self._get_selected_scene()
            fi = self._get_selected_file_info()
            if sc is not None and self._selected_scene_idx >= 0:
                # Diff from (global + video override)
                base = dict(self._global_settings)
                if fi:
                    base.update(fi.get('settings_override', {}))
                sc['settings_override'] = {
                    k: v for k, v in new_settings.items() if v != base.get(k)
                }
            elif fi is not None:
                # Diff from global
                fi['settings_override'] = {
                    k: v for k, v in new_settings.items()
                    if v != self._global_settings.get(k)
                }

    def _write_key_to_tier(self, key: str, value):
        """Write a single key to the correct tier (used by crop/zoom overlay)."""
        if self._render_toolbar.is_sync_mode:
            self._global_settings[key] = value
        else:
            sc = self._get_selected_scene()
            fi = self._get_selected_file_info()
            if sc is not None and self._selected_scene_idx >= 0:
                sc.setdefault('settings_override', {})[key] = value
            elif fi is not None:
                fi.setdefault('settings_override', {})[key] = value
            else:
                self._global_settings[key] = value
        self._refresh_resolved_settings()

    # ═══════════════════════════════════════════════════════════
    #  Signal handlers
    # ═══════════════════════════════════════════════════════════

    def _on_tab_changed(self, index: int):
        """Switch the edit panel based on Nav Rail tab selection."""
        if index == 0:
            self._panel_stack.setCurrentIndex(0)
        elif index in (1, 2, 3, 4):
            self._panel_stack.setCurrentIndex(1)
            redirect_map = {2: "logo", 3: "watermark", 4: "audio"}
            if index in redirect_map:
                self._custom_panel.select_tool(redirect_map[index])
        elif index == 5:
            self._template_panel.set_current_settings(self._current_settings)
            self._panel_stack.setCurrentIndex(2)

    def _on_edit_mode_changed(self, is_sync: bool):
        """Edit mode toggled between Sync and Individual."""
        self._refresh_resolved_settings()
        self._custom_panel.load_settings(self._current_settings)
        self._preview.update_settings(self._current_settings)

    def _on_video_selected(self, path: str):
        """Load selected video into preview."""
        self._current_video_path = path
        self._selected_scene_idx = -1  # Reset scene selection
        self._preview.load_video(path)

        # Resolve and load settings for this video
        self._refresh_resolved_settings()
        
        print(f"\n[DEBUG] --- CHỌN VIDEO: {os.path.basename(path)} ---")
        fi = self._get_selected_file_info()
        print(f"   + Global Settings: {json.dumps(self._global_settings, indent=2, ensure_ascii=False)}")
        if fi:
            print(f"   + Video Overrides: {json.dumps(fi.get('settings_override', {}), indent=2, ensure_ascii=False)}")
        print(f"   => Resolved Settings (Final UI State): {json.dumps(self._current_settings, indent=2, ensure_ascii=False)}")

        if not self._render_toolbar.is_sync_mode:
            self._custom_panel.load_settings(self._current_settings)
        self._preview.update_settings(self._current_settings)

        # Check if already has scenes
        for f in self._timeline.all_files:
            if f['path'] == path:
                if f.get('scene_done'):
                    scenes = f.get('scenes', [])
                    self._custom_panel.set_scene_info(f"✅ Đã phát hiện {len(scenes)} cảnh")
                else:
                    self._custom_panel.set_scene_info("Chưa phát hiện cảnh nào")
                break

    def _on_scene_clicked(self, path: str, scene_index: int, start_sec: float, end_sec: float):
        """Seek video to the start of the clicked scene."""
        if self._current_video_path != path:
            self._current_video_path = path
            self._preview.load_video(path)
        self._selected_scene_idx = scene_index
        self._preview.seek_to(start_sec)

        # Resolve and load settings for this scene
        self._refresh_resolved_settings()
        
        print(f"\n[DEBUG] --- CHỌN SCENE {scene_index + 1} của {os.path.basename(path)} ---")
        fi = self._get_selected_file_info()
        sc = self._get_selected_scene()
        print(f"   + Global Settings: {json.dumps(self._global_settings, indent=2, ensure_ascii=False)}")
        if fi:
            print(f"   + Video Overrides: {json.dumps(fi.get('settings_override', {}), indent=2, ensure_ascii=False)}")
        if sc:
            print(f"   + Scene Overrides: {json.dumps(sc.get('settings_override', {}), indent=2, ensure_ascii=False)}")
        print(f"   => Resolved Settings (Final UI State): {json.dumps(self._current_settings, indent=2, ensure_ascii=False)}")

        if not self._render_toolbar.is_sync_mode:
            self._custom_panel.load_settings(self._current_settings)
        self._preview.update_settings(self._current_settings)

    def _on_folder_loaded(self, path: str, count: int):
        """Folder loaded in timeline — update render toolbar."""
        self._render_toolbar.set_folder(path)

    def _on_auto_settings_changed(self, auto_settings: dict):
        """Merge auto filter settings into global settings."""
        self._global_settings.update(auto_settings)
        self._refresh_resolved_settings()
        self._preview.update_settings(self._current_settings)

    def _on_custom_settings_changed(self, custom_settings: dict):
        """Route custom tool settings to the correct tier."""
        self._save_settings_to_tier(custom_settings)
        self._refresh_resolved_settings()
        
        print("\n[DEBUG] --- LƯU EDIT SETTING (Confirm) ---")
        print(f"   Chế độ: {'ĐỒNG BỘ' if self._render_toolbar.is_sync_mode else 'RIÊNG LẺ'}")
        print(f"   Dữ liệu nhận được: {json.dumps(custom_settings, indent=2, ensure_ascii=False)}")
        if self._render_toolbar.is_sync_mode:
            print(f"   => Đã lưu vào Global Settings.")
        else:
            if self._selected_scene_idx >= 0:
                print(f"   => Đã lưu vào Scene {self._selected_scene_idx + 1} Override.")
            else:
                print(f"   => Đã lưu vào Video Override.")

        # If in interactive crop mode, update the overlay ratio immediately
        if self._preview.is_crop_mode():
            ratio_val = custom_settings.get("crop_ratio", "original")
            ar = None
            if ratio_val and ratio_val != "original":
                try:
                    w, h = map(int, ratio_val.split(":"))
                    ar = w / h
                except Exception:
                    pass
            self._preview.set_crop_aspect_ratio(ar)

        self._preview.update_settings(self._current_settings)

    def _on_template_loaded(self, settings: dict):
        """Template loaded — set as new global baseline, clear all overrides."""
        self._global_settings = settings.copy()
        # Clear all per-video and per-scene overrides
        for f in self._timeline.all_files:
            f['settings_override'] = {}
            for sc in f.get('scenes', []):
                sc['settings_override'] = {}
        self._refresh_resolved_settings()
        self._auto_panel.load_settings(self._current_settings)
        self._custom_panel.load_settings(self._current_settings)
        self._preview.update_settings(self._current_settings)
        self._nav_rail.set_tab(1)

    def _on_crop_mode_requested(self, enter: bool):
        """Toggle interactive crop overlay on the preview."""
        if enter:
            # Determine aspect ratio from currently selected crop ratio button
            checked = self._custom_panel._crop_group.checkedButton()
            ratio_val = checked.property("ratio_value") if checked else "original"
            ar = None
            if ratio_val and ratio_val != "original":
                try:
                    w, h = map(int, ratio_val.split(":"))
                    ar = w / h
                except Exception:
                    pass
            # Use existing crop_box if set, or default
            existing = self._current_settings.get("crop_box")
            self._preview.enter_crop_mode(initial_box=existing, aspect_ratio=ar)
        else:
            self._preview.exit_crop_mode(apply=False)

    def _on_crop_apply(self):
        """Finalize the crop on the preview widget."""
        self._preview.exit_crop_mode(apply=True)

    def _on_crop_reset(self):
        """Reset the crop on the preview widget."""
        self._write_key_to_tier("crop_box", None)
        self._preview.reset_crop()

    def _on_crop_box_from_overlay(self, box: dict):
        """Receive crop box from the interactive overlay and update panel."""
        self._custom_panel.update_crop_box(box)

    def _on_zoom_mode_requested(self, enter: bool):
        if enter:
            existing = self._current_settings.get("zoom_box")
            self._preview.enter_zoom_mode(initial_box=existing)
        else:
            self._preview.exit_zoom_mode(apply=False)

    def _on_zoom_apply(self):
        self._preview.exit_zoom_mode(apply=True)

    def _on_zoom_reset(self):
        self._write_key_to_tier("zoom_box", None)
        self._preview.reset_zoom()

    def _on_zoom_box_from_overlay(self, info: str, box: dict):
        """Receive info and box from overlay and update panel."""
        self._custom_panel.update_zoom_box(info, box)

    # ═══════════════════════════════════════════════════════════
    #  Scene Detection Handlers
    # ═══════════════════════════════════════════════════════════

    def _on_scene_detect_finished(self, video_path: str, scenes: list):
        self._custom_panel.set_scene_info(f"✅ Phát hiện {len(scenes)} cảnh thành công!")
        self._custom_panel._viewing_scenes = True
        self._custom_panel.set_detecting_state(False)
        self._timeline.update_scenes(video_path, scenes)
        if self._custom_panel._viewing_scenes:
            self._timeline.show_scenes(self._current_video_path, True)
            
    def _on_scene_detect_error(self, video_path: str, err: str):
        self._custom_panel.set_scene_info(f"❌ Lỗi: {err[:20]}...")
        self._custom_panel.set_detecting_state(False)
        InfoBar.error(
            title="Lỗi Scene Detect",
            content=str(err),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def _on_view_scenes_clicked(self, viewing: bool):
        if not self._current_video_path:
            self._custom_panel.set_scene_info("Vui lòng chọn video trước")
            self._custom_panel._viewing_scenes = False
            self._custom_panel.set_detecting_state(False)
            return

        if viewing:
            # Check if already processed
            for f in self._timeline.all_files:
                if f['path'] == self._current_video_path and f.get('scene_done'):
                    self._custom_panel._viewing_scenes = True
                    self._custom_panel.set_detecting_state(False)
                    self._timeline.show_scenes(self._current_video_path, True)
                    return

            # Not processed yet, start detection
            threshold = float(self._global_settings.get("scene_split_threshold", 30))
            self._custom_panel.set_scene_info("⏳ Đang phân tích video (vui lòng chờ)...")
            self._custom_panel.set_detecting_state(True)
            
            self._scene_detect_worker = SceneDetectWorker(self._current_video_path, threshold)
            self._scene_detect_worker.finished.connect(self._on_scene_detect_finished)
            self._scene_detect_worker.error.connect(self._on_scene_detect_error)
            self._scene_detect_worker.start()
        else:
            self._timeline.show_scenes(self._current_video_path, False)

    # ═══════════════════════════════════════════════════════════
    #  Batch processing
    # ═══════════════════════════════════════════════════════════

    def _start_batch(self):
        selected_files = self._timeline.files
        if not selected_files:
            return
        print(f"[DEBUG] Selected files: {json.dumps(selected_files, indent=2)}")

        # 1. AUTO-CHECK: Run validation first
        self._check_batch_settings(silent=True)
        
        # Check if any selected file has "error" status in timeline
        has_errors = False
        for f in selected_files:
            if f.get('status') == 'error':
                has_errors = True
                break
        
        if has_errors:
            InfoBar.error(
                title="Không thể bắt đầu",
                content="Có video bị lỗi cấu hình (màu đỏ). Vui lòng kiểm tra lại trước khi Start.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            return

        # Get output folder from toolbar
        save_path = self._render_toolbar.save_path
        if not save_path:
            InfoBar.error(
                title="Lỗi",
                content="Vui lòng chọn thư mục lưu trữ trước khi nhấn Apply Edit!",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return

        # ═══════════════════════════════════════════════════════════
        # CHUẨN BỊ DATA (DATA PREPARATION)
        # ═══════════════════════════════════════════════════════════
        output_height = self._render_toolbar.output_height
        batch_tasks = []
        
        print("\n[DEBUG] 🚀 --- BẮT ĐẦU RENDER BATCH ---")
        
        for f in selected_files:
            # 1. Gộp Global Settings và Video Override
            video_settings = dict(self._global_settings)
            video_settings.update(f.get('settings_override', {}))
            if output_height:
                video_settings["output_height"] = output_height
            
            # Khởi tạo Task cho Video
            task = {
                "file_info": f,
                "settings": video_settings,
                "scenes": []
            }

            # 2. Xử lý Scene (nếu có)
            if f.get('scene_done'):
                for sc in f.get('scenes', []):
                    if not sc.get('checked', True):
                        continue
                    
                    # Gộp Setting của Video và Scene Override
                    scene_settings = dict(video_settings)
                    scene_settings.update(sc.get('settings_override', {}))
                    
                    task["scenes"].append({
                        "scene_data": sc,
                        "settings": scene_settings
                    })
                    
            batch_tasks.append(task)
            
            # Print debug
            print(f"   📺 Video Task: {f['name']}")
            print(f"      - Video Settings keys: {len(task['settings'])}")
            if task["scenes"]:
                print(f"      - Tổng số cảnh sẽ xử lý: {len(task['scenes'])}")

        total = len(selected_files)
        self._batch_start_time = time.perf_counter() # Start timer
        
        # Cập nhật UI sang trạng thái 'doing'
        for f in selected_files:
            self._timeline.update_file_status(f['path'], "doing", "Đang chờ xử lý...")
        self._render_toolbar.set_progress(0, total)

        # Create batch processor (Tạm thời vẫn truyền file gốc và batch_tasks, ta sẽ sửa file kia sau)
        self._batch_processor = BatchProcessor(
            files=selected_files,
            batch_tasks=batch_tasks,  # Data mới chuẩn bị
            save_path=save_path,
            output_format=self._render_toolbar.output_format,
            settings=self._global_settings, # Giữ tạm để code cũ không lỗi
            max_workers=self._render_toolbar.workers,
            delete_original=self._render_toolbar.delete_original,
            use_gpu=self._render_toolbar.use_gpu,
        )

        # Connect batch signals
        bp = self._batch_processor
        bp.signals.file_done.connect(
            lambda path, status, done_count, msg: [
                self._timeline.update_file_status(path, status, msg),
                self._render_toolbar.set_progress(done_count, total)
            ]
        )
        # Show notification on completion/error
        def _on_completed(t, c, s):
            elapsed_ms = (time.perf_counter() - self._batch_start_time) * 1000
            self._render_toolbar.reset_processing(self._timeline.file_count, self._timeline.selected_count)
            
            # Update Timeline Session Info
            errors = t - c - s
            self._timeline.set_session_info(t, c, errors, s, elapsed_ms)
            
            InfoBar.success(
                title="Hoàn thành",
                content=f"Đã xử lý xong {c}/{t} video. (Bỏ qua {s})",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )

        def _on_error(msg):
            self._render_toolbar.reset_processing(self._timeline.file_count, self._timeline.selected_count)
            InfoBar.error(
                title="Lỗi xử lý",
                content=msg,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=0,
                parent=self
            )

        bp.signals.completed.connect(_on_completed)
        bp.signals.error.connect(_on_error)
        bp.signals.cancelled.connect(
            lambda: self._render_toolbar.reset_processing(self._timeline.file_count, self._timeline.selected_count)
        )

        bp.start()

    def _check_batch_settings(self, silent=False):
        """Validate current edit settings against all selected files."""
        selected_files = self._timeline.files
        if not selected_files:
            return

        # Use global settings for validation base
        settings = dict(self._global_settings)

        # Reset UI statuses
        self._timeline.reset_all_statuses()

        for f in selected_files:
            path = f['path']
            info = f.get('raw_info')
            
            if not info:
                self._timeline.update_file_status(path, "error", "Chưa có thông tin video (đang quét...)")
                continue

            v_w = info.get('width', 0)
            v_h = info.get('height', 0)
            v_dur = info.get('duration', 0)
            
            # Inject dimensions for core validation
            settings['_video_width'] = v_w
            settings['_video_height'] = v_h

            errors = []
            warnings = []

            # 1. Validate Crop
            crop_box = settings.get("crop_box")
            if crop_box:
                # crop_box format: {'x':, 'y':, 'w':, 'h':} in pixel values relative to preview
                # However, settings usually stores normalized or absolute pixels if we updated it correctly.
                # Let's assume absolute pixels for now as per custom_panel logic
                cx, cy = crop_box.get('x', 0), crop_box.get('y', 0)
                cw, ch = crop_box.get('w', 0), crop_box.get('h', 0)
                
                if cx < 0 or cy < 0 or (cx + cw) > v_w or (cy + ch) > v_h:
                    errors.append(f"Vùng Crop ({cw}x{ch}) vượt quá kích thước video ({v_w}x{v_h})")

            # 2. Validate Trim & Split
            trim_enabled = settings.get("trimmer_enabled", False)
            t_start = float(settings.get("trimmer_start", 0)) if trim_enabled else 0
            t_end = float(settings.get("trimmer_end", 0)) if trim_enabled else 0
            
            # Check Trim
            if trim_enabled:
                total_to_cut = t_start + t_end
                if total_to_cut >= v_dur:
                    errors.append(f"Trim: Tổng thời gian cắt ({total_to_cut}s) >= độ dài video ({v_dur:.1f}s)")
                elif t_start >= v_dur:
                    errors.append(f"Trim: Điểm cắt đầu ({t_start}s) vượt quá độ dài video")

            # Available duration for Split
            v_dur_avail = max(0, v_dur - (t_start + t_end))

            # Check Split
            split_enabled = settings.get("split_enabled", False)
            if split_enabled:
                s_count = int(settings.get("split_count", 0))
                s_min = float(settings.get("trim_start", 5)) # CustomPanel uses trim_start for split min
                s_max = float(settings.get("trim_end", 30))  # CustomPanel uses trim_end for split max

                if s_min > s_max:
                    errors.append(f"Split: Độ dài Min ({s_min}s) không được lớn hơn Max ({s_max}s)")
                
                if v_dur_avail <= 0:
                    errors.append("Split: Không còn thời lượng để cắt (do đã Trim hết video)")
                elif s_min > v_dur_avail:
                    errors.append(f"Split: Độ dài Min ({s_min}s) lớn hơn thời lượng khả dụng ({v_dur_avail:.1f}s)")
                elif s_count > 0:
                    min_needed = s_count * s_min
                    max_possible = s_count * s_max
                    if min_needed > v_dur_avail:
                        errors.append(f"Split: Cần ít nhất {min_needed}s để cắt {s_count} phần, nhưng chỉ còn {v_dur_avail:.1f}s")
                    elif v_dur_avail > max_possible:
                        errors.append(f"Split: Video quá dài ({v_dur_avail:.1f}s) để chia làm {s_count} phần tối đa {s_max}s")

            # 3. Validate Logo / Watermark
            logo_path = settings.get("logo_path")
            if logo_path and not os.path.exists(logo_path):
                errors.append("File Logo không tồn tại")

            watermark_path = settings.get("watermark_path")
            if watermark_path and not os.path.exists(watermark_path):
                errors.append("File Watermark không tồn tại")

            # Update UI
            if errors:
                f['status'] = 'error' # Mark for _start_batch check
                self._timeline.update_file_status(path, "error", " | ".join(errors))
            elif warnings:
                f['status'] = 'ready' # Warnings don't block
                self._timeline.update_file_status(path, "skipped", " | ".join(warnings)) 
            else:
                f['status'] = 'ready'
                self._timeline.update_file_status(path, "ready", "Cấu hình hợp lệ")

        if not silent:
            InfoBar.success(
            title="Kiểm tra xong",
            content=f"Đã kiểm tra {len(selected_files)} video. Vui lòng xem cột Message.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def _cancel_batch(self):
        if self._batch_processor:
            self._batch_processor.cancel()

    def _center_on_screen(self):
        """Center the main window on the current screen."""
        frame_gm = self.frameGeometry()
        screen_center = self.screen().availableGeometry().center()
        frame_gm.moveCenter(screen_center)
        self.move(frame_gm.topLeft())
