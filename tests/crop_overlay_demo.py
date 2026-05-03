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

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt
from ui.preview_widget import PreviewWidget

class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crop Preview System Demo (Non-destructive)")
        self.resize(1000, 750)
        
        layout = QVBoxLayout(self)
        
        # 1. Header & Info
        header = QLabel("Kéo khung tím để chọn vùng, sau đó nhấn 'Apply' để xem kết quả cắt thật")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; margin-bottom: 5px;")
        layout.addWidget(header)
        
        # 2. Preview Widget
        self.preview = PreviewWidget()
        layout.addWidget(self.preview)
        
        # 3. Control Buttons
        controls = QHBoxLayout()
        
        self.btn_free = QPushButton("Tự do (Free)")
        self.btn_16_9 = QPushButton("16:9")
        self.btn_1_1 = QPushButton("1:1")
        self.btn_apply = QPushButton("APPLY CROP (Xem kết quả)")
        self.btn_reset = QPushButton("RESET (Quay lại gốc)")
        
        # Styling cho nút Apply để nổi bật
        self.btn_apply.setStyleSheet("background-color: #7c3aed; color: white; font-weight: bold; padding: 8px;")
        self.btn_reset.setStyleSheet("background-color: #f43f5e; color: white; font-weight: bold; padding: 8px;")
        
        controls.addWidget(self.btn_free)
        controls.addWidget(self.btn_16_9)
        controls.addWidget(self.btn_1_1)
        controls.addSpacing(20)
        controls.addWidget(self.btn_apply)
        controls.addWidget(self.btn_reset)
        
        layout.addLayout(controls)
        
        # Status label
        self.status_label = QLabel("Trạng thái: Đang ở chế độ chọn vùng")
        layout.addWidget(self.status_label)
        
        # Connections
        self.btn_free.clicked.connect(lambda: self.preview.enter_crop_mode(aspect_ratio=None))
        self.btn_16_9.clicked.connect(lambda: self.preview.enter_crop_mode(aspect_ratio=16/9))
        self.btn_1_1.clicked.connect(lambda: self.preview.enter_crop_mode(aspect_ratio=1.0))
        
        self.btn_apply.clicked.connect(self.apply_crop_logic)
        self.btn_reset.clicked.connect(self.reset_crop_logic)
        
        # Tự động bật chế độ crop khi mở
        self.preview.enter_crop_mode()
        
        # Load video test
        video_path = r"C:\source_code_new\backup\video-downloader-interface\demo_server\test\part001.mp4"
        self.preview.load_video(video_path)

    def apply_crop_logic(self):
        """Logic xử lý khi nhấn Apply: Sử dụng hàm apply tích hợp trong widget."""
        if self.preview.is_crop_mode():
            # Gọi hàm exit với apply=True để widget tự xử lý filter
            self.preview.exit_crop_mode(apply=True)
            self.status_label.setText("Trạng thái: ĐÃ ÁP DỤNG CROP")

    def reset_crop_logic(self):
        """Quay lại trạng thái gốc."""
        self.preview.reset_crop()
        # Bật lại khung chọn để user chọn tiếp nếu muốn
        self.preview.enter_crop_mode()
        self.status_label.setText("Trạng thái: Đã reset về video gốc")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())
