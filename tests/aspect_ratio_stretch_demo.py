import sys
import os

# Thêm đường dẫn gốc vào sys.path để import được các module trong ui/
app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, app_root)

bins_path = os.path.join(app_root, "bins")
if os.path.exists(bins_path):
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(bins_path)
    os.environ["PATH"] = bins_path + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QFrame)
from PyQt6.QtCore import Qt
from ui.preview_widget import PreviewWidget
from ui.theme import Colors

class AspectRatioCanvasDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Canvas & Padding (Ép Khung Cách 2) Demo")
        self.resize(1100, 800)
        self.setStyleSheet(f"background-color: {Colors.BG_DARK}; color: {Colors.TEXT};")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Left Side: Video Preview Area ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Header với background để phân biệt vùng video
        self.header = QLabel("Video Preview (Slider luôn hiển thị Full)")
        self.header.setStyleSheet(f"font-size: 18px; font-weight: bold; padding: 10px; background: {Colors.BG_DARK}; border-bottom: 1px solid #333;")
        left_layout.addWidget(self.header)
        
        # Vùng chứa PreviewWidget (luôn giãn hết chiều ngang)
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(0)
        
        self.preview = PreviewWidget()
        # Đảm bảo layout của chính PreviewWidget cũng không có margin
        if self.preview.layout():
            self.preview.layout().setContentsMargins(0, 0, 0, 0)
            self.preview.layout().setSpacing(0)
            
        self.preview_layout.addWidget(self.preview)
        
        left_layout.addWidget(self.preview_container, 1)
        
        self.info_label = QLabel("Khung hình đích: Gốc")
        self.info_label.setStyleSheet(f"color: {Colors.ACCENT}; font-weight: bold; font-size: 14px; padding: 5px;")
        left_layout.addWidget(self.info_label)
        
        main_layout.addWidget(left_panel, 3)
        
        # --- Right Side: Controls ---
        right_panel = QWidget()
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("CÀI ĐẶT KHUNG HÌNH (CANVAS)"))
        
        # Preset Aspect Ratios
        self.combo_ratios = QComboBox()
        self.ratios = {
            "Gốc (Original)": None,
            "9:16 (Dọc - TikTok/Reels)": 9/16,
            "16:9 (Ngang - Youtube)": 16/9,
            "1:1 (Vuông - Square)": 1.0,
            "4:5 (Instagram Portrait)": 4/5,
            "3:4 (Dọc)": 3/4,
            "2:3 (Dọc)": 2/3,
            "4:3 (Ngang cũ)": 4/3,
            "21:9 (Ultrawide)": 21/9,
            "2.35:1 (Cinematic)": 2.35,
            "18:9 (Điện thoại mới)": 18/9
        }
        self.combo_ratios.addItems(self.ratios.keys())
        self.combo_ratios.currentIndexChanged.connect(self.on_ratio_changed)
        right_layout.addWidget(self.combo_ratios)
        
        help_text = QLabel(
            "Cách hoạt động:\n\n"
            "1. Video gốc GIỮ NGUYÊN tỉ lệ, không bị méo.\n"
            "2. 'Ép' ở đây là đưa video vào một cái khung mới.\n"
            "3. Nếu video nhỏ hơn khung, phần thừa sẽ được lấp đầy bằng màu đen mặc định."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        right_layout.addWidget(help_text)
        
        right_layout.addStretch()
        
        # Video Loader
        self.btn_load = QPushButton("Chọn Video Test")
        self.btn_load.clicked.connect(self.load_default_video)
        right_layout.addWidget(self.btn_load)
        
        main_layout.addWidget(right_panel)
        
        # State
        self.current_ratio_val = None
        
        # Load default
        self.load_default_video()

    def load_default_video(self):
        video_path = r"C:\source_code_new\backup\video-downloader-interface\desktop_v2\video_test\demo\MultiFormat Square Frame Test Video - Landscape - Wide (V03).mp4"
        if os.path.exists(video_path):
            self.preview.load_video(video_path)
        else:
            print("Video test not found.")

    def on_ratio_changed(self):
        label = self.combo_ratios.currentText()
        ratio = self.ratios[label]
        self.current_ratio_val = ratio
        
        self.info_label.setText(f"Khung hình đích: {label}")
        
        # SỬ DỤNG API CHÍNH THỨC: update_settings để PreviewWidget tự quản lý container
        self.preview.update_settings({
            "canvas_ratio_val": ratio,
            "bg_type": "black" # Hoặc "blur" tùy ý
        })

    def update_container_aspect(self, ratio):
        """Hàm này hiện tại đã được PreviewWidget tự xử lý bên trong update_settings"""
        pass

    def apply_preview_filters(self):
        """Hàm này hiện tại đã được PreviewWidget tự xử lý bên trong update_settings"""
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AspectRatioCanvasDemo()
    window.show()
    sys.exit(app.exec())
