"""
Batch video processor.
Migrated from demo_server/app.py — run_edit_videos.
Uses QThread + BatchSignals instead of Flask SSE + Queue.
"""
import os
import threading
import subprocess
import concurrent.futures
import logging

from PyQt6.QtCore import QThread

from batch.worker_signals import BatchSignals
from core.ffmpeg_builder import build_ffmpeg_cmds
from core.gpu_detect import get_hardware_encoder, get_encoder_preset
from core.config import FFMPEG_PATH, FFPROBE_PATH

logger = logging.getLogger("batch_processor")

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.wmv', '.m4v', '.3gp')


class BatchProcessor(QThread):
    """
    Process a batch of video files using FFmpeg in a separate thread.
    Emits progress through BatchSignals.
    """

    def __init__(
        self,
        files: list[dict],
        save_path: str,
        output_format: str,
        settings: dict,
        max_workers: int = 1,
        delete_original: bool = False,
        use_gpu: bool = True,
        parent=None,
        batch_tasks: list[dict] = None,
        recipe=None
    ):
        super().__init__(parent)
        self.signals = BatchSignals()
        self.files = files
        self.batch_tasks = batch_tasks if batch_tasks is not None else []
        self.save_path = save_path
        self.output_format = output_format
        self.settings = settings
        self.max_workers = max(1, min(os.cpu_count() or 4, max_workers))
        self.delete_original = delete_original
        self.use_gpu = use_gpu
        self.recipe = recipe  # PresetRecipe | None — for auto-detect per-scene

        self._cancel_event = threading.Event()
        self._active_procs: list[subprocess.Popen] = []
        self._proc_lock = threading.Lock()

    def cancel(self):
        """Request cancellation and kill all running ffmpeg processes."""
        self._cancel_event.set()
        with self._proc_lock:
            for proc in self._active_procs:
                try:
                    proc.terminate()
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

    def run(self):
        """Main batch processing logic (runs in QThread)."""
        try:
            if not self.files:
                self.signals.error.emit("Không tìm thấy video nào để xử lý")
                return

            total_files = len(self.files)
            self.signals.started.emit(total_files)

            os.makedirs(self.save_path, exist_ok=True)

            ext = self.output_format.lower()
            encoder = get_hardware_encoder(ext) if self.use_gpu else None

            completed_files = 0
            skipped_count = 0

            # Phase 1: Build all tasks
            all_tasks = []
            file_tracker = {}

            # We will use self.batch_tasks if provided
            tasks_to_process = self.batch_tasks if self.batch_tasks else [{"file_info": f, "settings": self.settings, "scenes": []} for f in self.files]

            for task in tasks_to_process:
                if self._cancel_event.is_set():
                    break

                file_obj = task["file_info"]
                video_settings = dict(task["settings"])
                scenes = list(task.get("scenes", []))

                input_path = file_obj['path']
                filename = file_obj['name']
                base_name = os.path.splitext(filename)[0]
                rel_dir = file_obj.get('rel_dir', '')

                try:
                    # Resolve full output directory
                    current_save_path = os.path.join(self.save_path, rel_dir) if rel_dir else self.save_path
                    os.makedirs(current_save_path, exist_ok=True)
                    
                    self.signals.log.emit(f"🚀 Processing: {filename} -> {rel_dir}")
                    self.signals.file_progress.emit(input_path, 0)

                    # --- AUTO DETECT SCENES ---
                    scene_split_enabled = video_settings.get("scene_split_enabled", False)
                    if scene_split_enabled and not scenes:
                        self.signals.log.emit(f"   => Auto-detecting scenes for {filename}...")
                        try:
                            from scenedetect import VideoManager, SceneManager
                            from scenedetect.detectors import ContentDetector
                            
                            threshold = float(video_settings.get("scene_split_threshold", 30))
                            vm = VideoManager([input_path])
                            sm = SceneManager()
                            sm.add_detector(ContentDetector(threshold=threshold))
                            
                            vm.start()
                            sm.detect_scenes(frame_source=vm)
                            raw_scenes = sm.get_scene_list()

                            for i, (start, end) in enumerate(raw_scenes):
                                s_sec = start.get_seconds()
                                e_sec = end.get_seconds()
                                scenes.append({
                                    "scene_data": {
                                        "idx": i + 1,
                                        "start_sec": s_sec,
                                        "end_sec": e_sec,
                                        "checked": True
                                    },
                                    "settings": dict(video_settings)
                                })
                            self.signals.log.emit(f"   => Detected {len(scenes)} scenes.")

                            # Apply recipe per-scene logic if available
                            if self.recipe and self.recipe.has_per_scene_logic:
                                raw = file_obj.get('raw_info', {})
                                v_w = raw.get('width', 0)
                                v_h = raw.get('height', 0)
                                if v_w <= 0 or v_h <= 0:
                                    # Fallback: get dimensions from ffprobe
                                    try:
                                        from core.video_info import get_video_width, get_video_height
                                        v_w = get_video_width(input_path, FFPROBE_PATH)
                                        v_h = get_video_height(input_path, FFPROBE_PATH)
                                    except Exception:
                                        v_w, v_h = 1920, 1080
                                self.recipe.apply_per_scene(scenes, v_w, v_h)
                                self.signals.log.emit(f"   => Applied preset '{self.recipe.name}' per-scene settings.")

                        except Exception as e:
                            logger.error(f"Auto-detect failed for {filename}: {e}")
                            self.signals.log.emit(f"   => Auto-detect failed: {e}")

                    # --- PREPARE SETTINGS FOR BUILDER ---
                    # Format scenes list for the ffmpeg_builder
                    video_settings["scenes"] = []
                    for sc in scenes:
                        sc_dict = dict(sc["scene_data"])
                        sc_dict["settings_override"] = sc["settings"]
                        video_settings["scenes"].append(sc_dict)

                    cmds_and_outputs = build_ffmpeg_cmds(
                        input_path, current_save_path, base_name, ext,
                        video_settings,
                        ffmpeg_path=FFMPEG_PATH, ffprobe_path=FFPROBE_PATH
                    )

                    if not cmds_and_outputs:
                        skipped_count += 1
                        completed_files += 1
                        self.signals.file_done.emit(input_path, "skipped", completed_files, "No commands generated (check settings)")
                        continue

                    needs_merge = scene_split_enabled and video_settings.get("scene_merge_enabled", True)

                    total_segs = len(cmds_and_outputs)
                    file_tracker[input_path] = {
                        'total': total_segs,
                        'completed': 0,
                        'has_error': False,
                        'error_msg': "",
                        'created_files': [],
                        'file_obj': file_obj,
                        'needs_merge': needs_merge,
                        'final_output_path': os.path.join(current_save_path, f"{base_name}.{ext}")
                    }

                    for cmd_info in cmds_and_outputs:
                        all_tasks.append((file_obj, cmd_info, total_segs))
                        # print(cmd_info)

                except Exception as e:
                    logger.warning(f"Skipping video {input_path} due to error: {e}")
                    skipped_count += 1
                    completed_files += 1
                    self.signals.file_done.emit(input_path, "skipped", completed_files, f"Init error: {e}")

            self.signals.log.emit(
                f"Tổng: {len(all_tasks)} segments từ {total_files} files, workers={self.max_workers}"
            )

            # Phase 2: Execute all tasks
            progress_lock = threading.Lock()
            try:
                cpu_count = os.cpu_count() or 4
                max_threads = max(1, cpu_count // self.max_workers)
            except Exception:
                max_threads = 2

            def process_one_segment(task):
                nonlocal completed_files
                file_obj, cmd_info, total_segs = task
                input_path = file_obj['path']
                cmd = list(cmd_info["cmd"])
                output_path = cmd_info["output_path"]
                is_stream_copy = cmd_info.get("stream_copy", False)

                if self._cancel_event.is_set():
                    return

                # --- UUID Temp File Strategy for Segments ---
                import uuid
                temp_output = os.path.join(os.path.dirname(output_path), f"temp_seg_{uuid.uuid4().hex}.mp4")
                
                # Replace the last argument (which is output_path) with temp_output
                if cmd[-1] == output_path:
                    cmd[-1] = temp_output
                else:
                    logger.warning("Lệnh FFmpeg không có output_path ở cuối cùng, có thể gây lỗi file ảo.")

                # --- START FULL LOGGING ---
                logger.info(f"[{os.path.basename(output_path)}] Bắt đầu xử lý segment. (Stream Copy: {is_stream_copy})")
                self.signals.log.emit(f"   => [Segment Start] {os.path.basename(output_path)}")

                try:
                    cflags = 0
                    if os.name == 'nt':
                        cflags = subprocess.CREATE_NO_WINDOW | 0x00004000

                    success = False

                    def _run_ffmpeg(ffmpeg_cmd):
                        if self._cancel_event.is_set():
                            return None, "", True
                        proc = subprocess.Popen(
                            ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            encoding='utf-8', errors='replace', creationflags=cflags
                        )
                        with self._proc_lock:
                            self._active_procs.append(proc)
                        _, err = proc.communicate()
                        with self._proc_lock:
                            try:
                                self._active_procs.remove(proc)
                            except ValueError:
                                pass
                        cancelled = self._cancel_event.is_set()
                        return proc, err, cancelled

                    # Try GPU first
                    if encoder and self.use_gpu:
                        gpu_cmd = list(cmd)
                        gpu_cmd.insert(-1, "-c:v")
                        gpu_cmd.insert(-1, encoder)
                        preset_args = get_encoder_preset(encoder)
                        gpu_cmd = gpu_cmd[:-1] + preset_args + [gpu_cmd[-1]]

                        logger.info(f"[{os.path.basename(output_path)}] Chạy lệnh GPU: {' '.join(gpu_cmd)}")
                        self.signals.log.emit(f"   => [GPU] Đang render: {os.path.basename(output_path)}")
                        
                        proc, err, cancelled = _run_ffmpeg(gpu_cmd)
                        
                        logger.info(f"[{os.path.basename(output_path)}] Kết quả GPU: Return Code={proc.returncode if proc else 'None'}, Cancelled={cancelled}")
                        
                        if cancelled:
                            if os.path.exists(temp_output):
                                try: os.remove(temp_output)
                                except: pass
                            return
                        if proc and proc.returncode == 0:
                            try:
                                if os.path.exists(output_path):
                                    os.remove(output_path)
                                os.rename(temp_output, output_path)
                                success = True
                                logger.info(f"[{os.path.basename(output_path)}] Render GPU THÀNH CÔNG.")
                                self.signals.log.emit(f"   => [Thành công] {os.path.basename(output_path)} (GPU)")
                            except Exception as e:
                                logger.error(f"Lỗi khi đổi tên từ {temp_output} sang {output_path}: {e}")
                        elif proc:
                            logger.warning(f"[{os.path.basename(output_path)}] GPU THẤT BẠI. Lỗi FFmpeg:\n{err[:1000]}")
                            self.signals.log.emit(f"   => [Cảnh báo] Render GPU thất bại, chuyển sang CPU...")
                            if os.path.exists(temp_output):
                                try: os.remove(temp_output)
                                except: pass

                    # CPU fallback
                    if not success:
                        cpu_cmd = list(cmd)
                        preset_args = get_encoder_preset(None)
                        cpu_cmd = cpu_cmd[:-1] + preset_args + [cpu_cmd[-1]]

                        logger.info(f"[{os.path.basename(output_path)}] Chạy lệnh CPU: {' '.join(cpu_cmd)}")
                        self.signals.log.emit(f"   => [CPU] Đang render: {os.path.basename(output_path)}")

                        proc, err, cancelled = _run_ffmpeg(cpu_cmd)
                        
                        logger.info(f"[{os.path.basename(output_path)}] Kết quả CPU: Return Code={proc.returncode if proc else 'None'}, Cancelled={cancelled}")
                        
                        if cancelled:
                            if os.path.exists(temp_output):
                                try: os.remove(temp_output)
                                except: pass
                            return
                        if proc and proc.returncode == 0:
                            try:
                                if os.path.exists(output_path):
                                    os.remove(output_path)
                                os.rename(temp_output, output_path)
                                success = True
                                logger.info(f"[{os.path.basename(output_path)}] Render CPU THÀNH CÔNG.")
                                self.signals.log.emit(f"   => [Thành công] {os.path.basename(output_path)} (CPU)")
                            except Exception as e:
                                logger.error(f"Lỗi khi đổi tên từ {temp_output} sang {output_path}: {e}")
                        elif proc:
                            logger.error(f"FFMPEG Error: {err[:2000]}")
                            if os.path.exists(temp_output):
                                try: os.remove(temp_output)
                                except: pass

                    # Update tracker
                    with progress_lock:
                        tracker = file_tracker[input_path]
                        tracker['completed'] += 1

                        if success:
                            tracker['created_files'].append(output_path)
                            logger.info(f"[Tracker] Video {os.path.basename(input_path)} đã hoàn thành {tracker['completed']}/{tracker['total']} segments.")
                        else:
                            tracker['has_error'] = True
                            if not tracker['error_msg']:
                                tracker['error_msg'] = (err[:200] + "...") if err else "FFmpeg execution failed"
                            logger.error(f"[Tracker] Lỗi xảy ra tại segment {os.path.basename(output_path)}! Đánh dấu has_error=True.")

                        if tracker['completed'] >= tracker['total']:
                            logger.info(f"[Tracker] Video {os.path.basename(input_path)} đã xong TẤT CẢ ({tracker['completed']}/{tracker['total']}). Bắt đầu bước cuối.")
                            completed_files += 1
                            if tracker['has_error']:
                                logger.warning(f"[Tracker] Video có lỗi trước đó. Xóa toàn bộ file tạm.")
                                status = 'error'
                                for f in tracker['created_files']:
                                    try:
                                        if os.path.exists(f):
                                            os.remove(f)
                                    except:
                                        pass
                            else:
                                if tracker.get('needs_merge') and len(tracker['created_files']) > 1:
                                    logger.info(f"[Tracker] Điều kiện GỘP FILE thỏa mãn. Số lượng: {len(tracker['created_files'])}")
                                    # Perform merge
                                    import uuid
                                    sorted_files = sorted(tracker['created_files'])
                                    # Tạo file text chứa list
                                    list_file = os.path.join(os.path.dirname(tracker['final_output_path']), f"concat_list_{uuid.uuid4().hex}.txt")
                                    with open(list_file, 'w', encoding='utf-8') as f:
                                        for tf in sorted_files:
                                            safe_path = tf.replace('\\', '/')
                                            f.write(f"file '{safe_path}'\n")
                                    
                                    # Tạo tên ảo cho file output gộp để tránh FFmpeg lỗi Unicode
                                    temp_output = os.path.join(os.path.dirname(tracker['final_output_path']), f"temp_merge_{uuid.uuid4().hex}.mp4")
                                    
                                    merge_cmd = [
                                        FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0",
                                        "-i", list_file, "-c", "copy", temp_output
                                    ]
                                    
                                    logger.info(f"[Merge] Chạy lệnh gộp: {' '.join(merge_cmd)}")
                                    self.signals.log.emit(f"   => Đang gộp {len(sorted_files)} cảnh thành 1 file...")
                                    
                                    cflags = subprocess.CREATE_NO_WINDOW | 0x00004000 if os.name == 'nt' else 0
                                    proc = subprocess.Popen(
                                        merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        encoding='utf-8', errors='replace', creationflags=cflags
                                    )
                                    _, err = proc.communicate()
                                    
                                    logger.info(f"[Merge] Kết quả lệnh gộp: Return Code={proc.returncode}")
                                    
                                    try: os.remove(list_file)
                                    except: pass
                                        
                                    if proc.returncode == 0:
                                        # Thành công: Đổi tên ảo thành tên thật
                                        try:
                                            if os.path.exists(tracker['final_output_path']):
                                                os.remove(tracker['final_output_path'])
                                            os.rename(temp_output, tracker['final_output_path'])
                                        except Exception as e:
                                            logger.error(f"[Merge] Lỗi khi đổi tên file temp thành file chính: {e}")
                                            
                                        logger.info(f"[Merge] Gộp và đổi tên thành công! Đang dọn dẹp file tạm.")
                                        status = 'done'
                                        # Delete segments
                                        for f in sorted_files:
                                            try: os.remove(f)
                                            except: pass
                                    else:
                                        if os.path.exists(temp_output):
                                            try: os.remove(temp_output)
                                            except: pass
                                        logger.error(f"[Merge] LỖI khi gộp! FFmpeg Error:\n{err[:1000]}")
                                        status = 'error'
                                        tracker['error_msg'] = f"Lỗi khi gộp file: {err[:500]}"
                                else:
                                    logger.info(f"[Tracker] Bỏ qua bước gộp (needs_merge={tracker.get('needs_merge')}, số file={len(tracker['created_files'])})")
                                    status = 'done' # success -> done
                                    
                                if status == 'done' and self.delete_original:
                                    try:
                                        os.remove(input_path)
                                    except Exception as e:
                                        logger.error(f"Failed to delete original: {e}")

                            self.signals.file_done.emit(input_path, status, completed_files, tracker.get('error_msg', ""))
                        else:
                            pct = int((tracker['completed'] / tracker['total']) * 100)
                            self.signals.file_progress.emit(input_path, pct)

                except Exception as e:
                    logger.exception(f"Exception processing segment for {input_path}")
                    with progress_lock:
                        tracker = file_tracker[input_path]
                        tracker['completed'] += 1
                        tracker['has_error'] = True
                        if tracker['completed'] >= tracker['total']:
                            completed_files += 1
                            for f in tracker['created_files']:
                                try:
                                    if os.path.exists(f): os.remove(f)
                                except: pass
                            self.signals.file_done.emit(input_path, "error", completed_files, str(e))

            # Execute
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                list(executor.map(process_one_segment, all_tasks))

            if self._cancel_event.is_set():
                # Emit skip for remaining files
                for input_path, tracker in file_tracker.items():
                    if tracker['completed'] < tracker['total']:
                        self.signals.file_done.emit(input_path, "skipped", completed_files, "Cancelled by user")
                
                self.signals.cancelled.emit(total_files)
            else:
                self.signals.completed.emit(total_files, completed_files, skipped_count)

        except Exception as e:
            logger.exception("Error in batch processing")
            self.signals.error.emit(str(e))
