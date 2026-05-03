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
                             QPushButton, QLabel, QComboBox, QSlider, QTextEdit)
from PyQt6.QtCore import Qt
from ui.preview_widget import PreviewWidget
from ui.theme import Colors

class CanvasBlurPreviewDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Preview: Background Canvas Blur")
        self.resize(1200, 850)
        self.setStyleSheet(f"background-color: {Colors.BG_DARK}; color: {Colors.TEXT};")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Left Side: Video Preview Area ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        self.header = QLabel("Live Preview: Canvas Blur Effect")
        self.header.setStyleSheet(f"font-size: 18px; font-weight: bold; padding: 15px; background: #1a1a1a; border-bottom: 1px solid #333;")
        left_layout.addWidget(self.header)
        
        # Vùng chứa PreviewWidget (luôn giãn hết chiều ngang)
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(0)
        
        self.preview = PreviewWidget()
        # Đảm bảo layout của PreviewWidget khít 100%
        if self.preview.layout():
            self.preview.layout().setContentsMargins(0, 0, 0, 0)
            self.preview.layout().setSpacing(0)
            
        self.preview_layout.addWidget(self.preview)
        left_layout.addWidget(self.preview_container, 1)
        
        main_layout.addWidget(left_panel, 3)
        
        # --- Right Side: Controls ---
        right_panel = QWidget()
        right_panel.setFixedWidth(350)
        right_panel.setStyleSheet(f"background-color: #1e1e1e; border-left: 1px solid #333;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)
        
        right_layout.addWidget(QLabel("CÀI ĐẶT CANVAS"))
        
        # 1. Chọn Tỉ lệ
        right_layout.addWidget(QLabel("Tỉ lệ khung hình (Aspect Ratio):"))
        self.combo_ratios = QComboBox()
        self.ratios = {
            "9:16 (Dọc TikTok)": 9/16,
            "3:4 (Dọc Classic)": 3/4,
            "1:1 (Vuông)": 1,
            "16:9 (Ngang Youtube)": 16/9,
            "21:9 (Cinematic)": 21/9
        }
        self.combo_ratios.addItems(self.ratios.keys())
        self.combo_ratios.currentIndexChanged.connect(self.update_preview)
        right_layout.addWidget(self.combo_ratios)
        
        # 2. Chỉnh Blur Strength
        self.blur_label = QLabel("Độ mờ nền (Blur Strength): 40")
        right_layout.addWidget(self.blur_label)
        self.slider_blur = QSlider(Qt.Orientation.Horizontal)
        self.slider_blur.setRange(0, 100)
        self.slider_blur.setValue(40)
        self.slider_blur.valueChanged.connect(self.on_blur_changed)
        right_layout.addWidget(self.slider_blur)
        
        # 3. Hiển thị Filter String (để debug/copy)
        right_layout.addWidget(QLabel("FFmpeg Filter (Lavfi):"))
        self.filter_display = QTextEdit()
        self.filter_display.setReadOnly(True)
        self.filter_display.setStyleSheet("background-color: #111; color: #aaa; font-family: Consolas; font-size: 11px;")
        right_layout.addWidget(self.filter_display)
        
        right_layout.addStretch()
        
        # Video Loader
        self.btn_load = QPushButton("Chọn Video Test")
        self.btn_load.setStyleSheet("height: 40px; background-color: #2563eb; font-weight: bold;")
        self.btn_load.clicked.connect(self.load_video)
        right_layout.addWidget(self.btn_load)
        
        main_layout.addWidget(right_panel)
        
        # Init State
        self.current_ratio = 9/16
        self.blur_strength = 40
        
        # Load video mặc định nếu có
        default_video = r"C:\source_code_new\backup\video-downloader-interface\desktop_v2\video_test\demo\MultiFormat Square Frame Test Video - Landscape - Wide (V03).mp4"
        if os.path.exists(default_video):
            self.preview.load_video(default_video)
            # Delay một chút để mpv init xong mới apply filter
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self.update_preview)

    def load_video(self):
        # Placeholder cho việc chọn file nếu cần, ở đây dùng mặc định để test nhanh
        pass

    def on_blur_changed(self, value):
        self.blur_strength = value
        self.blur_label.setText(f"Độ mờ nền (Blur Strength): {value}")
        self.update_preview()

    def update_preview(self):
        label = self.combo_ratios.currentText()
        ratio = self.ratios[label]
        self.current_ratio = ratio
        
        # 1. Cập nhật kích thước khung nhìn (giống CapCut: Slider vẫn full width)
        container_w = self.preview_container.width()
        container_h = self.preview_container.height() - 44 # trừ thanh controls
        
        if container_w <= 0 or container_h <= 0:
            container_w, container_h = 800, 600
            
        target_w = container_w
        target_h = target_w / ratio
        
        if target_h > container_h:
            target_h = container_h
            target_w = target_h * ratio
            
        tw, th = (int(target_w)//2)*2, (int(target_h)//2)*2
        
        self.preview._video_container.setFixedSize(tw, th)
        self.preview.layout().setAlignment(self.preview._video_container, Qt.AlignmentFlag.AlignCenter)
        
        # 2. Xây dựng Filter String dựa trên công thức bạn đưa
        # Chúng ta giả lập canvas_width và canvas_height chuẩn cho filter
        canvas_width = 720
        canvas_height = int(720 / ratio)
        canvas_width, canvas_height = (canvas_width//2)*2, (canvas_height//2)*2
        
        # Công thức của bạn:
        # [bg] = scale (increase) -> crop -> boxblur
        # [fg] = scale (decrease)
        # result = overlay [bg][fg]
        
        # Chuyển sang cú pháp MPV lavfi (dùng split để tách luồng video đơn thành 2)
        filter_complex = (
            f"split[v1][v2];"
            f"[v1]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=increase,crop={canvas_width}:{canvas_height},boxblur={self.blur_strength}:5[bg];"
            f"[v2]scale={canvas_width}:{canvas_height}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        
        # Áp dụng vào MPV
        self.preview.player.vf = f"lavfi=[{filter_complex}]"
        self.preview.player['keepaspect'] = 'no' # Vì filter đã xử lý tỉ lệ chuẩn rồi
        
        # Hiển thị filter để quan sát
        self.filter_display.setText(filter_complex)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CanvasBlurPreviewDemo()
    window.show()
    sys.exit(app.exec())
