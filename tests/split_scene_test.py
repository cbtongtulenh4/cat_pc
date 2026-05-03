# https://github.com/Breakthrough/PySceneDetect
import os
ffmpeg_path = r"C:\source_code_new\backup\video-downloader-interface\desktop_v2\bin\ffmpeg"
os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ["PATH"]
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

video_path = r"C:\source_code_new\backup\video-downloader-interface\desktop_v2\video_test\demo\Are you busy. My face need attention right now 🍒🥺— Hazey haley Official.mp4"

video_manager = VideoManager([video_path])
scene_manager = SceneManager()

scene_manager.add_detector(ContentDetector(threshold=30.0))

video_manager.start()
scene_manager.detect_scenes(frame_source=video_manager)

scene_list = scene_manager.get_scene_list()

for i, scene in enumerate(scene_list):
    start, end = scene
    print(f"Scene {i}: {start.get_timecode()} -> {end.get_timecode()}")