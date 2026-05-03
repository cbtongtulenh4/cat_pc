import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QTableWidgetItem, QHeaderView, QAbstractItemView, QSplitter
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    PrimaryPushButton, PushButton, TableWidget, CheckBox, 
    FluentIcon as FIF, ToolButton
)

from ui.theme import Colors
from batch.probe_worker import ProbeWorker

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.wmv', '.m4v', '.3gp')


class TimelineWidget(QWidget):
    """
    Timeline panel — List of videos in a Table.
    Supports Batch processing workflow: multi-select, recursive import, background info probing.
    """

    video_selected = pyqtSignal(str)       # file path
    files_changed = pyqtSignal(int, int)   # total_count, selected_count
    folder_loaded = pyqtSignal(str, int)   # for compatibility: root_folder, count
    scene_clicked = pyqtSignal(str, int, float, float) # path, scene_index, start_sec, end_sec

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[dict] = []  # List of {path, name, rel_dir, size, duration, status, checked}
        self._probe_worker: ProbeWorker = None
        self._current_scene_path: str = ""
        
        self.setStyleSheet(f"background-color: {Colors.BG_MICA};")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Header (Tabs)
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet(f"""
            background-color: {Colors.BG_MICA};
            border-bottom: 1px solid {Colors.BORDER_DIVIDER};
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 12, 0)
        
        self._lbl_session_info = QLabel("Những video dưới đây cần được tick chọn để xử lý")
        self._lbl_session_info.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 13px;
            font-weight: 500;
            background: transparent;
        """)
        h_layout.addWidget(self._lbl_session_info)

        h_layout.addStretch()
        layout.addWidget(header)

        # 2. Table Area
        self._content_splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(self._content_splitter)

        self._table = TableWidget(self)
        self._table.setColumnCount(10)
        self._table.setHorizontalHeaderLabels([
            "", "#", "Filename", "Sub-folder", "Message", "Size", "Duration", "Scenes", "Status", "Action"
        ])
        
        # Table styling
        self._table.setBorderRadius(8)
        self._table.setBorderVisible(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Column width behavior
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 40)
        self._table.setColumnWidth(1, 40)
        self._table.setColumnWidth(5, 100)
        self._table.setColumnWidth(6, 80)
        self._table.setColumnWidth(7, 80)
        self._table.setColumnWidth(8, 100)
        self._table.setColumnWidth(9, 80)

        self._table.itemClicked.connect(self._on_item_clicked)
        self._content_splitter.addWidget(self._table)

        # 2.5 Scene Table
        self._scene_table = TableWidget(self)
        self._scene_table.setColumnCount(8)
        self._scene_table.setHorizontalHeaderLabels([
            "", "#", "Filename", "Scene", "Start", "End", "Duration", "Action"
        ])
        self._scene_table.setBorderRadius(8)
        self._scene_table.setBorderVisible(True)
        self._scene_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._scene_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._scene_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        s_header = self._scene_table.horizontalHeader()
        s_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        s_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        s_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._scene_table.setColumnWidth(0, 40)
        self._scene_table.setColumnWidth(1, 40)
        self._scene_table.setColumnWidth(3, 80)
        self._scene_table.setColumnWidth(4, 100)
        self._scene_table.setColumnWidth(5, 100)
        self._scene_table.setColumnWidth(6, 100)
        self._scene_table.setColumnWidth(7, 80)
        
        self._scene_table.itemClicked.connect(self._on_scene_item_clicked)
        self._content_splitter.addWidget(self._scene_table)
        self._scene_table.setVisible(False)

        # 3. Empty State (Import Area)
        self._import_area = QWidget()
        import_layout = QHBoxLayout(self._import_area)
        import_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        import_layout.setSpacing(16)

        btn_dir = PrimaryPushButton(FIF.FOLDER_ADD.icon(), "  Import Video Directory")
        btn_dir.setFixedHeight(44)
        btn_dir.setFixedWidth(250)
        btn_dir.clicked.connect(self._import_directory)
        import_layout.addWidget(btn_dir)

        btn_single = PushButton(FIF.DOCUMENT.icon(), "  Import Video File(s)")
        btn_single.setFixedHeight(44)
        btn_single.setFixedWidth(250)
        btn_single.clicked.connect(self._import_single)
        import_layout.addWidget(btn_single)

        layout.addWidget(self._import_area)
        self._import_area.setVisible(True)
        self._content_splitter.setVisible(False)

    @property
    def files(self) -> list[dict]:
        """Return list of checked files only."""
        return [f for f in self._files if f.get('checked', True)]

    @property
    def all_files(self) -> list[dict]:
        return self._files

    @property
    def folder_path(self) -> str:
        """Return the root path of the first file or common parent."""
        if not self._files:
            return ""
        return os.path.dirname(self._files[0]['path'])

    @property
    def file_count(self) -> int:
        return len(self._files)

    @property
    def selected_count(self) -> int:
        return len([f for f in self._files if f.get('checked', True)])

    def clear_all(self):
        """Empty the timeline."""
        self._files.clear()
        if self._probe_worker:
            self._probe_worker.cancel()
            self._probe_worker = None
        self._refresh_table()

    def update_file_status(self, path: str, status: str, message: str = ""):
        """Update file status in the table (e.g., '35%', 'done', 'error', 'skip')."""
        for i, f in enumerate(self._files):
            if f['path'] == path:
                f['status'] = status
                if message:
                    f['message'] = message
                
                # Update table item directly
                item_status = self._table.item(i, 8)
                item_msg = self._table.item(i, 4)
                
                if item_status:
                    # Map common status to display text
                    display_text = status.capitalize()
                    if status == "done":
                        display_text = "Done"
                    elif status == "skipped":
                        display_text = "Skip"
                    elif status == "error":
                        display_text = "Error"
                    elif status == "doing":
                        display_text = "Doing..."
                    elif "%" in status or status == "processing":
                        display_text = status
                        
                    item_status.setText(display_text)
                    
                    # Color coding
                    if status == "done":
                        item_status.setForeground(QColor(Colors.SUCCESS))
                    elif status == "error":
                        item_status.setForeground(QColor(Colors.ERROR))
                    elif status == "skipped" or status == "skip":
                        item_status.setForeground(QColor(Colors.WARNING))
                    elif "%" in status or status == "processing" or status == "doing":
                        item_status.setForeground(QColor(Colors.ACCENT_LIGHT))
                    elif status == "ready":
                        item_status.setForeground(QColor(Colors.TEXT))
                
                if item_msg and message:
                    item_msg.setText(message)
                    if status == "error":
                        item_msg.setForeground(QColor(Colors.ERROR))
                    elif status == "skipped" or status == "skip":
                        item_msg.setForeground(QColor(Colors.WARNING))
                    else:
                        item_msg.setForeground(QColor(Colors.TEXT_TERTIARY))
                break

    def reset_all_statuses(self):
        """Set all selected files to 'Ready' before starting."""
        for i, f in enumerate(self._files):
            if f.get('checked', True):
                f['status'] = "ready"
                f['message'] = ""
                item_status = self._table.item(i, 8)
                item_msg = self._table.item(i, 4)
                if item_status:
                    item_status.setText("Ready")
                    item_status.setForeground(QColor(Colors.TEXT))
                if item_msg:
                    item_msg.setText("")

    def set_session_info(self, total: int, success: int, error: int, skipped: int, elapsed_ms: float = None):
        """Update the header with batch processing results."""
        status_text = f"📊 Tổng: {total} | ✅ Thành công: {success} | ❌ Lỗi: {error} | ⏭ Bỏ qua: {skipped}"
        
        if elapsed_ms is not None:
            # Format elapsed_ms to mm:ss:ms
            # ms is the decimal part of seconds * 1000
            total_seconds = elapsed_ms / 1000.0
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            milliseconds = int(elapsed_ms % 1000)
            time_str = f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}"
            status_text += f"  |  ⏱ Thời gian: {time_str}"
            
        self._lbl_session_info.setText(status_text)
        self._lbl_session_info.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-weight: 600;")

    # ── Private Handlers ──

    def _import_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Select video folder")
        if not folder:
            return

        folder = os.path.normpath(folder)
        new_paths = []
        base_name = os.path.basename(folder)

        # Recursive scan
        for root, _, filenames in os.walk(folder):
            for f in sorted(filenames):
                if f.lower().endswith(VIDEO_EXTENSIONS):

                    fp = os.path.normpath(os.path.join(root, f))
                    if any(x['path'] == fp for x in self._files):
                        continue
                    
                    rel_dir = os.path.relpath(root, folder)
                    if rel_dir == ".":
                        rel_dir = base_name
                    else:
                        rel_dir = os.path.join(base_name, rel_dir).replace("\\", "/")
                    
                    file_info = {
                        "path": fp,
                        "name": f,
                        "rel_dir": rel_dir,
                        "size": os.path.getsize(fp),
                        "duration": "...",
                        "status": "ready",
                        "message": "",
                        "checked": True,
                        "settings_override": {},  # Per-video edit overrides (Tier 2)
                    }
                    self._files.append(file_info)
                    new_paths.append(fp)

        self._refresh_table()
        if new_paths:
            self._start_probing(new_paths)
        
        self.folder_loaded.emit(folder, len(self._files))

    def _import_single(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select video file(s)", "",
            "Video Files (*.mp4 *.mkv *.avi *.webm *.mov *.flv);;All Files (*.*)"
        )
        if not paths:
            return

        new_paths = []
        for path in paths:
            if any(x['path'] == path for x in self._files):
                continue
            
            f = os.path.basename(path)
            file_info = {
                "path": path,
                "name": f,
                "rel_dir": ".",
                "size": os.path.getsize(path),
                "duration": "...",
                "status": "ready",
                "message": "",
                "checked": True,
                "settings_override": {},  # Per-video edit overrides (Tier 2)
            }
            self._files.append(file_info)
            new_paths.append(path)

        self._refresh_table()
        if new_paths:
            self._start_probing(new_paths)

    def _refresh_table(self):
        """Sync the UI table with self._files."""
        self._table.setRowCount(len(self._files))
        
        has_files = len(self._files) > 0
        self._content_splitter.setVisible(has_files)
        self._import_area.setVisible(not has_files)

        for i, f in enumerate(self._files):
            # 0. Checkbox
            cb = CheckBox()
            cb.blockSignals(True) # Prevent stateChanged from firing during setup
            cb.setChecked(f.get('checked', True))
            cb.stateChanged.connect(lambda state, idx=i: self._on_checkbox_changed(idx, state))
            cb.blockSignals(False)
            self._table.setCellWidget(i, 0, cb)

            # 1. Index
            self._table.setItem(i, 1, QTableWidgetItem(str(i + 1)))
            
            # 2. Filename
            self._table.setItem(i, 2, QTableWidgetItem(f['name']))
            
            # 3. Rel Dir
            self._table.setItem(i, 3, QTableWidgetItem(f['rel_dir']))
            
            # 4. Message
            self._table.setItem(i, 4, QTableWidgetItem(f.get('message', "")))
            
            # 5. Size
            size_mb = f['size'] / (1024 * 1024)
            self._table.setItem(i, 5, QTableWidgetItem(f"{size_mb:.1f} MB"))
            
            # 6. Duration
            self._table.setItem(i, 6, QTableWidgetItem(str(f['duration'])))
            
            # 7. Scenes
            sc = len(f.get('scenes', []))
            si = QTableWidgetItem(f"{sc} cảnh" if sc else "—")
            si.setForeground(QColor(Colors.ACCENT_LIGHT if sc else Colors.TEXT_TERTIARY))
            self._table.setItem(i, 7, si)
            
            # 8. Status
            self._table.setItem(i, 8, QTableWidgetItem(f['status'].capitalize()))
            
            # 9. Action
            btn_del = ToolButton(FIF.DELETE.icon(), self)
            btn_del.clicked.connect(lambda _, idx=i: self._remove_file(idx))
            self._table.setCellWidget(i, 9, btn_del)

        self.files_changed.emit(self.file_count, self.selected_count)

    def _on_checkbox_changed(self, index: int, state: int):
        self._files[index]['checked'] = (state == 2)  # 2 is Checked
        self.files_changed.emit(self.file_count, self.selected_count)

    def _remove_file(self, index: int):
        if 0 <= index < len(self._files):
            self._files.pop(index)
            self._refresh_table()

    def _on_item_clicked(self, item: QTableWidgetItem):
        row = item.row()
        if 0 <= row < len(self._files):
            path = self._files[row]['path']
            self.video_selected.emit(path)

    # ── Background Probing ──

    def _start_probing(self, paths: list[str]):
        if self._probe_worker:
            self._probe_worker.cancel()
        
        self._probe_worker = ProbeWorker(paths)
        self._probe_worker.info_ready.connect(self._on_probe_ready)
        self._probe_worker.start()

    def _on_probe_ready(self, path: str, info: dict):
        for i, f in enumerate(self._files):
            if f['path'] == path:
                f['raw_info'] = info  # Store full info for validation
                duration = info.get('duration', 0)
                # Format duration HH:MM:SS
                mm, ss = divmod(int(duration), 60)
                hh, mm = divmod(mm, 60)
                d_str = f"{hh:02d}:{mm:02d}:{ss:02d}" if hh > 0 else f"{mm:02d}:{ss:02d}"
                f['duration'] = d_str
                
                # Update table cell
                item = self._table.item(i, 6) # Duration is index 6 now
                if item:
                    item.setText(d_str)
                break

    # ── Scene Detection Logic ──

    def update_scenes(self, path: str, scenes: list):
        """Update scenes for a video and refresh table."""
        for i, f in enumerate(self._files):
            if f['path'] == path:
                # Ensure each scene has settings_override for per-scene edits (Tier 3)
                for sc in scenes:
                    if 'settings_override' not in sc:
                        sc['settings_override'] = {}
                f['scenes'] = scenes
                f['scene_done'] = True
                
                sc_count = len(scenes)
                si = QTableWidgetItem(f"{sc_count} cảnh" if sc_count else "—")
                si.setForeground(QColor(Colors.ACCENT_LIGHT if sc_count else Colors.TEXT_TERTIARY))
                self._table.setItem(i, 7, si)
                break

    def show_scenes(self, path: str, viewing: bool):
        """Show or hide the scene table for the given video path."""
        if not viewing:
            self._scene_table.setRowCount(0)
            self._scene_table.setVisible(False)
            self._table.setVisible(True)
            self._lbl_session_info.setText("Những video dưới đây cần được tick chọn để xử lý")
            self._lbl_session_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; font-weight: 500;")
            return

        file_info = next((f for f in self._files if f['path'] == path), None)
        if not file_info:
            self._scene_table.setRowCount(0)
            self._scene_table.setVisible(False)
            self._table.setVisible(True)
            return

        scenes = file_info.get("scenes", [])
        self._scene_table.setRowCount(len(scenes))
        self._table.setVisible(False)
        self._scene_table.setVisible(True)
        
        self._lbl_session_info.setText(f"🎬 Scenes: {file_info['name']} — {len(scenes)} cảnh")
        self._lbl_session_info.setStyleSheet(f"color: {Colors.ACCENT_LIGHT}; font-size: 13px; font-weight: 600;")

        self._current_scene_path = path
        for i, sc in enumerate(scenes):
            cb = CheckBox()
            cb.setChecked(sc.get('checked', True))
            cb.stateChanged.connect(lambda state, idx=i: self._on_scene_checkbox_changed(idx, state))
            self._scene_table.setCellWidget(i, 0, cb)
            
            self._scene_table.setItem(i, 1, QTableWidgetItem(str(i + 1)))
            self._scene_table.setItem(i, 2, QTableWidgetItem(file_info['name']))
            
            ni = QTableWidgetItem(f"Scene {sc['idx']}")
            ni.setForeground(QColor(Colors.ACCENT_LIGHT))
            self._scene_table.setItem(i, 3, ni)
            
            self._scene_table.setItem(i, 4, QTableWidgetItem(str(sc['start'])))
            self._scene_table.setItem(i, 5, QTableWidgetItem(str(sc['end'])))
            self._scene_table.setItem(i, 6, QTableWidgetItem(str(sc['dur'])))

            btn_del = ToolButton(FIF.DELETE.icon(), self)
            btn_del.clicked.connect(lambda _, idx=i: self._remove_scene(idx))
            self._scene_table.setCellWidget(i, 7, btn_del)

    def _remove_scene(self, idx: int):
        if not self._current_scene_path: return
        file_info = next((f for f in self._files if f['path'] == self._current_scene_path), None)
        if file_info and 'scenes' in file_info:
            scenes = file_info['scenes']
            if 0 <= idx < len(scenes):
                scenes.pop(idx)
                self.show_scenes(self._current_scene_path, True)
                self.update_scenes(self._current_scene_path, scenes)

    def _on_scene_checkbox_changed(self, scene_idx: int, state: int):
        if not self._current_scene_path: return
        file_info = next((f for f in self._files if f['path'] == self._current_scene_path), None)
        if file_info and 'scenes' in file_info:
            if scene_idx < len(file_info['scenes']):
                file_info['scenes'][scene_idx]['checked'] = (state == 2)

    def _on_scene_item_clicked(self, item: QTableWidgetItem):
        if not self._current_scene_path: return
        row = item.row()
        file_info = next((f for f in self._files if f['path'] == self._current_scene_path), None)
        if file_info and 'scenes' in file_info:
            scenes = file_info['scenes']
            if row < len(scenes):
                sc = scenes[row]
                self.scene_clicked.emit(self._current_scene_path, row, sc['start_sec'], sc['end_sec'])

