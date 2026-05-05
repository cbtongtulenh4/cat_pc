import sys, os

app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, app_root)
bins_path = os.path.join(app_root, "bins")
if os.path.exists(bins_path):
    if hasattr(os, 'add_dll_directory'): os.add_dll_directory(bins_path)
    os.environ["PATH"] = bins_path + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QComboBox, QSlider, QTextEdit)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QCursor
from ui.preview_widget import PreviewWidget
from ui.theme import Colors


class ZoomOverlayWidget(QWidget):
    """Lưới kéo thả để điều chỉnh kích thước và vị trí video trong canvas.
    Tọa độ tính bằng pixel của widget (có thể vượt ra ngoài biên)."""

    zoom_changed = pyqtSignal(dict)
    HANDLE_R = 7
    HANDLE_HIT = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setMouseTracking(True)
        # _box: tọa độ lưới relative to CANVAS (không phải overlay widget)
        self._box = QRectF(10, 10, 100, 100)
        # _canvas_offset: vị trí canvas trong overlay widget
        self._canvas_offset = QPointF(0, 0)
        self._canvas_size = QRectF(0, 0, 100, 100)
        self._drag_mode = None
        self._drag_start = QPointF()
        self._drag_start_box = QRectF()
        self._aspect_ratio = None # Aspect ratio constraint (None = free)

    def set_canvas_offset(self, offset: QPointF, size: QRectF):
        """Cập nhật vị trí canvas trong overlay widget"""
        self._canvas_offset = offset
        self._canvas_size = size
        self.update()

    def set_box(self, rect: QRectF):
        """Set box relative to canvas"""
        self._box = QRectF(rect)
        self.update()

    def get_box(self) -> QRectF:
        """Get box relative to canvas"""
        return QRectF(self._box)

    def set_aspect_ratio(self, ratio: float | None):
        """Set aspect ratio constraint for dragging"""
        self._aspect_ratio = ratio
        if ratio:
            # Adjust current box to match ratio (centered on current center)
            # Area preservation to avoid "shrinking" bug
            center = self._box.center()
            area = self._box.width() * self._box.height()
            nh = (area / ratio) ** 0.5
            nw = nh * ratio
            self._box = QRectF(center.x() - nw/2, center.y() - nh/2, nw, nh)
        self.update()

    def _box_on_screen(self) -> QRectF:
        """Chuyển box từ tọa độ canvas → tọa độ screen (overlay widget)"""
        o = self._canvas_offset
        return QRectF(self._box.x() + o.x(), self._box.y() + o.y(),
                      self._box.width(), self._box.height())

    def _screen_to_canvas(self, pos: QPointF) -> QPointF:
        """Chuyển tọa độ chuột (screen) → tọa độ canvas"""
        return QPointF(pos.x() - self._canvas_offset.x(),
                       pos.y() - self._canvas_offset.y())

    def _corners(self):
        b = self._box_on_screen()
        return {"tl": b.topLeft(), "tr": b.topRight(),
                "bl": b.bottomLeft(), "br": b.bottomRight()}

    def _edges(self):
        b = self._box_on_screen()
        return {"t": QPointF(b.center().x(), b.top()),
                "b": QPointF(b.center().x(), b.bottom()),
                "l": QPointF(b.left(), b.center().y()),
                "r": QPointF(b.right(), b.center().y())}

    def _hit_test(self, pos):
        for k, c in self._corners().items():
            if (pos - c).manhattanLength() < self.HANDLE_HIT: return k
        for k, c in self._edges().items():
            if (pos - c).manhattanLength() < self.HANDLE_HIT: return k
        if self._box_on_screen().contains(pos): return "move"
        return None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        b = self._box_on_screen()  # Dùng tọa độ screen để vẽ
        accent = QColor("#00d4aa")

        # Vẽ viền canvas (khung hình đích) để user nhìn rõ ranh giới
        o = self._canvas_offset
        cs = self._canvas_size
        canvas_rect = QRectF(o.x(), o.y(), cs.width(), cs.height())
        p.setPen(QPen(QColor(255, 255, 255, 40), 1, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(canvas_rect)

        # Glow + border
        p.setPen(QPen(QColor(0, 212, 170, 80), 6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(b)
        p.setPen(QPen(accent, 2))
        p.drawRect(b)

        # Lưới 3x3
        gp = QPen(QColor(255, 255, 255, 60), 1)
        p.setPen(gp)
        tw, th = b.width() / 3, b.height() / 3
        for i in range(1, 3):
            x = b.left() + tw * i
            p.drawLine(QPointF(x, b.top()), QPointF(x, b.bottom()))
            y = b.top() + th * i
            p.drawLine(QPointF(b.left(), y), QPointF(b.right(), y))

        # Corner handles
        for c in self._corners().values():
            p.setPen(QPen(accent, 2))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawEllipse(c, self.HANDLE_R, self.HANDLE_R)

        # Edge handles
        for c in self._edges().values():
            p.setPen(QPen(accent, 2))
            p.setBrush(QBrush(QColor(200, 200, 200)))
            p.drawEllipse(c, 4, 4)

        # Dimension label
        # Hiển thị kích thước bằng tọa độ canvas (không phải screen)
        label = f"{int(self._box.width())} x {int(self._box.height())} px"
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 160)))
        lw, lh = 110, 22
        p.drawRoundedRect(QRectF(b.center().x()-lw/2, b.center().y()-lh/2, lw, lh), 4, 4)
        p.setPen(QColor(255, 255, 255))
        f = p.font(); f.setPixelSize(11); f.setBold(True); p.setFont(f)
        p.drawText(b, Qt.AlignmentFlag.AlignCenter, label)
        p.end()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            m = self._hit_test(ev.position())
            if m:
                self._drag_mode = m
                self._drag_start = ev.position()
                self._drag_start_box = QRectF(self._box)
                ev.accept(); return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._drag_mode:
            self._handle_drag(ev.position()); ev.accept(); return
        m = self._hit_test(ev.position())
        cursors = {"tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
                   "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
                   "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
                   "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor,
                   "move": Qt.CursorShape.SizeAllCursor}
        self.setCursor(QCursor(cursors.get(m, Qt.CursorShape.ArrowCursor)))
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if self._drag_mode:
            self._drag_mode = None
            b = self._box
            self.zoom_changed.emit({"x": b.x(), "y": b.y(), "width": b.width(), "height": b.height()})
            ev.accept(); return
        super().mouseReleaseEvent(ev)

    def _handle_drag(self, pos):
        # dx, dy tính trên screen pixels → áp dụng trực tiếp cho _box (canvas coords)
        # vì tỉ lệ 1:1 giữa di chuyển chuột và di chuyển box
        dx = pos.x() - self._drag_start.x()
        dy = pos.y() - self._drag_start.y()
        sb = self._drag_start_box
        MIN = 20

        if self._drag_mode == "move":
            self._box = QRectF(sb.x()+dx, sb.y()+dy, sb.width(), sb.height())
        elif self._aspect_ratio:
            # --- Aspect Ratio Dragging ---
            ratio = self._aspect_ratio
            if self._drag_mode in ("tl", "tr", "bl", "br"):
                # Diagonal projection logic
                sig_x = 1 if "r" in self._drag_mode else -1
                sig_y = 1 if "b" in self._drag_mode else -1
                vx, vy = sig_x * ratio, sig_y * 1
                mag_sq = vx*vx + vy*vy
                dot = dx*vx + dy*vy
                proj_len = dot / mag_sq
                nw = max(MIN, sb.width() + proj_len * vx * sig_x)
                nh = nw / ratio
                nx = sb.right() - nw if "l" in self._drag_mode else sb.left()
                ny = sb.bottom() - nh if "t" in self._drag_mode else sb.top()
                self._box = QRectF(nx, ny, nw, nh)
            elif self._drag_mode in ("t", "b"):
                nh = max(MIN, sb.height() + (dy if self._drag_mode == "b" else -dy))
                nw = nh * ratio
                nx = sb.center().x() - nw/2
                ny = sb.bottom() - nh if self._drag_mode == "t" else sb.top()
                self._box = QRectF(nx, ny, nw, nh)
            elif self._drag_mode in ("l", "r"):
                nw = max(MIN, sb.width() + (dx if self._drag_mode == "r" else -dx))
                nh = nw / ratio
                nx = sb.right() - nw if self._drag_mode == "l" else sb.left()
                ny = sb.center().y() - nh/2
                self._box = QRectF(nx, ny, nw, nh)
        else:
            # --- Free Dragging ---
            if self._drag_mode == "tl":
                self._box = QRectF(sb.left()+dx, sb.top()+dy, sb.right()-(sb.left()+dx), sb.bottom()-(sb.top()+dy))
            elif self._drag_mode == "tr":
                self._box = QRectF(sb.left(), sb.top()+dy, sb.right()+dx-sb.left(), sb.bottom()-(sb.top()+dy))
            elif self._drag_mode == "bl":
                self._box = QRectF(sb.left()+dx, sb.top(), sb.right()-(sb.left()+dx), sb.bottom()+dy-sb.top())
            elif self._drag_mode == "br":
                self._box = QRectF(sb.left(), sb.top(), sb.right()+dx-sb.left(), sb.bottom()+dy-sb.top())
            elif self._drag_mode == "t":
                self._box = QRectF(sb.left(), sb.top()+dy, sb.width(), sb.bottom()-(sb.top()+dy))
            elif self._drag_mode == "b":
                self._box = QRectF(sb.left(), sb.top(), sb.width(), sb.bottom()+dy-sb.top())
            elif self._drag_mode == "l":
                self._box = QRectF(sb.left()+dx, sb.top(), sb.right()-(sb.left()+dx), sb.height())
            elif self._drag_mode == "r":
                self._box = QRectF(sb.left(), sb.top(), sb.right()+dx-sb.left(), sb.height())

        if self._box.width() < MIN: self._box.setWidth(MIN)
        if self._box.height() < MIN: self._box.setHeight(MIN)
        self.update()


class ZoomCanvasPreviewDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Preview: Zoom + Canvas Blur")
        self.resize(1200, 850)
        self.setStyleSheet(f"background-color: {Colors.BG_DARK}; color: {Colors.TEXT};")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left: Video ---
        left = QWidget()
        ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        self.header = QLabel("Live Preview: Zoom + Canvas Blur")
        self.header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 15px; background: #1a1a1a; border-bottom: 1px solid #333;")
        ll.addWidget(self.header)

        self.preview_container = QWidget()
        pl = QVBoxLayout(self.preview_container); pl.setContentsMargins(0,0,0,0); pl.setSpacing(0)
        self.preview = PreviewWidget()
        if self.preview.layout():
            self.preview.layout().setContentsMargins(0,0,0,0)
            self.preview.layout().setSpacing(0)
        pl.addWidget(self.preview)
        ll.addWidget(self.preview_container, 1)
        main_layout.addWidget(left, 3)

        # --- Right: Controls ---
        right = QWidget(); right.setFixedWidth(350)
        right.setStyleSheet("background-color: #1e1e1e; border-left: 1px solid #333;")
        rl = QVBoxLayout(right); rl.setContentsMargins(20,20,20,20); rl.setSpacing(12)

        rl.addWidget(QLabel("ZOOM + CANVAS BLUR"))

        rl.addWidget(QLabel("Tỉ lệ khung hình:"))
        self.combo = QComboBox()
        self.ratios = {"9:16 (TikTok)": 9/16, "3:4 (Dọc)": 3/4, "1:1 (Vuông)": 1, "16:9 (Youtube)": 16/9}
        self.combo.addItems(self.ratios.keys())
        self.combo.currentIndexChanged.connect(self.on_ratio_changed)
        rl.addWidget(self.combo)

        rl.addWidget(QLabel("Tỉ lệ lưới (Grid Ratio):"))
        self.zoom_ratio_combo = QComboBox()
        self.zoom_ratios = {
            "Tự do": None,
            "9:16": 9/16,
            "16:9": 16/9,
            "1:1": 1.0,
            "4:5": 4/5,
            "4:3": 4/3
        }
        self.zoom_ratio_combo.addItems(self.zoom_ratios.keys())
        self.zoom_ratio_combo.currentIndexChanged.connect(self.on_zoom_ratio_changed)
        rl.addWidget(self.zoom_ratio_combo)

        self.blur_label = QLabel("Blur Strength: 40")
        rl.addWidget(self.blur_label)
        self.slider_blur = QSlider(Qt.Orientation.Horizontal)
        self.slider_blur.setRange(0, 100); self.slider_blur.setValue(40)
        self.slider_blur.valueChanged.connect(self.on_blur_changed)
        rl.addWidget(self.slider_blur)

        # Info hiển thị giá trị zoom
        self.zoom_info = QLabel("Grid: chưa khởi tạo")
        self.zoom_info.setStyleSheet(f"color: #00d4aa; font-size: 12px;")
        self.zoom_info.setWordWrap(True)
        rl.addWidget(self.zoom_info)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton("APPLY ZOOM")
        self.btn_apply.setStyleSheet("height: 40px; background-color: #00a87e; font-weight: bold;")
        self.btn_apply.clicked.connect(self.apply_zoom)
        btn_row.addWidget(self.btn_apply)

        self.btn_reset = QPushButton("RESET")
        self.btn_reset.setStyleSheet("height: 40px; background-color: #f43f5e; font-weight: bold;")
        self.btn_reset.clicked.connect(self.reset_zoom)
        btn_row.addWidget(self.btn_reset)
        rl.addLayout(btn_row)

        rl.addWidget(QLabel("FFmpeg Filter:"))
        self.filter_display = QTextEdit()
        self.filter_display.setReadOnly(True)
        self.filter_display.setStyleSheet("background-color: #111; color: #aaa; font-family: Consolas; font-size: 11px;")
        rl.addWidget(self.filter_display)

        rl.addStretch()
        main_layout.addWidget(right)

        # State
        self.canvas_w = 720
        self.canvas_h = 1280
        self.blur_strength = 40
        self.zoom_overlay = None

        # Load video
        vid = r"C:\source_code_new\backup\video-downloader-interface\desktop_v2\video_test\demo\MultiFormat Square Frame Test Video - Landscape - Wide (V03).mp4"
        if os.path.exists(vid):
            self.preview.load_video(vid)
            QTimer.singleShot(500, self.on_ratio_changed)

    # --- Tính toán ---

    def _get_video_ar(self):
        """Lấy aspect ratio video gốc từ MPV"""
        try:
            p = self.preview.player.video_params
            return p.get('w', 1920) / p.get('h', 1080)
        except: return 16/9

    def _calc_fitted_video(self):
        """Tính kích thước video sau khi fit vào canvas (decrease)"""
        video_ar = self._get_video_ar()
        canvas_ar = self.canvas_w / self.canvas_h

        if video_ar > canvas_ar:
            fit_w = self.canvas_w
            fit_h = self.canvas_w / video_ar
        else:
            fit_h = self.canvas_h
            fit_w = self.canvas_h * video_ar

        x = (self.canvas_w - fit_w) / 2
        y = (self.canvas_h - fit_h) / 2
        return x, y, fit_w, fit_h

    def _canvas_to_widget(self, cx, cy, cw, ch):
        """Canvas pixels → Widget pixels"""
        ww = self.preview._video_container.width()
        wh = self.preview._video_container.height()
        sx, sy = ww / self.canvas_w, wh / self.canvas_h
        return cx*sx, cy*sy, cw*sx, ch*sy

    def _widget_to_canvas(self, wx, wy, ww, wh):
        """Widget pixels → Canvas pixels"""
        cw = self.preview._video_container.width()
        ch = self.preview._video_container.height()
        sx, sy = self.canvas_w / cw, self.canvas_h / ch
        return wx*sx, wy*sy, ww*sx, wh*sy

    # --- Events ---

    def on_ratio_changed(self):
        label = self.combo.currentText()
        ratio = self.ratios[label]
        self.canvas_w = 720
        self.canvas_h = int(720 / ratio)
        self.canvas_w, self.canvas_h = (self.canvas_w//2)*2, (self.canvas_h//2)*2

        # Resize container
        cw = self.preview_container.width()
        ch = self.preview_container.height() - 44
        if cw <= 0 or ch <= 0: cw, ch = 800, 600

        tw = cw; th = tw / ratio
        if th > ch: th = ch; tw = th * ratio
        tw, th = (int(tw)//2)*2, (int(th)//2)*2

        self.preview._video_container.setFixedSize(tw, th)
        self.preview.layout().setAlignment(self.preview._video_container, Qt.AlignmentFlag.AlignCenter)

        # Đặt filter blur mặc định (video fit giữa)
        self._apply_default_blur()

        # Tạo hoặc reset lưới
        QTimer.singleShot(100, self._init_grid)

    def on_blur_changed(self, val):
        self.blur_strength = val
        self.blur_label.setText(f"Blur Strength: {val}")

    def on_zoom_ratio_changed(self):
        if self.zoom_overlay:
            label = self.zoom_ratio_combo.currentText()
            ratio = self.zoom_ratios[label]
            self.zoom_overlay.set_aspect_ratio(ratio)
            self._update_zoom_info()

    def _init_grid(self):
        """Tạo lưới bao quanh vị trí video mặc định"""
        if self.zoom_overlay is None:
            self.zoom_overlay = ZoomOverlayWidget(self.preview_container)
            self.zoom_overlay.zoom_changed.connect(self._on_grid_changed)

        # Overlay phủ toàn bộ preview_container
        self.zoom_overlay.setGeometry(0, 0, self.preview_container.width(), self.preview_container.height())
        self.zoom_overlay.show()
        self.zoom_overlay.raise_()

        # Tính offset: vị trí _video_container trong preview_container
        self._update_canvas_offset()

        # Tính vị trí video fit trong canvas → chuyển sang widget pixels
        cx, cy, cfw, cfh = self._calc_fitted_video()
        wx, wy, ww, wh = self._canvas_to_widget(cx, cy, cfw, cfh)
        self.zoom_overlay.set_box(QRectF(wx, wy, ww, wh))
        self._update_zoom_info()

    def _update_canvas_offset(self):
        """Tính vị trí canvas (_video_container) trong preview_container"""
        if not self.zoom_overlay: return
        vc = self.preview._video_container
        # Chuyển tọa độ góc trên-trái của _video_container sang tọa độ preview_container
        pos = vc.mapTo(self.preview_container, vc.rect().topLeft())
        offset = QPointF(pos.x(), pos.y())
        size = QRectF(0, 0, vc.width(), vc.height())
        self.zoom_overlay.set_canvas_offset(offset, size)

    def _on_grid_changed(self, box):
        """Khi user thả lưới (chưa Apply)"""
        self._update_zoom_info()

    def _update_zoom_info(self):
        if not self.zoom_overlay: return
        b = self.zoom_overlay.get_box()
        # Chuyển sang canvas pixels
        cx, cy, cw, ch = self._widget_to_canvas(b.x(), b.y(), b.width(), b.height())
        self.zoom_info.setText(
            f"Grid (widget): {int(b.width())}x{int(b.height())} tại ({int(b.x())},{int(b.y())})\n"
            f"Grid (canvas): {int(cw)}x{int(ch)} tại ({int(cx)},{int(cy)})\n"
            f"Canvas: {self.canvas_w}x{self.canvas_h}"
        )

    # --- Filter ---

    def _apply_default_blur(self):
        """Áp dụng filter blur mặc định (video fit giữa canvas)"""
        w, h = self.canvas_w, self.canvas_h
        f = (
            f"split[v1][v2];"
            f"[v1]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur={self.blur_strength}:5[bg];"
            f"[v2]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        self.preview.player.vf = f"lavfi=[{f}]"
        self.preview.player['keepaspect'] = 'no'
        self.filter_display.setText(f)

    def apply_zoom(self):
        """Nhấn Apply: resize video theo kích thước lưới"""
        if not self.zoom_overlay: return
        b = self.zoom_overlay.get_box()

        # Chuyển grid từ widget → canvas pixels
        cx, cy, cw, ch = self._widget_to_canvas(b.x(), b.y(), b.width(), b.height())

        # Ép chẵn
        video_w = (int(cw) // 2) * 2
        video_h = (int(ch) // 2) * 2
        target_x = int(cx)
        target_y = int(cy)

        canvas_w, canvas_h = self.canvas_w, self.canvas_h

        # Công thức của bạn
        f = (
            f"split[v1][v2];"
            f"[v1]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
            f"crop={canvas_w}:{canvas_h},boxblur={self.blur_strength}:5[bg];"
            f"[v2]scale={video_w}:{video_h}[fg];"
            f"[bg][fg]overlay={target_x}:{target_y}:shortest=1"
        )

        self.preview.player.vf = f"lavfi=[{f}]"
        self.preview.player['keepaspect'] = 'no'
        self.filter_display.setText(f)

        self.zoom_info.setText(
            self.zoom_info.text() + f"\n\n✅ APPLIED!\n"
            f"video: {video_w}x{video_h}\n"
            f"pos: ({target_x}, {target_y})"
        )

    def reset_zoom(self):
        """Reset về trạng thái mặc định"""
        self._apply_default_blur()
        QTimer.singleShot(50, self._init_grid)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ZoomCanvasPreviewDemo()
    w.show()
    sys.exit(app.exec())
