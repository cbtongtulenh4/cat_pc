import os
import sys

# Thêm đường dẫn chứa mpv DLL vào PATH
# Kiểm tra cả thư mục cha và thư mục 'bins'
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
bins_path = os.path.join(base_path, "bins")

if os.path.exists(bins_path):
    os.environ["PATH"] = bins_path + os.pathsep + os.environ["PATH"]
else:
    os.environ["PATH"] = base_path + os.pathsep + os.environ["PATH"]


import mpv
player = mpv.MPV(ytdl=True)

# 1. Thử một vài filter "CapCut style"
# Bạn có thể uncomment (bỏ dấu #) từng dòng để thử:

# Hiệu ứng Đen trắng (Black & White)
# player.vf = "format=gray"

# Hiệu ứng Làm mờ (Box Blur)
# player.vf = "boxblur=10:1"

# Hiệu ứng Vignette (Tối 4 góc)
# player.vf = "vignette"

# # Chỉnh màu: Tăng độ bão hòa (saturation) và tương phản (contrast)
# player.vf = "eq=saturation=1.5:contrast=1.2"

# Lật ngược video (Flip).
player.vf = "hflip,vflip"

player.play(r"C:\source_code_new\backup\video-downloader-interface\demo_server\test\part001.mp4")
player.wait_for_playback()

