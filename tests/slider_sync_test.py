import sys
import os
import time

# --- MPV Path Setup ---
base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bins_path = os.path.join(base_path, "bins")
if os.path.exists(bins_path):
    os.environ["PATH"] = bins_path + os.pathsep + os.environ["PATH"]

import mpv
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSlider, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from qfluentwidgets import Slider, setTheme, Theme, setThemeColor

class SliderTest(QWidget):
    def __init__(self, video_path):
        super().__init__()
        self.setWindowTitle("So sánh Slider Sync với Video")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #202020; color: white;")
        
        layout = QVBoxLayout(self)

        # 1. Video Canvas
        self.video_canvas = QWidget()
        self.video_canvas.setMinimumSize(640, 360)
        self.video_canvas.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_canvas)

        # 2. Slider của thư viện QFluentWidgets (Có thể bị delay Thumb)
        layout.addWidget(QLabel("1. QFluentWidgets Slider (Quan sát độ trễ của Thumb so với vạch tím):"))
        self.fluent_slider = Slider(Qt.Orientation.Horizontal)
        self.fluent_slider.setRange(0, 1000)
        layout.addWidget(self.fluent_slider)

        # 3. Slider gốc của PyQt6 + Custom CSS (Chính xác tuyệt đối)
        layout.addWidget(QLabel("2. Standard QSlider + Custom CSS (Vạch tím và Thumb dính liền):"))
        self.standard_slider = QSlider(Qt.Orientation.Horizontal)
        self.standard_slider.setRange(0, 1000)
        
        # Áp dụng CSS để giả lập giao diện Win11 màu tím
        self.standard_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 4px solid #7c3aed;
                width: 14px;
                height: 14px;
                margin: -7px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #7c3aed;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.standard_slider)

        # Khởi tạo MPV
        self.player = mpv.MPV(
            wid=str(int(self.video_canvas.winId())),
            keep_open=True,
            hwdec="auto"
        )
        
        self._duration = 0.0
        self.player.play(video_path)

        # Timer cập nhật UI (30fps)
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll_update)
        self.timer.start(33)

    def _poll_update(self):
        duration = self.player.duration
        time_pos = self.player.time_pos
        
        if duration:
            self._duration = duration
        
        if time_pos and self._duration > 0:
            val = int((time_pos / self._duration) * 1000)
            
            # Cập nhật cả 2 slider
            self.fluent_slider.setValue(val)
            self.standard_slider.setValue(val)

    def closeEvent(self, event):
        self.player.terminate()
        super().closeEvent(event)

if __name__ == "__main__":
    # Đường dẫn video test (Thay bằng file của bạn nếu cần)
    test_video = r"C:\source_code_new\backup\video-downloader-interface\demo_server\test\part001.mp4"
    
    if not os.path.exists(test_video):
        print(f"Lỗi: Không tìm thấy file video tại {test_video}")
        sys.exit(1)

    app = QApplication(sys.argv)
    setTheme(Theme.DARK)
    setThemeColor('#7c3aed')
    
    demo = SliderTest(test_video)
    demo.show()
    sys.exit(app.exec())
