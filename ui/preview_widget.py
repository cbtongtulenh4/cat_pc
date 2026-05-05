"""
Preview Widget — Video display with player controls (play/pause, seek, time).
Uses python-mpv for real-time, hardware-accelerated, perfect-sync preview.
"""
import os
import sys
import ctypes

import mpv
from ctypes import c_int, c_void_p, cast, POINTER, pointer, Structure, c_char_p, c_size_t
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QSlider, QStyle, QStyleOptionSlider, QStackedLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QImage
from qfluentwidgets import CaptionLabel, ToolButton
from core.ffmpeg_builder import build_vf_string
from ui.crop_overlay import CropOverlayWidget
from ui.zoom_overlay import ZoomOverlayWidget
from ui.theme import Colors

# --- CTYPES DEFINITIONS FOR LIBMPV SOFTWARE RENDER ---
class MpvRenderParam(Structure):
    _fields_ = [('type_id', c_int), ('data', c_void_p)]

MPV_RENDER_PARAM_SW_SIZE = 17
MPV_RENDER_PARAM_SW_FORMAT = 18
MPV_RENDER_PARAM_SW_STRIDE = 19
MPV_RENDER_PARAM_SW_POINTER = 20

class _SeekSlider(QSlider):
    """QSlider subclass that jumps to clicked position instead of page-stepping."""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            groove = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt,
                QStyle.SubControl.SC_SliderGroove, self
            )
            handle = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt,
                QStyle.SubControl.SC_SliderHandle, self
            )
            if self.orientation() == Qt.Orientation.Horizontal:
                slider_len = handle.width()
                slider_min = groove.x()
                slider_max = groove.right() - slider_len + 1
                pos = event.position().x()
            else:
                slider_len = handle.height()
                slider_min = groove.y()
                slider_max = groove.bottom() - slider_len + 1
                pos = event.position().y()

            val = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(),
                int(pos - slider_min), slider_max - slider_min
            )
            self.setValue(val)
        super().mousePressEvent(event)


class PreviewWidget(QWidget):
    """Video preview panel with playback controls using MPV."""

    frame_changed = pyqtSignal(float)   # current time seconds
    crop_box_changed = pyqtSignal(dict)  # {x, y, width, height} in %
    zoom_box_changed = pyqtSignal(str, dict)  # {x, y, width, height} in canvas_px

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings: dict = {}
        self._is_playing = False
        self._duration = 0.0
        self._last_slider_val = -1        # track last slider value to skip redundant updates
        self._time_update_counter = 0     # throttle time label updates
        self._crop_mode = False            # True when interactive crop overlay is shown
        self._crop_box_pixels = None      # Stores {w, h, x, y} when applied
        self._zoom_mode = False
        self._zoom_scale = None
        self._canvas_ratio = None
        self._current_frame = None
        self._libmpv_render_func = None

        self.setStyleSheet(f"background-color: {Colors.BG_DARK};")
        self._init_ui()
        self._init_mpv()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video display area
        self._video_container = QWidget()
        self._video_container.setStyleSheet("background-color: black;")
        
        # Use QStackedLayout to keep video and overlay perfectly aligned
        self._video_stack = QStackedLayout(self._video_container)
        self._video_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self._video_stack.setContentsMargins(0, 0, 0, 0)
        
        # Bottom layer: MPV video canvas
        self.video_canvas = QWidget()
        self.video_canvas.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.video_canvas.paintEvent = self._canvas_paint_event
        self.video_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.video_canvas.setMinimumSize(0, 0)
        
        # Top layer: Crop overlay (child of video_canvas for better composition)
        self._crop_overlay = CropOverlayWidget(self.video_canvas)
        self._crop_overlay.hide()
        self._crop_overlay.crop_changed.connect(self._on_crop_changed)

        # Zoom overlay: parent = self (PreviewWidget) để có thể vẽ vượt ra ngoài canvas
        self._zoom_overlay = ZoomOverlayWidget(self)
        self._zoom_overlay.hide()
        self._zoom_overlay.zoom_changed.connect(self._on_zoom_changed)

        self._video_stack.addWidget(self.video_canvas)
        layout.addWidget(self._video_container, 1)

        # Player controls bar
        controls = QWidget()
        controls.setFixedHeight(44)
        controls.setStyleSheet(f"""
            background-color: {Colors.BG_MICA};
            border-top: 1px solid {Colors.BORDER_DIVIDER};
        """)
        c_layout = QHBoxLayout(controls)
        c_layout.setContentsMargins(16, 2, 16, 2)
        c_layout.setSpacing(10)

        # Play/Pause
        self._btn_play = ToolButton()
        self._btn_play.setText("▶")
        self._btn_play.setFixedSize(32, 32)
        self._btn_play.setStyleSheet(f"""
            QToolButton {{
                font-size: 14px;
                border-radius: 16px;
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                color: {Colors.TEXT};
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        self._btn_play.clicked.connect(self._toggle_play)
        c_layout.addWidget(self._btn_play)

        # Time display
        self._time_label = CaptionLabel("00:00 / 00:00")
        self._time_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-weight: 500;
            font-size: 12px;
            background: transparent;
        """)
        c_layout.addWidget(self._time_label)

        # Seek slider
        self._seek = _SeekSlider(Qt.Orientation.Horizontal)
        self._seek.setRange(0, 1000)
        self._seek.setValue(0)
        self._seek.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: none;
                height: 4px;
                background: rgba(255, 255, 255, 0.1);
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: white;
                border: 4px solid {Colors.ACCENT};
                width: 14px;
                height: 14px;
                margin: -7px 0;
                border-radius: 11px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {Colors.ACCENT_LIGHT};
                border-color: {Colors.ACCENT_LIGHT};
            }}
            QSlider::sub-page:horizontal {{
                background: {Colors.ACCENT};
                border-radius: 2px;
            }}
        """)
        self._seek.sliderPressed.connect(self._on_seek_press)
        self._seek.sliderReleased.connect(self._on_seek_release)
        c_layout.addWidget(self._seek, 1)

        layout.addWidget(controls)

    def _init_mpv(self):
        """Initialize MPV player with software rendering context."""
        try:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            bins_path = os.path.join(app_dir, "bins")
            if os.path.exists(bins_path):
                if hasattr(os, 'add_dll_directory'):
                    os.add_dll_directory(bins_path)
                os.environ["PATH"] = bins_path + os.pathsep + os.environ["PATH"]

            dll_names = ["libmpv-2.dll", "libmpv-1.dll", "mpv-1.dll"]
            for name in dll_names:
                try:
                    lib_path = os.path.join(bins_path, name)
                    if os.path.exists(lib_path):
                        lib = ctypes.CDLL(lib_path)
                        self._libmpv_render_func = lib.mpv_render_context_render
                        self._libmpv_render_func.argtypes = [c_void_p, POINTER(MpvRenderParam)]
                        self._libmpv_render_func.restype = c_int
                        break
                except:
                    continue

            self.player = mpv.MPV(
                vo="libmpv",
                start_event_thread=True
            )

            self.ctx = mpv.MpvRenderContext(self.player, 'sw')
            self.ctx.update_cb = self._on_mpv_update

            self.player['keep-open'] = 'yes'
            self.player['video-align-x'] = 0
            self.player['video-align-y'] = 0

            # Register observers for UI sync
            self.player.observe_property('pause', self._on_pause_changed)
            self.player.register_event_callback(self._on_mpv_event)

            # Setup UI update timer to poll MPV properties from the Main Thread (30fps)
            self._update_timer = QTimer(self)
            self._update_timer.setInterval(33)
            self._update_timer.timeout.connect(self._poll_mpv_properties)
            self._update_timer.start()
        except Exception as e:
            print(f"Error initializing MPV: {e}")

    def _on_mpv_update(self):
        """Called when MPV has a new frame. Triggers Qt repaint."""
        QTimer.singleShot(0, self.video_canvas.update)

    def _get_letterbox_rect(self, cw, ch):
        """Calculate the actual video rectangle within the container (letterboxing)."""
        try:
            params = self.player.video_params
            if not params or not params.get('w'):
                return QRectF(0, 0, cw, ch)
            
            vw, vh = params['w'], params['h']
            video_aspect = vw / vh
            container_aspect = cw / ch

            if container_aspect > video_aspect:
                # Pillarbox (black bars on sides)
                final_w = ch * video_aspect
                x = (cw - final_w) / 2
                return QRectF(x, 0, final_w, ch)
            else:
                # Letterbox (black bars top/bottom)
                final_h = cw / video_aspect
                y = (ch - final_h) / 2
                return QRectF(0, y, cw, final_h)
        except:
            return QRectF(0, 0, cw, ch)

    def _canvas_paint_event(self, event):
        """Paint the video frame."""
        painter = QPainter(self.video_canvas)
        w, h = self.video_canvas.width(), self.video_canvas.height()
        
        # CLEAR BACKGROUND to prevent ghosting
        painter.fillRect(self.video_canvas.rect(), Qt.GlobalColor.black)
        
        if not self._libmpv_render_func or w <= 0 or h <= 0:
            painter.end()
            return

        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.black)

        try:
            size = (c_int * 2)(w, h)
            fmt = c_char_p(b"bgra")
            stride = c_size_t(img.bytesPerLine())
            ptr = c_void_p(int(img.bits()))
            
            params = (MpvRenderParam * 5)(
                MpvRenderParam(MPV_RENDER_PARAM_SW_SIZE, cast(pointer(size), c_void_p)),
                MpvRenderParam(MPV_RENDER_PARAM_SW_FORMAT, cast(fmt, c_void_p)),
                MpvRenderParam(MPV_RENDER_PARAM_SW_STRIDE, cast(pointer(stride), c_void_p)),
                MpvRenderParam(MPV_RENDER_PARAM_SW_POINTER, ptr),
                MpvRenderParam(0, None)
            )
            self._libmpv_render_func(self.ctx.handle, params)
            painter.drawImage(0, 0, img)
            
            if self._crop_mode:
                # Calculate actual video area and update overlay
                video_rect = self._get_letterbox_rect(w, h)
                self._crop_overlay.set_video_rect(video_rect)

        except Exception as e:
            print(f"Render error: {e}")
        
        painter.end()

    def _on_mpv_event(self, event):
        """Handle MPV events (e.g. end of file)."""
        if event.event_id == mpv.MpvEventID.END_FILE:
            # Handle playback end if needed
            pass

    def _poll_mpv_properties(self):
        """Polls MPV properties on the Main UI Thread to avoid jerkiness."""
        if not hasattr(self, 'player'):
            return

        # 1. Update Duration
        duration = self.player.duration
        if duration and duration != self._duration:
            self._duration = duration

        # 2. Update Time Position
        time_pos = self.player.time_pos
        if time_pos is not None and self._duration > 0:
            # Only update slider if user is not actively dragging it
            if not self._seek.isSliderDown():
                new_val = int((time_pos / self._duration) * 1000)
                # Skip if value hasn't changed — avoids unnecessary repaint
                if new_val != self._last_slider_val:
                    self._last_slider_val = new_val
                    self._seek.setValue(new_val)

            # Throttle time label: update every ~3 ticks (~100ms) instead of every 33ms
            self._time_update_counter += 1
            if self._time_update_counter >= 3:
                self._time_update_counter = 0
                self._time_label.setText(f"{self._fmt(time_pos)} / {self._fmt(self._duration)}")

            # Emit frame_changed (throttled along with time label)
            self.frame_changed.emit(time_pos)

    # ── Public API ──

    def seek_to(self, target_time: float):
        """Seek video to a specific time in seconds."""
        if hasattr(self, 'player') and self._duration > 0:
            try:
                self.player.command('seek', target_time, 'absolute')
                self.player.pause = True
            except Exception as e:
                print(f"Seek error: {e}")

    def load_video(self, path: str):
        """Load a video file for preview."""
        if not os.path.exists(path):
            return
        
        self.player.play(path)
        self.player.pause = True # Start paused
        # Delay geometry update slightly to allow MPV to load metadata
        QTimer.singleShot(200, self._update_overlay_geometry)

    def update_settings(self, settings: dict):
        """Update filter settings and refresh."""
        self._settings = settings
        
        self._canvas_ratio = settings.get("canvas_ratio_val")
        self._update_container_aspect()
        
        # Build filter list
        vf_list = []
        
        # 1. Add Crop Filter if applied and NOT currently in crop-selection mode
        crop_box = settings.get("crop_box")
        if crop_box and not self._crop_mode:
            try:
                p = self.player.video_params
                vw, vh = p.get('w', 0), p.get('h', 0)
                if vw and vh:
                    cw = int(vw * crop_box['width'] / 100)
                    ch = int(vh * crop_box['height'] / 100)
                    cx = int(vw * crop_box['x'] / 100)
                    cy = int(vh * crop_box['y'] / 100)
                    vf_list.append(f"crop={cw}:{ch}:{cx}:{cy}")
            except Exception as e:
                pass
            
        # 2. Add other settings (speed, color, etc.)
        other_vfs = build_vf_string(settings, for_preview=True)
        # Strip internal crop if we are using our own
        other_vfs = [f for f in other_vfs if not f.startswith("crop=")]
        vf_list.extend(other_vfs)
        
        vf_str = ",".join(vf_list) if vf_list else ""
        
        bg_type = settings.get("bg_type", "black")
        is_blur_bg = (self._canvas_ratio and bg_type == "blur" and not self._zoom_mode and not self._crop_mode)
        
        # Apply to MPV
        try:
            zoom_box = settings.get("zoom_box")
            
            # Unified Canvas Rendering Logic
            # If we have a target canvas ratio, we should explicitly render on a canvas
            # to handle centering, scaling, and background styles correctly.
            if self._canvas_ratio and not self._crop_mode:
                cw = 720
                ch = int(720 / float(self._canvas_ratio))
                cw, ch = (cw//2)*2, (ch//2)*2
                
                pre_filters = f"{vf_str}[v0];[v0]" if vf_str else ""
                
                # 1. Build Background
                if bg_type == "blur":
                    strength = settings.get("bg_blur_strength", 40)
                    bg_filter = f"scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},boxblur={strength}:5"
                else:
                    # Black Background
                    bg_filter = f"scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill"
                
                # 2. Build Foreground (Video content)
                if zoom_box:
                    video_w = (int(float(zoom_box['width'])) // 2) * 2
                    video_h = (int(float(zoom_box['height'])) // 2) * 2
                    target_x = int(float(zoom_box['x']))
                    target_y = int(float(zoom_box['y']))
                    fg_filter = f"scale={video_w}:{video_h}"
                    overlay_pos = f"{target_x}:{target_y}"
                else:
                    # Default: Center and Fit (Contain)
                    fg_filter = f"scale={cw}:{ch}:force_original_aspect_ratio=decrease"
                    overlay_pos = "(W-w)/2:(H-h)/2"
                
                fc = (
                    f"{pre_filters}split[v1][v2];"
                    f"[v1]{bg_filter}[bg];"
                    f"[v2]{fg_filter}[fg];"
                    f"[bg][fg]overlay={overlay_pos}:shortest=1"
                )
                self.player.vf = f"lavfi=[{fc}]"
                self.player['keepaspect'] = 'no'
                
            elif vf_str:
                # Basic mode (Original ratio)
                self.player.vf = f"lavfi=[{vf_str}]"
                self.player['keepaspect'] = 'yes'
            else:
                # Reset
                self.player.vf = ""
                self.player['keepaspect'] = 'yes'
        except Exception as e:
            print(f"Filter error: {e}")
        
        # Also handle speed and audio muted here if needed
        speed = settings.get("speed_value")
        if speed:
            self.player.speed = speed
            
        remove_audio = settings.get("remove_audio", False)
        self.player.mute = remove_audio

    # ── Crop Mode API ──

    def enter_crop_mode(self, initial_box: dict | None = None, aspect_ratio: float | None = None):
        """Show the interactive crop overlay on top of the video."""
        self._crop_mode = True
        if initial_box:
            self._crop_overlay.set_box(initial_box)
        else:
            self._crop_overlay.set_box({"x": 0, "y": 0, "width": 100, "height": 100})
        self._crop_overlay.set_aspect_ratio(aspect_ratio)
        self._crop_overlay.show()
        self._crop_overlay.raise_()
        # Strip crop filter from MPV so user sees full video
        self.update_settings(self._settings)

    def exit_crop_mode(self, apply: bool = False):
        """Hide the crop overlay and re-apply full filters."""
        self._crop_mode = False
        self._crop_overlay.hide()
        self.update_settings(self._settings)

    def reset_crop(self):
        """Clear the crop and refresh video."""
        self._crop_mode = False
        self._crop_overlay.hide()
        self.update_settings(self._settings)

    def is_crop_mode(self) -> bool:
        return self._crop_mode

    def set_crop_aspect_ratio(self, ratio: float | None):
        """Update the aspect ratio of the active crop overlay."""
        self._crop_overlay.set_aspect_ratio(ratio)

    def set_zoom_aspect_ratio(self, ratio: float | None):
        """Update the aspect ratio of the active zoom overlay."""
        self._zoom_overlay.set_aspect_ratio(ratio)

    def _on_crop_changed(self, box: dict):
        """Called when user finishes dragging the crop frame."""
        self.crop_box_changed.emit(box)

    # ── Zoom Mode API ──

    def enter_zoom_mode(self, initial_box: dict = None, aspect_ratio: float = None):
        """Enable interactive zoom/scale overlay."""
        """Enable interactive zoom/scale overlay."""
        self._zoom_mode = True
        
        # Calculate canvas size
        c_w = 720
        c_h = int(720 / float(self._canvas_ratio)) if self._canvas_ratio else 1280
        c_w, c_h = (c_w//2)*2, (c_h//2)*2
        
        # Determine offset of video_container
        offset = QPointF(0, 0)
        size = QRectF(0, 0, self._video_container.width(), self._video_container.height())
        self._zoom_overlay.set_canvas_offset(offset, size)
        
        # Set aspect ratio constraint
        self._zoom_overlay.set_aspect_ratio(aspect_ratio)
        
        if initial_box:
            # {x, y, w, h} in canvas coordinates -> convert to widget
            w_w = self._video_container.width()
            w_h = self._video_container.height()
            sx = w_w / c_w
            sy = w_h / c_h
            
            wx = initial_box['x'] * sx
            wy = initial_box['y'] * sy
            ww = initial_box['width'] * sx
            wh = initial_box['height'] * sy
            
            self._zoom_overlay.set_box(QRectF(wx, wy, ww, wh))
        else:
            try:
                p = self.player.video_params
                video_ar = p.get('w', 1920) / p.get('h', 1080)
            except:
                video_ar = 16/9
                
            canvas_ar = c_w / c_h
            if video_ar > canvas_ar:
                fit_w = c_w
                fit_h = c_w / video_ar
            else:
                fit_h = c_h
                fit_w = c_h * video_ar
                
            cx = (c_w - fit_w) / 2
            cy = (c_h - fit_h) / 2
            
            w_w = self._video_container.width()
            w_h = self._video_container.height()
            sx = w_w / c_w
            sy = w_h / c_h
            
            wx = cx * sx
            wy = cy * sy
            ww = fit_w * sx
            wh = fit_h * sy
            
            self._zoom_overlay.set_box(QRectF(wx, wy, ww, wh))
            
        # Phủ toàn bộ PreviewWidget, không chỉ _video_container
        self._zoom_overlay.setGeometry(0, 0, self.width(), self.height())
        self._update_zoom_geometry()
        self._zoom_overlay.show()
        self._zoom_overlay.raise_()
        self._on_zoom_changed(self._zoom_overlay.get_box())

    def exit_zoom_mode(self, apply: bool = False):
        """Hide the zoom overlay and apply scale."""
        self._zoom_mode = False
        self._zoom_overlay.hide()
        self.update_settings(self._settings)

    def reset_zoom(self):
        """Clear the zoom scale."""
        self._zoom_mode = False
        self._zoom_overlay.hide()
        self.update_settings(self._settings)

    def is_zoom_mode(self) -> bool:
        return self._zoom_mode

    def _on_zoom_changed(self, box: QRectF | dict):
        b = box if isinstance(box, QRectF) else QRectF(box['x'], box['y'], box['width'], box['height'])
        
        w_w = self._video_container.width()
        w_h = self._video_container.height()
        c_w = 720
        c_h = int(720 / float(self._canvas_ratio)) if self._canvas_ratio else 1280
        c_w, c_h = (c_w//2)*2, (c_h//2)*2
        
        sx = c_w / w_w
        sy = c_h / w_h
        
        cx = b.x() * sx
        cy = b.y() * sy
        cw = b.width() * sx
        ch = b.height() * sy
        
        self._zoom_scale = {
            'x': cx,
            'y': cy,
            'width': cw,
            'height': ch
        }
        
        info = f"Video Pos: {int(cw)}x{int(ch)} tại X:{int(cx)}, Y:{int(cy)}"
        self.zoom_box_changed.emit(info, self._zoom_scale)

    # ── Playback ──

    def _toggle_play(self):
        # If we reached the end of the video, seek to 0 before unpausing
        if self.player.eof_reached or (self._duration > 0 and self.player.time_pos and self.player.time_pos >= self._duration - 0.1):
            self.player.seek(0, reference="absolute")
            self.player.pause = False
        else:
            self.player.pause = not self.player.pause

    def _on_pause_changed(self, name, paused):
        self._is_playing = not paused
        self._btn_play.setText("▶" if paused else "⏸")

    def _on_seek_press(self):
        self._was_playing = not self.player.pause
        self.player.pause = True

    def _on_seek_release(self):
        if self._duration > 0:
            try:
                target_time = (self._seek.value() / 1000) * self._duration
                # Use raw command for better compatibility
                self.player.command('seek', target_time, 'absolute')
            except Exception as e:
                print(f"Seek error: {e}")
            
        if self._was_playing:
            self.player.pause = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_container_aspect()
        self._update_overlay_geometry()

    def _update_container_aspect(self):
        ratio = self._canvas_ratio
        if ratio is None:
            self._video_container.setMinimumSize(0, 0)
            self._video_container.setMaximumSize(16777215, 16777215)
            if hasattr(self, 'player'):
                self.player['keepaspect'] = 'yes'
            return
            
        max_w = self.width()
        max_h = self.height() - 44
        if max_w <= 0 or max_h <= 0:
            return
            
        target_w = max_w
        target_h = target_w / ratio
        
        if target_h > max_h:
            target_h = max_h
            target_w = target_h * ratio
            
        self._video_container.setFixedSize(int(target_w), int(target_h))
        self.layout().setAlignment(self._video_container, Qt.AlignmentFlag.AlignCenter)
        # Không set keepaspect ở đây — update_settings sẽ quyết định giá trị đúng
        # tùy thuộc vào bg_type và zoom_box

    def _update_overlay_geometry(self):
        """Calculate actual video rectangle (letterbox) and resize overlay to match it."""
        if not hasattr(self, 'video_canvas') or not self._video_container.width():
            return
            
        # Fit video_canvas to container
        self.video_canvas.setGeometry(0, 0, self._video_container.width(), self._video_container.height())
        
        # Calculate video rect
        try:
            params = self.player.video_params
            vw = params.get('w')
            vh = params.get('h')
        except:
            vw, vh = 0, 0
            
        if not vw or not vh:
            # Fallback to full container if no video metadata
            self._crop_overlay.setGeometry(0, 0, self._video_container.width(), self._video_container.height())
            return

        cw = self._video_container.width()
        ch = self._video_container.height()
        
        video_ratio = vw / vh
        container_ratio = cw / ch
        
        if video_ratio > container_ratio:
            # Pillarbox (black bars top/bottom)
            rw = cw
            rh = cw / video_ratio
        else:
            # Letterbox (black bars left/right)
            rh = ch
            rw = ch * video_ratio
            
        rx = (cw - rw) / 2
        ry = (ch - rh) / 2
        
        # Overlay now fills its parent (video_canvas)
        self._crop_overlay.setGeometry(0, 0, int(cw), int(ch))
        
        self._crop_overlay.set_video_rect(QRectF(rx, ry, rw, rh))
        
        # Zoom overlay phủ toàn bộ PreviewWidget (không phải _video_container)
        self._zoom_overlay.setGeometry(0, 0, self.width(), self.height())
        self._update_zoom_geometry()

    def _update_zoom_geometry(self):
        if not hasattr(self, '_zoom_overlay') or not self._video_container.width():
            return
        
        # Tính offset: vị trí _video_container trong PreviewWidget (self)
        vc = self._video_container
        pos = vc.mapTo(self, vc.rect().topLeft())
        offset = QPointF(pos.x(), pos.y())
        size = QRectF(0, 0, vc.width(), vc.height())
        self._zoom_overlay.set_canvas_offset(offset, size)
        
        if self._zoom_scale and self._canvas_ratio:
            c_w = 720
            c_h = int(720 / float(self._canvas_ratio))
            c_w, c_h = (c_w//2)*2, (c_h//2)*2
            
            w_w = vc.width()
            w_h = vc.height()
            sx = w_w / c_w
            sy = w_h / c_h
            
            wx = self._zoom_scale['x'] * sx
            wy = self._zoom_scale['y'] * sy
            ww = self._zoom_scale['width'] * sx
            wh = self._zoom_scale['height'] * sy
            self._zoom_overlay.set_box(QRectF(wx, wy, ww, wh))

    @staticmethod
    def _fmt(s: float) -> str:
        if s is None:
            return "00:00"
        return f"{int(s) // 60:02d}:{int(s) % 60:02d}"

    def closeEvent(self, event):
        """Clean up MPV player."""
        if hasattr(self, 'player'):
            self.player.terminate()
        super().closeEvent(event)
