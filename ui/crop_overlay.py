"""
Crop Overlay Widget — Interactive crop frame drawn on top of the video canvas.
Supports dragging 4 corners and the entire box. Renders a semi-transparent
black mask over the "cropped-out" regions and a rule-of-thirds grid inside
the crop area. All coordinates are in percentage (0-100) of the video area.

Win11 Fluent Design style: purple accent border, subtle glow, clean handles.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QCursor


class CropOverlayWidget(QWidget):
    """Transparent overlay for interactive crop region editing."""

    # Emitted when user finishes dragging. Dict: {x, y, width, height} in %
    crop_changed = pyqtSignal(dict)

    HANDLE_RADIUS = 7       # px — corner circle radius
    HANDLE_HIT_RADIUS = 14  # px — click target area

    def __init__(self, parent=None):
        super().__init__(parent)
        # Make this widget transparent so video shows through
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setMouseTracking(True)

        # Crop box in percent (0-100)
        self._box = {"x": 10.0, "y": 10.0, "width": 80.0, "height": 80.0}

        # Drag state
        self._drag_mode = None  # "move" | "tl" | "tr" | "bl" | "br" | None
        self._drag_start_mouse = QPointF()
        self._drag_start_box = {}

        # Aspect ratio constraint (None = free, else float w/h)
        self._aspect_ratio = None

        # Actual video rectangle (in pixels) within this widget
        self._video_rect = QRectF()

    # ── Public API ──

    def set_box(self, box: dict):
        """Set crop box from outside (e.g. when ratio button changes)."""
        self._box = dict(box)
        self.update()

    def get_box(self) -> dict:
        return dict(self._box)

    def set_video_rect(self, rect: QRectF):
        """Set the actual video area pixels within this widget."""
        self._video_rect = rect
        self.update()

    def set_aspect_ratio(self, ratio: float | None):
        """Set aspect ratio constraint. None = free crop."""
        self._aspect_ratio = ratio
        if ratio is not None:
            # Use video_rect for calculation instead of widget size
            vr = self._video_rect if not self._video_rect.isEmpty() else QRectF(0, 0, self.width(), self.height())
            vw, vh = vr.width(), vr.height()
            
            if vw > 0 and vh > 0:
                container_ratio = vw / vh
                # Calculate required percentage dimensions
                # PixelWidth = nw% * vw, PixelHeight = nh% * vh
                # nw% * vw / (nh% * vh) = ratio -> nw% = ratio * nh% * (vh/vw)
                
                if ratio > container_ratio:
                    nw_pct = 80.0
                    nh_pct = (80.0 / ratio) * container_ratio
                else:
                    nh_pct = 80.0
                    nw_pct = (80.0 * ratio) / container_ratio
                
                # print(f"[Ratio Change] Target AR: {ratio:.2f} | Container AR: {container_ratio:.2f}")
                # print(f"  Initial Box %: Width={nw_pct:.2f}, Height={nh_pct:.2f}")

                self._box = {
                    "x": (100.0 - nw_pct) / 2,
                    "y": (100.0 - nh_pct) / 2,
                    "width": nw_pct,
                    "height": nh_pct
                }
                self.crop_changed.emit(self.get_box())
                self.update()

    def reset(self):
        """Reset to full frame."""
        self._box = {"x": 0, "y": 0, "width": 100, "height": 100}
        self._aspect_ratio = None
        self.update()

    # ── Coordinate helpers ──

    def _box_rect(self) -> QRectF:
        """Return the crop box as pixel QRectF relative to this widget."""
        vr = self._video_rect
        if vr.isEmpty():
            # Fallback to widget rect if video rect not set
            vr = QRectF(0, 0, self.width(), self.height())
            
        return QRectF(
            vr.x() + (self._box["x"] / 100 * vr.width()),
            vr.y() + (self._box["y"] / 100 * vr.height()),
            self._box["width"] / 100 * vr.width(),
            self._box["height"] / 100 * vr.height(),
        )

    def _corner_centers(self) -> dict[str, QPointF]:
        r = self._box_rect()
        return {
            "tl": r.topLeft(),
            "tr": r.topRight(),
            "bl": r.bottomLeft(),
            "br": r.bottomRight(),
        }

    def _hit_test(self, pos: QPointF) -> str | None:
        """Return 'tl'/'tr'/'bl'/'br'/'move'/None depending on what was clicked."""
        for key, center in self._corner_centers().items():
            if (pos - center).manhattanLength() < self.HANDLE_HIT_RADIUS:
                return key
        if self._box_rect().contains(pos):
            return "move"
        return None

    # ── Paint ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        box_r = self._box_rect()

        # 1. Dark mask outside crop area
        # Safe now thanks to software rendering bridge
        mask_color = QColor(0, 0, 0, 150)  # semi-transparent black
        painter.setBrush(QBrush(mask_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        vr = self._video_rect if not self._video_rect.isEmpty() else QRectF(0, 0, w, h)
        
        # Mask areas (Top, Bottom, Left, Right relative to box_r)
        # We only mask within the video_rect to keep black bars clean
        # Top strip
        painter.drawRect(QRectF(vr.left(), vr.top(), vr.width(), box_r.top() - vr.top()))
        # Bottom strip
        painter.drawRect(QRectF(vr.left(), box_r.bottom(), vr.width(), vr.bottom() - box_r.bottom()))
        # Left strip
        painter.drawRect(QRectF(vr.left(), box_r.top(), box_r.left() - vr.left(), box_r.height()))
        # Right strip
        painter.drawRect(QRectF(box_r.right(), box_r.top(), vr.right() - box_r.right(), box_r.height()))

        # 2. Crop border — purple accent with subtle glow
        accent = QColor("#7c3aed")
        glow_pen = QPen(QColor(124, 58, 237, 80), 6)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(box_r)

        border_pen = QPen(accent, 2)
        painter.setPen(border_pen)
        painter.drawRect(box_r)

        # 3. Rule-of-thirds grid (subtle white lines)
        grid_pen = QPen(QColor(255, 255, 255, 80), 1)
        painter.setPen(grid_pen)
        third_w = box_r.width() / 3
        third_h = box_r.height() / 3
        for i in range(1, 3):
            x = box_r.left() + third_w * i
            painter.drawLine(QPointF(x, box_r.top()), QPointF(x, box_r.bottom()))
            y = box_r.top() + third_h * i
            painter.drawLine(QPointF(box_r.left(), y), QPointF(box_r.right(), y))

        # 4. Corner handles
        for key, center in self._corner_centers().items():
            # White filled circle with purple border
            painter.setPen(QPen(accent, 2))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(center, self.HANDLE_RADIUS, self.HANDLE_RADIUS)

        # 5. Dimension label (center of crop area)
        bw = self._box["width"]
        bh = self._box["height"]
        if bw < 99.5 or bh < 99.5:
            label = f"{bw:.1f}% × {bh:.1f}%"
            # Draw subtle background for text to be readable on any video
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
            tw = 80; th = 20
            painter.drawRoundedRect(
                QRectF(box_r.center().x() - tw/2, box_r.center().y() - th/2, tw, th),
                4, 4
            )
            
            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPixelSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(box_r, Qt.AlignmentFlag.AlignCenter, label)

        painter.end()

    # ── Mouse events ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            mode = self._hit_test(event.position())
            if mode:
                self._drag_mode = mode
                self._drag_start_mouse = event.position()
                self._drag_start_box = dict(self._box)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_mode:
            self._handle_drag(event.position())
            event.accept()
            return

        # Update cursor based on hover
        mode = self._hit_test(event.position())
        if mode in ("tl", "br"):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif mode in ("tr", "bl"):
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif mode == "move":
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_mode:
            self._drag_mode = None
            self.crop_changed.emit(self.get_box())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ── Drag logic ──

    def _handle_drag(self, pos: QPointF):
        w, h = self.width(), self.height()
        vr = self._video_rect if not self._video_rect.isEmpty() else QRectF(0, 0, w, h)
        if vr.width() == 0 or vr.height() == 0:
            return

        dx_pct = (pos.x() - self._drag_start_mouse.x()) / vr.width() * 100
        dy_pct = (pos.y() - self._drag_start_mouse.y()) / vr.height() * 100
        sb = self._drag_start_box

        if self._drag_mode == "move":
            nx = max(0, min(100 - sb["width"], sb["x"] + dx_pct))
            ny = max(0, min(100 - sb["height"], sb["y"] + dy_pct))
            self._box["x"] = nx
            self._box["y"] = ny
        else:
            # Corner drag
            nx, ny, nw, nh = sb["x"], sb["y"], sb["width"], sb["height"]
            anchor_x = sb["x"] if "r" in self._drag_mode else sb["x"] + sb["width"]
            anchor_y = sb["y"] if "b" in self._drag_mode else sb["y"] + sb["height"]

            # Calculate target width/height based on mouse delta
            if "l" in self._drag_mode:
                nw = max(2, sb["width"] - dx_pct)
                nx = anchor_x - nw
            elif "r" in self._drag_mode:
                nw = max(2, sb["width"] + dx_pct)

            if "t" in self._drag_mode:
                nh = max(2, sb["height"] - dy_pct)
                ny = anchor_y - nh
            elif "b" in self._drag_mode:
                nh = max(2, sb["height"] + dy_pct)

            # Apply aspect ratio constraint
            if self._aspect_ratio is not None:
                ar_pixel = self._aspect_ratio
                container_ar = vr.width() / vr.height()
                ar_pct = ar_pixel / container_ar
                
                # Pure diagonal projection logic
                sig_x = 1 if "r" in self._drag_mode else -1
                sig_y = 1 if "b" in self._drag_mode else -1
                
                # Vector representing the allowed ratio diagonal
                vx, vy = sig_x * ar_pct, sig_y * 1
                mag_sq = vx*vx + vy*vy
                
                # Mouse delta relative to start of drag
                dx = (pos.x() - self._drag_start_mouse.x()) / vr.width() * 100
                dy = (pos.y() - self._drag_start_mouse.y()) / vr.height() * 100
                
                # Project (dx, dy) onto (vx, vy)
                dot = dx*vx + dy*vy
                proj_len = dot / mag_sq
                
                nw = max(2, sb["width"] + proj_len * vx * sig_x)
                nh = max(2, sb["height"] + proj_len * vy * sig_y)

                # Boundary check: Cap both if any side hits a wall
                if "l" in self._drag_mode:
                    if anchor_x - nw < 0: nw = anchor_x
                else:
                    if anchor_x + nw > 100: nw = 100 - anchor_x
                    
                if "t" in self._drag_mode:
                    if anchor_y - nh < 0: nh = anchor_y
                else:
                    if anchor_y + nh > 100: nh = 100 - anchor_y
                
                # Re-sync nw/nh to maintain exact ratio after boundary caps
                if nw / ar_pct < nh:
                    nh = nw / ar_pct
                else:
                    nw = nh * ar_pct

                # Calculate final nx, ny
                nx = anchor_x - nw if "l" in self._drag_mode else anchor_x
                ny = anchor_y - nh if "t" in self._drag_mode else anchor_y

            # Final safety clamp
            nx = max(0, min(100 - nw, nx))
            ny = max(0, min(100 - nh, ny))
            self._box = {"x": nx, "y": ny, "width": nw, "height": nh}

        self.update()
