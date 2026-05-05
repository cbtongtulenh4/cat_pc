"""
FFmpeg command builder.
Migrated from demo_server/video_editor.py — build_ffmpeg_cmds, calculate_split_segments.
"""
import os
import math
import random
import logging

from core.config import FFMPEG_PATH, FFPROBE_PATH
from core.video_info import get_video_duration, get_video_height

logger = logging.getLogger("ffmpeg_builder")


def calculate_split_segments(T: float, min_d: float, max_d: float, target_k: int = 0) -> list[float]:
    """
    Calculate random split segment durations.
    
    Args:
        T: Total video duration in seconds
        min_d: Minimum segment duration
        max_d: Maximum segment duration
        target_k: Fixed number of segments (0 = auto)
    
    Returns:
        List of segment durations that sum to T
    """
    # Validation for fixed N segments
    if target_k > 0:
        if T < target_k * min_d:
            raise ValueError(
                f"Video ({T:.2f}s) quá ngắn để chia làm {target_k} phần "
                f"(Yêu cầu tối thiểu {target_k * min_d:.1f}s)"
            )
        if T > target_k * max_d:
            raise ValueError(
                f"Video ({T:.2f}s) quá dài để chia làm {target_k} phần "
                f"(Yêu cầu tối đa {target_k * max_d:.1f}s)"
            )

        segments = []
        remaining = T
        for i in range(target_k, 1, -1):
            lb = max(min_d, remaining - (i - 1) * max_d)
            ub = min(max_d, remaining - (i - 1) * min_d)
            d = random.uniform(lb, ub)
            segments.append(d)
            remaining -= d
        segments.append(remaining)
        return segments

    # Original logic for random duration-based split
    if min_d > max_d:
        min_d, max_d = max_d, min_d

    k_min = math.ceil(T / max_d) if max_d > 0 else 1
    k_max = math.floor(T / min_d) if min_d > 0 else 1

    if k_min > k_max:
        raise ValueError(f"Không thể chia nhỏ video ({T:.2f}s) với khoảng [{min_d}-{max_d}]s")

    k = random.randint(k_min, k_max)
    segments = []
    remaining = T
    for i in range(k, 1, -1):
        lower_bound = max(min_d, remaining - (i - 1) * max_d)
        upper_bound = min(max_d, remaining - (i - 1) * min_d)
        d = random.uniform(lower_bound, upper_bound)
        segments.append(d)
        remaining -= d
    segments.append(remaining)
    return segments


def build_vf_string(settings: dict, for_preview: bool = False) -> list[str]:
    """
    Build the list of FFmpeg video filters (-vf) based on settings.
    This logic is shared between the final render and the MPV preview.
    """
    vf_filters = []

    # 1. Speed
    speed = settings.get("speed_value")
    if speed and speed != 1.0 and not for_preview:
        vf_filters.append(f"setpts={1/speed}*PTS")

    # 2. Crop
    crop_box = settings.get("crop_box")
    crop_ratio = settings.get("crop_ratio")

    if crop_box:
        # Get actual video size for validation if available in settings (optional but safer)
        v_w = settings.get("_video_width", 0)
        v_h = settings.get("_video_height", 0)

        x_p = crop_box.get("x", 0) / 100
        y_p = crop_box.get("y", 0) / 100
        w_p = crop_box.get("width", 100) / 100
        h_p = crop_box.get("height", 100) / 100
        
        # Internal validation as fail-safe
        if v_w > 0 and v_h > 0:
            cx, cy = v_w * x_p, v_h * y_p
            cw, ch = v_w * w_p, v_h * h_p
            if cx < 0 or cy < 0 or (cx + cw) > (v_w + 1) or (cy + ch) > (v_h + 1):
                raise ValueError(f"Vùng Crop ({int(cw)}x{int(ch)}) vượt quá kích thước video ({v_w}x{v_h})")

        vf_filters.append(
            f"crop=iw*{w_p:.4f}:ih*{h_p:.4f}:iw*{x_p:.4f}:ih*{y_p:.4f}"
        )
    elif crop_ratio and crop_ratio != "original":
        try:
            w_r, h_r = map(int, crop_ratio.split(':'))
            r_str = f"{(w_r / h_r):.4f}"
            vf_filters.append(
                f"crop='if(gt(a,{r_str}),ih*{r_str},iw)':'if(gt(a,{r_str}),ih,iw/{r_str})'"
            )
        except Exception as e:
            logger.error(f"Invalid crop ratio {crop_ratio}: {e}")

    # 2.5 Canvas Ratio Padding (Ép khung)
    canvas_ratio = settings.get("canvas_ratio_val")
    bg_type = settings.get("bg_type", "black")
    zoom_box = settings.get("zoom_box")
    if canvas_ratio and not for_preview and not zoom_box:
        if bg_type == "black":
            R = float(canvas_ratio)
            vf_filters.append(
                f"pad='ceil(max(iw,ih*{R})/2)*2':'ceil(max(ih,iw/{R})/2)*2':(ow-iw)/2:(oh-ih)/2:color=black"
            )

    # 3. Flip
    if settings.get("flip_h"):
        vf_filters.append("hflip")
    if settings.get("flip_v"):
        vf_filters.append("vflip")

    # 4. Blur
    blur = settings.get("blur")
    if blur:
        vf_filters.append(f"boxblur={blur}")

    # 4.3 Custom Color (Brightness/Saturation)
    br = settings.get("brightness", 0)
    sa = settings.get("saturation", 0)
    if br != 0 or sa != 0:
        b_val = br / 100.0
        s_val = 1.0 + (sa / 50.0)
        vf_filters.append(f"eq=brightness={b_val:.2f}:saturation={s_val:.2f}")

    # 4.4 RGB Curves
    r_val = settings.get("red", 0)
    g_val = settings.get("green", 0)
    b_val = settings.get("blue", 0)
    if r_val != 0 or g_val != 0 or b_val != 0:
        # Map -50..50 to 0.25..0.75 for the mid-point of the curve (0/0 0.5/X 1/1)
        r_mid = 0.5 + (r_val / 200.0)
        g_mid = 0.5 + (g_val / 200.0)
        b_mid = 0.5 + (b_val / 200.0)
        vf_filters.append(f"curves=r='0/0 0.5/{r_mid:.2f} 1/1':g='0/0 0.5/{g_mid:.2f} 1/1':b='0/0 0.5/{b_mid:.2f} 1/1'")

    # 4.5 Auto Filters
    auto_filters = settings.get("auto_filters", [])
    if auto_filters:
        eq_args = []
        if "brightness" in auto_filters:
            eq_args.append("brightness=0.08")
        if "contrast" in auto_filters:
            eq_args.append("contrast=1.15")
        if "saturation" in auto_filters:
            eq_args.append("saturation=1.3")
        if eq_args:
            vf_filters.append("eq=" + ":".join(eq_args))

        if "sharpen" in auto_filters:
            vf_filters.append("unsharp=5:5:1.0:5:5:0.0")
        if "blur_light" in auto_filters:
            vf_filters.append("boxblur=2:1")
        if "bw" in auto_filters:
            vf_filters.append("format=gray")
        if "vignette" in auto_filters:
            vf_filters.append("vignette='PI/4'")
        if "color_balance" in auto_filters:
            vf_filters.append("colorbalance=rs=0.05:gs=0.05:bs=0.05")
        if "skin_smooth" in auto_filters:
            vf_filters.append("hqdn3d=4.0:4.0:3.0:3.0")

    # Watermark text
    watermark_text = settings.get("watermark_text")
    if watermark_text:
        pos = settings.get("watermark_position", "bottom-right")
        x, y = "w-tw-10", "h-th-10"
        if pos == "top-left":
            x, y = "10", "10"
        elif pos == "top-right":
            x, y = "w-tw-10", "10"
        elif pos == "bottom-left":
            x, y = "10", "h-th-10"
        elif pos == "center":
            x, y = "(w-tw)/2", "(h-th)/2"

        font_part = ""
        if os.name == 'nt':
            font_path = "C\\:/Windows/Fonts/arial.ttf"
            font_part = f":fontfile='{font_path}'"
        vf_filters.append(
            f"drawtext=text='{watermark_text}':fontcolor=white:fontsize=24"
            f":x={x}:y={y}{font_part}:box=1:boxcolor=black@0.5:boxborderw=5"
        )
        
    return vf_filters


def build_ffmpeg_cmds(
    input_path: str, save_path: str, base_name: str, ext: str,
    settings: dict,
    ffmpeg_path: str = None, ffprobe_path: str = None
) -> list[dict]:
    """
    Build FFmpeg commands based on edit settings.
    
    Returns a list of dicts: [{"cmd": [...], "output_path": ..., "stream_copy": bool}, ...]
    """
    ffmpeg_path = ffmpeg_path or FFMPEG_PATH
    ffprobe_path = ffprobe_path or FFPROBE_PATH

    cmds_and_outputs = []
    vf_filters = build_vf_string(settings)
    
    crop_box = settings.get("crop_box")
    crop_ratio = settings.get("crop_ratio")
    speed = settings.get("speed_value")

    # 5. Scale output
    output_height = settings.get("output_height")
    if output_height:
        source_height = get_video_height(input_path, ffprobe_path)
        if source_height > 0 and output_height < source_height:
            vf_filters.append(f"scale=-2:{output_height}")

    # 6. Ensure even dimensions after crop
    if crop_box or (crop_ratio and crop_ratio != "original"):
        vf_filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

    # 7. Ensure yuv420p output
    if vf_filters:
        vf_filters.append("format=yuv420p")

    # Logo
    def finalize_cmd(local_settings, cmd_prefix, output_path):
        cmd = list(cmd_prefix)
        input_count = 1

        # 1. Video Filters
        vf_filters = build_vf_string(local_settings, for_preview=False)

        # 2. Logo settings from local
        has_logo = bool(local_settings.get("logo_path"))
        logo_path = local_settings.get("logo_path")
        logo_pos = local_settings.get("logo_position", "top-right")
        logo_size = float(local_settings.get("logo_size", 20))

        logo_idx = -1
        if has_logo:
            cmd.extend(["-i", logo_path])
            logo_idx = input_count
            input_count += 1

        # 3. Audio settings from local
        bg_audio_path = local_settings.get("bg_audio_path")
        bg_audio_vol = float(local_settings.get("bg_audio_volume", 100)) / 100.0
        bg_audio_loop = local_settings.get("bg_audio_loop", False)

        audio_idx = -1
        if bg_audio_path:
            if bg_audio_loop:
                cmd.extend(["-stream_loop", "-1"])
            cmd.extend(["-i", bg_audio_path])
            audio_idx = input_count
            input_count += 1

        # Video Filter Complex
        main_v_pad = "0:v"
        fc_parts = []

        if vf_filters:
            fc_parts.append(f"[{main_v_pad}]{','.join(vf_filters)}[v_filtered]")
            main_v_pad = "v_filtered"

        canvas_ratio = local_settings.get("canvas_ratio_val")
        bg_type = local_settings.get("bg_type", "black")
        zoom_box = local_settings.get("zoom_box")

        if canvas_ratio:
            R = float(canvas_ratio)
            cw_scale = f"'ceil(max(iw,ih*{R})/2)*2'"
            ch_scale = f"'ceil(max(ih,iw/{R})/2)*2'"
            cw_crop = f"'ceil(min(iw,ih*{R})/2)*2'"
            ch_crop = f"'ceil(min(ih,iw/{R})/2)*2'"

            if zoom_box:
                canvas_w = 720
                canvas_h = int(720 / R)
                canvas_w, canvas_h = (canvas_w // 2) * 2, (canvas_h // 2) * 2
                
                video_w = (int(float(zoom_box['width'])) // 2) * 2
                video_h = (int(float(zoom_box['height'])) // 2) * 2
                target_x = int(float(zoom_box['x']))
                target_y = int(float(zoom_box['y']))
                
                if bg_type == "blur":
                    strength = local_settings.get("bg_blur_strength", 5)
                    bg_filter = f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,crop={canvas_w}:{canvas_h},boxblur={strength}:5"
                else:
                    bg_filter = f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,crop={canvas_w}:{canvas_h},drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill"

                fc_parts.append(f"[{main_v_pad}]split[v1][v2]")
                fc_parts.append(f"[v1]{bg_filter}[bg]")
                fc_parts.append(f"[v2]scale={video_w}:{video_h}[fg]")
                fc_parts.append(f"[bg][fg]overlay={target_x}:{target_y}:shortest=1[v_canvas_zoom]")
                main_v_pad = "v_canvas_zoom"

            elif bg_type == "blur":
                strength = local_settings.get("bg_blur_strength", 5)
                fc_parts.append(f"[{main_v_pad}]split[v1][v2]")
                fc_parts.append(f"[v1]scale=w={cw_scale}:h={ch_scale}:force_original_aspect_ratio=increase,crop=w={cw_crop}:h={ch_crop},boxblur={strength}:5[bg]")
                fc_parts.append(f"[v2]scale=w={cw_scale}:h={ch_scale}:force_original_aspect_ratio=decrease[fg]")
                fc_parts.append(f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v_canvas_blur]")
                main_v_pad = "v_canvas_blur"

        if has_logo:
            fc_parts.append(f"[{logo_idx}:v]scale=iw*{logo_size / 100}:-1[logo_scaled]")
            lx, ly = "10", "10"
            if logo_pos == "top-right":
                lx, ly = "W-w-10", "10"
            elif logo_pos == "bottom-left":
                lx, ly = "10", "H-h-10"
            elif logo_pos == "bottom-right":
                lx, ly = "W-w-10", "H-h-10"
            fc_parts.append(f"[{main_v_pad}][logo_scaled]overlay={lx}:{ly}[v_with_logo]")
            main_v_pad = "v_with_logo"

        # Audio Handling
        is_muted = local_settings.get("remove_audio", False)
        main_a_pad = "0:a"

        if bg_audio_path:
            if is_muted:
                fc_parts.append(f"[{audio_idx}:a]volume={bg_audio_vol}[out_a]")
                main_a_pad = "out_a"
            else:
                fc_parts.append(f"[{audio_idx}:a]volume={bg_audio_vol}[bg_a]")
                fc_parts.append(
                    f"[0:a][bg_a]amix=inputs=2:duration=first:dropout_transition=2[out_a]"
                )
                main_a_pad = "out_a"
        elif is_muted:
            main_a_pad = None

        # Build final command mapping
        if fc_parts:
            cmd.extend(["-filter_complex", ";".join(fc_parts)])
            if main_v_pad == "0:v":
                cmd.extend(["-map", "0:v"])
            else:
                cmd.extend(["-map", f"[{main_v_pad}]"])
            if main_a_pad:
                if main_a_pad == "0:a":
                    cmd.extend(["-map", "0:a"])
                else:
                    cmd.extend(["-map", f"[{main_a_pad}]"])
        else:
            if vf_filters:
                cmd.extend(["-vf", ",".join(vf_filters)])
            cmd.extend(["-map", "0:v"])
            if main_a_pad:
                cmd.extend(["-map", "0:a?"])
            else:
                cmd.append("-an")

        speed = local_settings.get("speed_value")
        if speed and speed != 1.0 and not (bg_audio_path or is_muted):
            cmd.extend(["-af", f"atempo={speed}"])

        if bg_audio_path and bg_audio_loop:
            cmd.append("-shortest")

        cmd.append(output_path)
        return cmd

    scene_split_enabled = settings.get("scene_split_enabled")
    split_enabled = settings.get("split_enabled")
    trimmer_enabled = settings.get("trimmer_enabled")

    if scene_split_enabled:
        scenes = settings.get("scenes", [])
        if not scenes:
            logger.warning(f"Scene split enabled but no scenes found for {input_path}")
            return []
            
        for i, scene in enumerate(scenes):
            if not scene.get('checked', True):
                continue
                
            idx = scene.get('idx', i + 1)
            start_t = float(scene.get('start_sec', 0))
            end_t = float(scene.get('end_sec', 0))
            duration = end_t - start_t
            
            if duration <= 0:
                continue
                
            output_name = f"{base_name}_scene{idx:03d}.{ext}"
            output_path = os.path.join(save_path, output_name)
            
            # Merge scene overrides with video settings
            scene_settings = dict(settings)
            scene_settings.update(scene.get('settings_override', {}))
            
            cmd_prefix = [
                ffmpeg_path, "-y",
                "-ss", f"{start_t:.3f}",
                "-i", input_path,
                "-t", f"{duration:.3f}"
            ]
            cmd = finalize_cmd(scene_settings, cmd_prefix, output_path)
            cmds_and_outputs.append({
                "cmd": cmd, "output_path": output_path, "stream_copy": False
            })

    elif split_enabled:
        trim_head = float(settings.get("trimmer_start", 0)) if trimmer_enabled else 0
        trim_tail = float(settings.get("trimmer_end", 0)) if trimmer_enabled else 0
        
        total_duration = get_video_duration(input_path, ffprobe_path)
        available_duration = total_duration - (trim_head + trim_tail)

        if available_duration <= 0:
            logger.warning(f"Skipping {input_path}: Trim duration exceeds video length.")
            return []

        min_d = float(settings.get("trim_start") or 1)
        max_d = float(settings.get("trim_end") or 100)
        split_count = int(settings.get("split_count") or 0)

        segments = calculate_split_segments(available_duration, min_d, max_d, target_k=split_count)

        start_time = trim_head
        for i, duration in enumerate(segments):
            idx_str = f"{(i + 1):03d}"
            output_name = f"{base_name}_part{idx_str}.{ext}"
            output_path = os.path.join(save_path, output_name)

            cmd_prefix = [
                ffmpeg_path, "-y",
                "-ss", f"{start_time:.3f}",
                "-i", input_path,
                "-t", f"{duration:.3f}"
            ]
            cmd = finalize_cmd(settings, cmd_prefix, output_path)
            cmds_and_outputs.append({
                "cmd": cmd, "output_path": output_path, "stream_copy": False
            })
            start_time += duration

    elif trimmer_enabled:
        trim_head = float(settings.get("trimmer_start", 0))
        trim_tail = float(settings.get("trimmer_end", 0))
        total_duration = get_video_duration(input_path, ffprobe_path)
        available_duration = total_duration - (trim_head + trim_tail)

        output_name = f"{base_name}.{ext}"
        output_path = os.path.join(save_path, output_name)
        
        cmd_prefix = [
            ffmpeg_path, "-y",
            "-ss", f"{trim_head:.3f}",
            "-i", input_path,
            "-t", f"{available_duration:.3f}"
        ]
        cmd = finalize_cmd(settings, cmd_prefix, output_path)
        cmds_and_outputs.append({
            "cmd": cmd, "output_path": output_path, "stream_copy": False
        })
    else:
        output_name = f"{base_name}.{ext}"
        output_path = os.path.join(save_path, output_name)
        cmd_prefix = [ffmpeg_path, "-y", "-i", input_path]
        cmd = finalize_cmd(settings, cmd_prefix, output_path)
        cmds_and_outputs.append({
            "cmd": cmd, "output_path": output_path, "stream_copy": False
        })

    return cmds_and_outputs
