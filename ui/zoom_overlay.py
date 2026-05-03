from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QCursor

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
        elif self._drag_mode == "tl":
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


