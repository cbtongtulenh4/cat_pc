import os
import sys
import ctypes
from ctypes import c_int, c_void_p, cast, POINTER, pointer, Structure, c_char_p, c_size_t

# Thêm path mpv bins vào PATH
bins_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bins")
if os.path.exists(bins_path):
    os.environ["PATH"] = bins_path + os.pathsep + os.environ["PATH"]

import mpv
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QImage

# --- CTYPES DEFINITIONS FOR LIBMPV SOFTWARE RENDER ---
class MpvRenderParam(Structure):
    _fields_ = [('type_id', c_int), ('data', c_void_p)]

MPV_RENDER_PARAM_SW_SIZE = 17
MPV_RENDER_PARAM_SW_FORMAT = 18
MPV_RENDER_PARAM_SW_STRIDE = 19
MPV_RENDER_PARAM_SW_POINTER = 20

# Load libmpv directly to access low-level render function
try:
    # Use os.add_dll_directory for Python 3.8+ on Windows
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(bins_path)
        
    dll_name = "libmpv-2.dll"
    lib_path = os.path.join(bins_path, dll_name)
    _libmpv = ctypes.CDLL(lib_path)
    _mpv_render_context_render = _libmpv.mpv_render_context_render
    _mpv_render_context_render.argtypes = [c_void_p, POINTER(MpvRenderParam)]
    _mpv_render_context_render.restype = c_int
except Exception as e:
    print(f"Error loading libmpv ({lib_path}): {e}")
    sys.exit(1)

class SoftwarePreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        
        # Khởi tạo MPV
        self.player = mpv.MPV(vo="libmpv", start_event_thread=True)
        
        # Tạo render context
        self.ctx = mpv.MpvRenderContext(self.player, 'sw')
        self.ctx.update_cb = self._on_update
        
        self._crop_box = {"x": 20, "y": 20, "width": 60, "height": 60}
        
    def _on_update(self):
        QTimer.singleShot(0, self.update)

    def paintEvent(self, event):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        
        # Tạo QImage làm buffer
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.black)
        
        # --- LOW-LEVEL RENDER CALL ---
        size = (c_int * 2)(w, h)
        fmt = c_char_p(b"bgra")
        stride = c_size_t(img.bytesPerLine())
        # Lấy địa chỉ vùng nhớ trực tiếp từ QImage
        ptr = c_void_p(int(img.bits()))
        
        params = (MpvRenderParam * 5)(
            MpvRenderParam(MPV_RENDER_PARAM_SW_SIZE, cast(pointer(size), c_void_p)),
            MpvRenderParam(MPV_RENDER_PARAM_SW_FORMAT, cast(fmt, c_void_p)),
            MpvRenderParam(MPV_RENDER_PARAM_SW_STRIDE, cast(pointer(stride), c_void_p)),
            MpvRenderParam(MPV_RENDER_PARAM_SW_POINTER, ptr),
            MpvRenderParam(0, None) # End of array
        )
        
        # Gọi trực tiếp hàm C
        _mpv_render_context_render(self.ctx.handle, params)
        
        # Vẽ kết quả
        painter.drawImage(0, 0, img)
        self._draw_overlay(painter, w, h)
        painter.end()

    def _draw_overlay(self, painter, w, h):
        bx = self._crop_box["x"] / 100 * w
        by = self._crop_box["y"] / 100 * h
        bw = self._crop_box["width"] / 100 * w
        bh = self._crop_box["height"] / 100 * h
        rect = QRectF(bx, by, bw, bh)

        # Mask
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(0, 0, w, by))
        painter.drawRect(QRectF(0, by + bh, w, h - (by + bh)))
        painter.drawRect(QRectF(0, by, bx, bh))
        painter.drawRect(QRectF(bx + bw, by, w - (bx + bw), bh))

        # Khung tím
        accent = QColor("#7c3aed")
        painter.setPen(QPen(accent, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        
        # Lưới
        grid_pen = QPen(QColor(255, 255, 255, 80), 1)
        painter.setPen(grid_pen)
        for i in range(1, 3):
            lx = bx + (bw / 3) * i
            painter.drawLine(QPointF(lx, by), QPointF(lx, by + bh))
            ly = by + (bh / 3) * i
            painter.drawLine(QPointF(bx, ly), QPointF(bx + bw, ly))

        # Nhãn
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self._crop_box['width']}% x {self._crop_box['height']}%")

    def load_video(self, path):
        if os.path.exists(path):
            self.player.play(path)

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MPV Low-Level SW Render Test")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        self.preview = SoftwarePreviewWidget()
        layout.addWidget(self.preview)
        
        video_path = r"C:\source_code_new\backup\video-downloader-interface\demo_server\test\part001.mp4"
        self.preview.load_video(video_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())
