"""
Preset Recipes — Built-in template presets with dynamic (randomized) logic.

Each recipe defines:
  - Global settings applied immediately when selected.
  - Per-scene logic executed after scene detection (randomized per scene).
"""
import random
import logging

logger = logging.getLogger("preset_recipes")


class PresetRecipe:
    """Base class for all preset recipes."""

    name: str = "Untitled"
    description: str = ""

    def get_global_settings(self) -> dict:
        """Return a settings dict to apply globally (immediately)."""
        raise NotImplementedError

    def apply_per_scene(self, scenes: list, video_width: int, video_height: int) -> None:
        """
        Mutate each scene's 'settings_override' dict with randomized values.

        Args:
            scenes: List of scene dicts, each with at least:
                     {'start_sec', 'end_sec', 'idx', 'checked', 'settings_override': {}}
            video_width: Source video width in pixels.
            video_height: Source video height in pixels.
        """
        pass  # No per-scene logic by default

    @property
    def has_per_scene_logic(self) -> bool:
        """Whether this recipe has per-scene randomization logic."""
        return False


class SoftKeyRecipe(PresetRecipe):
    """
    'Soft Key' preset — subtle, randomized edits per scene.

    Global:
      - Canvas ratio: 9:16
      - Background: blur
      - Scene split: enabled, merge: enabled

    Per-scene (randomized):
      - Crop: inward 20-80px per side
      - Zoom: outward 40-100px per side (on 720×1280 canvas)
      - Flip horizontal: ~30% of scenes
      - Speed: 1.05 – 1.08×
      - Color: brightness/saturation/red/green/blue ±10
    """

    name = "Soft Key"
    description = "Chuyển đổi mềm mại — crop, zoom, flip, speed, color ngẫu nhiên mỗi cảnh"

    # ── Canvas constants for 9:16 at 720px width ──
    CANVAS_W = 720
    CANVAS_H = 1280  # 720 / (9/16)

    def get_global_settings(self) -> dict:
        return {
            "canvas_ratio_label": "9:16",
            "canvas_ratio_val": 9 / 16,
            "bg_type": "blur",
            "bg_blur_strength": 5,
            "scene_split_enabled": True,
            "scene_merge_enabled": True,
        }

    @property
    def has_per_scene_logic(self) -> bool:
        return True

    def apply_per_scene(self, scenes: list, video_width: int, video_height: int) -> None:
        """Apply randomized settings to each scene."""
        if not scenes:
            return

        total = len(scenes)
        v_w = max(video_width, 1)
        v_h = max(video_height, 1)

        # ── Decide which scenes get flipped (~30%) ──
        flip_count = max(1, round(total * 0.3))
        flip_count = min(flip_count, total)  # safety clamp
        flip_indices = set(random.sample(range(total), flip_count))

        for i, enumerate_scene in enumerate(scenes):
            ovr = enumerate_scene.get("settings_override", {})

            # 1. Crop — inward 20-80px per side
            crop_left   = random.randint(20, 80)
            crop_right  = random.randint(20, 80)
            crop_top    = random.randint(20, 80)
            crop_bottom = random.randint(20, 80)

            # Ensure crop doesn't exceed video dimensions
            if crop_left + crop_right >= v_w:
                crop_left = int(v_w * 0.05)
                crop_right = int(v_w * 0.05)
            if crop_top + crop_bottom >= v_h:
                crop_top = int(v_h * 0.05)
                crop_bottom = int(v_h * 0.05)

            ovr["crop_box"] = {
                "x":      (crop_left / v_w) * 100,
                "y":      (crop_top / v_h) * 100,
                "width":  ((v_w - crop_left - crop_right) / v_w) * 100,
                "height": ((v_h - crop_top - crop_bottom) / v_h) * 100,
            }

            # 2. Zoom — Proportional zoom to avoid distortion
            # Calculate aspect ratio of the cropped video
            cropped_w = v_w - crop_left - crop_right
            cropped_h = v_h - crop_top - crop_bottom
            video_ar = cropped_w / cropped_h

            # We want to zoom so it fills the 9:16 canvas (720x1280) + random margins
            # The margins should be applied such that the aspect ratio is preserved.
            
            # Base logic: Scale to fill the 9:16 frame (Cover)
            canvas_ar = self.CANVAS_W / self.CANVAS_H # 0.5625
            
            # Additional random 'overflow' from 40 to 100px on each side
            # To keep it simple and proportional, we pick a scale factor that ensures this
            margin = random.randint(40, 100)
            
            if video_ar > canvas_ar:
                # Video is wider than 9:16 (e.g. 16:9). Match height to canvas + margins.
                target_h = self.CANVAS_H + (margin * 2)
                target_w = target_h * video_ar
            else:
                # Video is taller than 9:16. Match width to canvas + margins.
                target_w = self.CANVAS_W + (margin * 2)
                target_h = target_w / video_ar
            
            # Center and add a tiny random jitter to X/Y
            ovr["zoom_box"] = {
                "x":      (self.CANVAS_W - target_w) / 2 + random.randint(-10, 10),
                "y":      (self.CANVAS_H - target_h) / 2 + random.randint(-10, 10),
                "width":  target_w,
                "height": target_h,
            }

            # 3. Flip horizontal — ~30% of scenes
            ovr["flip_h"] = (i in flip_indices)

            # 4. Speed — random 1.05 to 1.08
            ovr["speed_value"] = round(random.uniform(1.05, 1.08), 3)

            # 5. Color — each channel ±10
            ovr["brightness"] = random.randint(-10, 10)
            ovr["saturation"] = random.randint(-10, 10)
            ovr["red"]        = random.randint(-10, 10)
            ovr["green"]      = random.randint(-10, 10)
            ovr["blue"]       = random.randint(-10, 10)

            enumerate_scene["settings_override"] = ovr

        logger.info(
            f"[SoftKey] Applied per-scene settings to {total} scenes "
            f"(flip={len(flip_indices)}, video={v_w}x{v_h})"
        )


# ═══════════════════════════════════════════════════════════
#  Registry of all built-in recipes
# ═══════════════════════════════════════════════════════════
BUILTIN_RECIPES: list[PresetRecipe] = [
    SoftKeyRecipe(),
]
