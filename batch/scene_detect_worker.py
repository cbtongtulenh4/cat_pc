from PyQt6.QtCore import QThread, pyqtSignal

class SceneDetectWorker(QThread):
    finished = pyqtSignal(str, list)
    error = pyqtSignal(str, str)

    def __init__(self, video_path, threshold=30.0, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.threshold = threshold

    def run(self):
        try:
            from scenedetect import VideoManager, SceneManager
            from scenedetect.detectors import ContentDetector
            
            # Note: VideoManager is deprecated in PySceneDetect v0.6+ but keeping for compatibility
            # Use 'open_video' if using newer API, here we just follow the test script structure
            
            vm = VideoManager([self.video_path])
            sm = SceneManager()
            sm.add_detector(ContentDetector(threshold=self.threshold))
            
            vm.start()
            sm.detect_scenes(frame_source=vm)
            raw_scenes = sm.get_scene_list()

            scenes = []
            for i, (start, end) in enumerate(raw_scenes):
                s_sec = start.get_seconds()
                e_sec = end.get_seconds()
                dur = e_sec - s_sec
                scenes.append({
                    "idx": i + 1,
                    "start_sec": s_sec,
                    "end_sec": e_sec,
                    "start": start.get_timecode(),
                    "end": end.get_timecode(),
                    "dur": f"{dur:.1f}s",
                    "settings": {}  # Scene-level overrides
                })
            self.finished.emit(self.video_path, scenes)
        except Exception as e:
            self.error.emit(self.video_path, str(e))
