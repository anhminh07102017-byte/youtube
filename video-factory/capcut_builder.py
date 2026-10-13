"""
CapCut Project Builder — tạo project CapCut Pro Desktop từ scenes đã duyệt.
CapCut Pro Desktop 9.5.0, macOS.
"""

import hashlib
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional


CAPCUT_PROJECTS_DIR = os.path.expanduser(
    "~/Movies/CapCut/User Data/Projects/com.lveditor.draft"
)

# 1 second = 1_000_000 microseconds in CapCut
US_PER_SEC = 1_000_000


def _uuid():
    return str(uuid.uuid4()).upper()


def _get_device_info(capcut_dir: str) -> dict:
    """Đọc device info từ project CapCut hiện có."""
    default = {
        "app_id": 359289, "app_source": "cc", "app_version": "9.5.0",
        "device_id": "", "hard_disk_id": "", "mac_address": "",
        "os": "mac", "os_version": "26.2",
    }
    capcut_path = Path(capcut_dir)
    if not capcut_path.exists():
        return default
    for project_dir in capcut_path.iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue
        draft_file = project_dir / "draft_info.json"
        if draft_file.exists():
            try:
                data = json.loads(draft_file.read_text("utf-8"))
                platform = data.get("platform", {})
                if platform.get("device_id"):
                    return platform
            except (json.JSONDecodeError, KeyError):
                continue
    return default


def _make_segment_base(material_id: str, target_start: int, target_duration: int,
                       source_start: int = 0, source_duration: Optional[int] = None,
                       render_index: int = 0, track_render_index: int = 0):
    """Tạo segment base — dùng chung cho video/audio/text."""
    return {
        "caption_info": None,
        "cartoon": False,
        "clip": None,
        "color_correct_alg_result": "",
        "common_keyframes": [],
        "desc": "",
        "digital_human_template_group_id": "",
        "enable_adjust": False,
        "enable_adjust_mask": False,
        "enable_color_adjust_pro": False,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_hsl": False,
        "enable_hsl_curves": True,
        "enable_lut": False,
        "enable_mask_shadow": False,
        "enable_mask_stroke": False,
        "enable_smart_color_adjust": False,
        "enable_video_mask": True,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": None,
        "hdr_vivid_settings": None,
        "id": _uuid(),
        "intensifies_audio": False,
        "is_loop": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1.0,
        "lyric_keyframes": None,
        "material_id": material_id,
        "raw_segment_id": "",
        "render_index": render_index,
        "render_timerange": {"duration": 0, "start": 0},
        "responsive_layout": {"enable": False, "horizontal_pos_layout": 0,
                               "size_layout": 0, "target_follow": "",
                               "vertical_pos_layout": 0},
        "reverse": False,
        "segment_color_tag": "",
        "source": "segmentsourcenormal",
        "source_timerange": {"duration": source_duration or target_duration, "start": source_start},
        "speed": 1.0,
        "state": 0,
        "target_timerange": {"duration": target_duration, "start": target_start},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": track_render_index,
        "uniform_scale": None,
        "visible": True,
        "volume": 1.0,
    }


def _make_image_material(image_path: str, width: int = 1920, height: int = 1080):
    """Tạo image material cho CapCut."""
    mat_id = _uuid()
    abs_path = str(Path(image_path).resolve())
    return mat_id, {
        "aigc_type": "none",
        "audio_fade": None,
        "category_id": "",
        "category_name": "local",
        "check_flag": 63487,
        "crop": {
            "lower_left_x": 0.0, "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
            "upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0,
        },
        "crop_ratio": "free",
        "crop_scale": 1.0,
        "duration": 5 * US_PER_SEC,
        "extra_type_option": 0,
        "formula_id": "",
        "freeze": None,
        "gameplay_album_id": "",
        "has_audio": False,
        "height": height,
        "id": mat_id,
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_ai_generate_content": False,
        "is_copyright": False,
        "is_text_edit_overdub": False,
        "is_unified_beauty_mode": False,
        "is_ugc_subtitle_generation": False,
        "local_id": "",
        "local_material_id": _uuid().lower(),
        "material_id": "",
        "material_name": Path(image_path).name,
        "material_url": "",
        "matting": {"flag": 0, "has_use_quick_brush": False,
                    "has_use_quick_eraser": False, "interactiveTime": [],
                    "path": "", "strokes": [],
                    "expansion": 0, "feather": 0, "reverse": False,
                    "custom_matting_id": "", "enable_matting_stroke": False,
                    "is_clould": False, "mask_video_path": "",
                    "cloud_product_fps": 0.0},
        "media_path": "",
        "multi_camera_info": None,
        "object_locked": None,
        "origin_material_id": "",
        "path": abs_path,
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "request_id": "",
        "reverse_intensifies_path": "",
        "reverse_path": "",
        "smart_motion": None,
        "source": 0,
        "source_platform": 0,
        "stable": {"matrix_path": "", "stable_level": 0, "time_range": {"duration": 0, "start": 0}},
        "team_id": "",
        "type": "photo",
        "unique_id": "",
        "video_algorithm": {
            "algorithms": [], "deflicker": None,
            "motion_blur_config": None, "noise_reduction": None,
            "path": "", "quality_enhance": None,
            "time_range": None, "gameplay_configs": [],
            "ai_in_painting_config": [], "complement_frame_config": None,
            "super_resolution": None, "ai_background_configs": [],
            "smart_complement_frame": None, "aigc_generate": None,
            "aigc_generate_list": [], "mouth_shape_driver": None,
            "ai_expression_driven": None, "ai_motion_driven": None,
            "image_interpretation": None,
            "story_video_modify_video_config": {
                "task_id": "", "is_overwrite_last_video": False,
                "tracker_task_id": "", "generate_id": "", "generate_card_id": "",
            },
            "skip_algorithm_index": [],
        },
        "width": width,
        "has_sound_separated": False,
        "is_video_copilot_aigc_content": False,
        "aigc_history_id": "",
        "aigc_item_id": "",
        "local_material_from": "",
        "smart_match_info": None,
        "cartoon_path": "",
        "is_set_beauty_mode": False,
    }


def _make_video_material(video_path: str, duration_us: int, width: int = 1920, height: int = 1080):
    """Tạo video material cho CapCut."""
    mat_id = _uuid()
    abs_path = str(Path(video_path).resolve())
    return mat_id, {
        "aigc_type": "none",
        "audio_fade": None,
        "category_id": "",
        "category_name": "local",
        "check_flag": 63487,
        "crop": {
            "lower_left_x": 0.0, "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
            "upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0,
        },
        "crop_ratio": "free",
        "crop_scale": 1.0,
        "duration": duration_us,
        "extra_type_option": 0,
        "formula_id": "",
        "freeze": None,
        "gameplay_album_id": "",
        "has_audio": False,
        "height": height,
        "id": mat_id,
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_ai_generate_content": False,
        "is_copyright": False,
        "is_text_edit_overdub": False,
        "is_unified_beauty_mode": False,
        "is_ugc_subtitle_generation": False,
        "local_id": "",
        "local_material_id": _uuid().lower(),
        "material_id": "",
        "material_name": Path(video_path).name,
        "material_url": "",
        "matting": {"flag": 0, "has_use_quick_brush": False,
                    "has_use_quick_eraser": False, "interactiveTime": [],
                    "path": "", "strokes": [],
                    "expansion": 0, "feather": 0, "reverse": False,
                    "custom_matting_id": "", "enable_matting_stroke": False,
                    "is_clould": False, "mask_video_path": "",
                    "cloud_product_fps": 0.0},
        "media_path": "",
        "multi_camera_info": None,
        "object_locked": None,
        "origin_material_id": "",
        "path": abs_path,
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "request_id": "",
        "reverse_intensifies_path": "",
        "reverse_path": "",
        "smart_motion": None,
        "source": 0,
        "source_platform": 0,
        "stable": {"matrix_path": "", "stable_level": 0, "time_range": {"duration": 0, "start": 0}},
        "team_id": "",
        "type": "video",
        "unique_id": "",
        "video_algorithm": {
            "algorithms": [], "deflicker": None,
            "motion_blur_config": None, "noise_reduction": None,
            "path": "", "quality_enhance": None,
            "time_range": None, "gameplay_configs": [],
            "ai_in_painting_config": [], "complement_frame_config": None,
            "super_resolution": None, "ai_background_configs": [],
            "smart_complement_frame": None, "aigc_generate": None,
            "aigc_generate_list": [], "mouth_shape_driver": None,
            "ai_expression_driven": None, "ai_motion_driven": None,
            "image_interpretation": None,
            "story_video_modify_video_config": {
                "task_id": "", "is_overwrite_last_video": False,
                "tracker_task_id": "", "generate_id": "", "generate_card_id": "",
            },
            "skip_algorithm_index": [],
        },
        "width": width,
        "has_sound_separated": False,
        "is_video_copilot_aigc_content": False,
        "aigc_history_id": "",
        "aigc_item_id": "",
        "local_material_from": "",
        "smart_match_info": None,
        "cartoon_path": "",
        "is_set_beauty_mode": False,
    }


def _make_audio_material(audio_path: str, duration_us: int):
    """Tạo audio material cho CapCut."""
    mat_id = _uuid()
    abs_path = str(Path(audio_path).resolve())
    return mat_id, {
        "ai_music_enter_from": "",
        "ai_music_generate_scene": 0,
        "ai_music_type": 0,
        "aigc_history_id": "",
        "aigc_item_id": "",
        "app_id": 0,
        "category_id": "",
        "category_name": "local",
        "check_flag": 1,
        "cloned_model_type": "",
        "copyright_limit_type": "none",
        "duration": duration_us,
        "effect_id": "",
        "formula_id": "",
        "id": mat_id,
        "intensifies_path": "",
        "is_ai_clone_tone": False,
        "is_ai_clone_tone_post": False,
        "is_text_edit_overdub": False,
        "is_ugc": False,
        "local_material_id": _uuid().lower(),
        "lyric_type": 0,
        "mock_tone_speaker": "",
        "moyin_emotion": "",
        "music_id": _uuid().lower(),
        "music_source": "",
        "name": Path(audio_path).name,
        "path": abs_path,
        "pgc_id": "",
        "pgc_name": "",
        "query": "",
        "request_id": "",
        "resource_id": "",
        "search_id": "",
        "similiar_music_info": {},
        "sound_separate_type": "",
        "source_from": "",
        "source_platform": 0,
        "team_id": "",
        "text_id": "",
        "third_resource_id": "",
        "tone_category_id": "",
        "tone_category_name": "",
        "tone_effect_id": "",
        "tone_effect_name": "",
        "tone_emotion_name_key": "",
        "tone_emotion_role": "",
        "tone_emotion_scale": 0.0,
        "tone_emotion_selection": "",
        "tone_emotion_style": "",
        "tone_platform": "",
        "tone_second_category_id": "",
        "tone_second_category_name": "",
        "tone_speaker": "",
        "tone_type": "",
        "tts_benefit_info": {},
        "tts_generate_scene": "",
        "tts_language_info": None,
        "tts_task_id": "",
        "type": "extract_music",
        "unique_id": uuid.uuid4().hex,
        "video_id": "",
        "wave_points": [],
    }


def _make_speed_material():
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "type": "speed",
        "mode": 0,
        "speed": 1.0,
        "curve_speed": None,
    }


def _make_canvas_material():
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "type": "canvas_color",
        "color": "",
        "blur": 0.0,
        "image": "",
        "album_image": "",
        "image_id": "",
        "image_name": "",
        "source_platform": 0,
        "team_id": "",
    }


def _make_placeholder_info():
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "type": "placeholder_info",
        "meta_type": "none",
        "res_path": "",
        "res_text": "",
        "error_path": "",
        "error_text": "",
    }


def _make_sound_channel_mapping():
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "type": "",
        "audio_channel_mapping": 0,
        "is_config_open": False,
    }


def _make_material_color():
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "is_color_clip": False,
        "is_gradient": False,
        "solid_color": "",
        "gradient_colors": [],
        "gradient_percents": [],
        "gradient_angle": 90.0,
        "width": 0.0,
        "height": 0.0,
    }


def _make_loudness():
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "enable": False,
        "time_range": None,
        "file_id": "",
        "target_loudness": 0.0,
        "loudness_param": None,
    }


def _make_vocal_separation():
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "type": "vocal_separation",
        "choice": 0,
        "removed_sounds": [],
        "time_range": None,
        "production_path": "",
        "final_algorithm": "",
        "enter_from": "",
    }


def _make_text_material(text: str, font_path: str = ""):
    """Tạo subtitle text material cho CapCut."""
    mat_id = _uuid()
    if not font_path:
        font_path = "/Applications/CapCut.app/Contents/Resources/Font/SystemFont/en.ttf"
    text_len = len(text)
    content_obj = {
        "styles": [{
            "fill": {
                "alpha": 1.0,
                "content": {
                    "render_type": "solid",
                    "solid": {"alpha": 1.0, "color": [1.0, 1.0, 1.0]},
                },
            },
            "font": {"id": "", "path": font_path},
            "range": [0, text_len],
            "size": 7.0,
        }],
        "text": text,
    }
    content_str = json.dumps(content_obj, ensure_ascii=False)
    return mat_id, {
        "id": mat_id,
        "type": "subtitle",
        "name": "",
        "content": content_str,
        "base_content": content_str,
        "recognize_text": text,
        "recognize_task_id": "",
        "recognize_model": "",
        "punc_model": "",
        "words": {"start_time": [], "end_time": [], "text": []},
        "current_words": {"start_time": [], "end_time": [], "text": []},
        "global_alpha": 1.0,
        "combo_info": {"text_templates": []},
        "caption_template_info": {
            "resource_id": "", "third_resource_id": "", "resource_name": "",
            "category_id": "", "category_name": "", "effect_id": "",
            "request_id": "", "path": "", "is_new": False, "source_platform": 0,
        },
        "layer_weight": 1,
        "letter_spacing": 0.0,
        "text_curve": None,
        "text_loop_on_path": False,
        "offset_on_path": 0.0,
        "enable_path_typesetting": False,
        "text_exceeds_path_process_type": 0,
        "text_typesetting_paths": None,
        "text_typesetting_paths_file": "",
        "text_typesetting_path_index": 0,
        "line_spacing": 0.02,
        "has_shadow": True,
        "shadow_color": "#000000",
        "shadow_alpha": 0.9,
        "shadow_smoothing": 0.45,
        "shadow_distance": 5.0,
        "shadow_point": {"x": 0.636, "y": -0.636},
        "shadow_angle": -45.0,
        "shadow_thickness_projection_enable": False,
        "shadow_thickness_projection_angle": 0.0,
        "shadow_thickness_projection_distance": 0.0,
        "border_alpha": 1.0,
        "border_color": "#000000",
        "border_width": 0.08,
        "border_mode": 0,
        "style_name": "",
        "text_color": "#FFFFFF",
        "text_alpha": 1.0,
        "font_name": "",
        "font_title": "none",
        "font_size": 7.0,
        "font_path": font_path,
        "font_id": "",
        "font_resource_id": "",
        "initial_scale": 1.0,
        "font_url": "",
        "typesetting": 0,
        "alignment": 1,
        "line_feed": 1,
        "use_effect_default_color": True,
        "is_rich_text": False,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "ktv_color": "",
        "text_to_audio_ids": [],
        "bold_width": 0.0,
        "italic_degree": 0,
        "underline": False,
        "underline_width": 0.05,
        "underline_offset": 0.22,
        "sub_type": 0,
        "check_flag": 7,
        "text_size": 30,
        "font_category_name": "",
        "font_source_platform": 0,
        "font_third_resource_id": "",
        "font_category_id": "",
        "add_type": 1,
        "operation_type": 0,
        "recognize_type": 0,
        "fonts": [],
        "background_color": "",
        "background_alpha": 1.0,
        "background_style": 0,
        "background_round_radius": 0.0,
        "background_width": 0.14,
        "background_height": 0.14,
        "background_vertical_offset": 0.0,
        "background_horizontal_offset": 0.0,
        "background_fill": "",
        "single_char_bg_enable": False,
        "single_char_bg_color": "",
        "single_char_bg_alpha": 1.0,
        "single_char_bg_round_radius": 0.3,
        "single_char_bg_width": 0.0,
        "single_char_bg_height": 0.0,
        "single_char_bg_vertical_offset": 0.0,
        "single_char_bg_horizontal_offset": 0.0,
        "font_team_id": "",
        "tts_auto_update": False,
        "text_preset_resource_id": "",
        "group_id": "",
        "preset_id": "",
        "preset_name": "",
        "preset_category": "",
        "preset_category_id": "",
        "preset_index": 0,
        "preset_has_set_alignment": False,
        "force_apply_line_max_width": False,
        "language": "vi-VN",
        "relevance_segment": [],
        "original_size": [],
        "fixed_width": -1.0,
        "fixed_height": -1.0,
        "autoAdaptCanvasEnabled": False,
        "line_max_width": 0.82,
        "oneline_cutoff": False,
        "cutoff_postfix": "",
        "subtitle_template_original_fontsize": 0.0,
        "subtitle_keywords": {"range": []},
        "inner_padding": -1.0,
        "multi_language_current": "none",
        "source_from": "",
        "is_lyric_effect": False,
        "lyric_group_id": "",
        "lyrics_template": {
            "resource_id": "", "resource_name": "", "panel": "",
            "effect_id": "", "path": "", "category_id": "",
            "category_name": "", "request_id": "",
        },
        "is_batch_replace": False,
        "is_words_linear": False,
        "ssml_content": "",
        "subtitle_keywords_config": None,
        "sub_template_id": -1,
        "translate_original_text": "",
    }


def _make_text_segment(material_id: str, anim_id: str, target_start: int,
                       target_duration: int, render_index: int,
                       subtitle_y: float = -0.73):
    """Tạo text segment cho subtitle track."""
    return {
        "id": _uuid(),
        "source_timerange": None,
        "target_timerange": {"start": target_start, "duration": target_duration},
        "render_timerange": {"start": 0, "duration": 0},
        "material_id": material_id,
        "extra_material_refs": [anim_id],
        "render_index": render_index,
        "track_render_index": 1,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": subtitle_y},
        },
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": 1.0,
        "last_nonzero_volume": 1.0,
        "speed": 1.0,
        "state": 0,
        "is_loop": False,
        "is_tone_modify": False,
        "reverse": False,
        "intensifies_audio": False,
        "cartoon": False,
        "desc": "",
        "group_id": "",
        "enable_lut": False,
        "enable_adjust": False,
        "enable_hsl": False,
        "enable_color_curves": True,
        "enable_hsl_curves": True,
        "enable_color_wheels": True,
        "enable_color_match_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_color_adjust_pro": False,
        "enable_smart_color_adjust": False,
        "enable_adjust_mask": False,
        "enable_video_mask": True,
        "enable_mask_stroke": False,
        "enable_mask_shadow": False,
        "hdr_settings": None,
        "hdr_vivid_settings": None,
        "track_attribute": 0,
        "is_placeholder": False,
        "template_id": "",
        "template_scene": "default",
        "common_keyframes": [],
        "caption_info": None,
        "responsive_layout": {
            "enable": False, "target_follow": "", "size_layout": 0,
            "horizontal_pos_layout": 0, "vertical_pos_layout": 0,
        },
        "raw_segment_id": "",
        "lyric_keyframes": None,
        "digital_human_template_group_id": "",
        "color_correct_alg_result": "",
        "source": "segmentsourcenormal",
        "keyframe_refs": [],
        "segment_color_tag": "",
    }


def _make_sticker_animation():
    """Tạo material_animation cho text segment."""
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "type": "sticker_animation",
        "animations": [],
        "multi_language_current": "none",
    }


def _make_transition_material(duration_us: int = 500000):
    """Tạo transition material (crossfade/dissolve)."""
    mat_id = _uuid()
    return mat_id, {
        "id": mat_id,
        "type": "transition",
        "category_id": "",
        "category_name": "",
        "duration": duration_us,
        "effect_id": "",
        "is_overlap": True,
        "name": "",
        "path": "",
        "platform": "all",
        "request_id": "",
        "resource_id": "",
        "value": 0,
    }


def _make_ken_burns_keyframes(segment_id: str, duration_us: int, effect_type: str = "zoom_in"):
    """
    Tạo common_keyframes cho Ken Burns effect.
    Format reverse-engineered từ CapCut Pro 9.5.0.
    effect_type: 'zoom_in', 'zoom_out', 'pan_left', 'pan_right'
    """
    if effect_type == "zoom_in":
        start_scale, end_scale = 1.0, 1.15
        start_x, start_y, end_x, end_y = 0.0, 0.0, 0.0, 0.0
    elif effect_type == "zoom_out":
        start_scale, end_scale = 1.15, 1.0
        start_x, start_y, end_x, end_y = 0.0, 0.0, 0.0, 0.0
    elif effect_type == "pan_left":
        start_scale, end_scale = 1.15, 1.15
        start_x, start_y = 0.05, 0.0
        end_x, end_y = -0.05, 0.0
    elif effect_type == "pan_right":
        start_scale, end_scale = 1.15, 1.15
        start_x, start_y = -0.05, 0.0
        end_x, end_y = 0.05, 0.0
    else:
        start_scale, end_scale = 1.0, 1.1
        start_x, start_y, end_x, end_y = 0.0, 0.0, 0.0, 0.0

    def _kf_entry(time_offset, values):
        return {
            "id": "",
            "curveType": "Line",
            "time_offset": time_offset,
            "left_control": {"x": 0.0, "y": 0.0},
            "right_control": {"x": 0.0, "y": 0.0},
            "values": values,
            "string_value": "",
            "graphID": "",
        }

    keyframes = [
        {
            "id": _uuid(),
            "material_id": segment_id,
            "property_type": "KFTypePositionScaleX",
            "keyframe_list": [
                _kf_entry(0, [start_scale]),
                _kf_entry(duration_us, [end_scale]),
            ],
        },
        {
            "id": _uuid(),
            "material_id": segment_id,
            "property_type": "KFTypePositionScaleY",
            "keyframe_list": [
                _kf_entry(0, [start_scale]),
                _kf_entry(duration_us, [end_scale]),
            ],
        },
    ]

    # Chỉ thêm PositionX/Y nếu có pan (tránh thừa keyframes)
    if start_x != end_x or start_y != end_y:
        keyframes.extend([
            {
                "id": _uuid(),
                "material_id": segment_id,
                "property_type": "KFTypePositionX",
                "keyframe_list": [
                    _kf_entry(0, [start_x]),
                    _kf_entry(duration_us, [end_x]),
                ],
            },
            {
                "id": _uuid(),
                "material_id": segment_id,
                "property_type": "KFTypePositionY",
                "keyframe_list": [
                    _kf_entry(0, [start_y]),
                    _kf_entry(duration_us, [end_y]),
                ],
            },
        ])

    return keyframes


def _make_draft_material_entry(
    file_path: str,
    metetype: str,
    duration_us: int,
    width: int = 0,
    height: int = 0,
):
    """Tạo entry cho draft_materials trong draft_meta_info.json."""
    now = int(time.time())
    now_us = int(time.time() * US_PER_SEC)
    return {
        "ai_group_type": "",
        "create_time": now,
        "duration": duration_us,
        "enter_from": 0,
        "extra_info": Path(file_path).name if file_path else "",
        "file_Path": str(Path(file_path).resolve()) if file_path else "",
        "height": height,
        "id": uuid.uuid4().hex[:8] + "-" + uuid.uuid4().hex[:4] + "-" + uuid.uuid4().hex[:4] + "-" + uuid.uuid4().hex[:4] + "-" + uuid.uuid4().hex[:12],
        "import_time": now,
        "import_time_ms": now_us,
        "item_source": 1,
        "material_color_tag": "",
        "md5": "",
        "metetype": metetype,
        "roughcut_time_range": {"duration": duration_us, "start": 0},
        "sub_time_range": {"duration": -1, "start": -1},
        "type": 0,
        "width": width,
    }


def _make_key_value_entry(material_name: str, material_subcategory: str = "local"):
    """Tạo entry cho key_value.json."""
    return {
        "Tiktok_music_is_avaliable": False,
        "add_to_timeline_before_download": False,
        "commerce_template_cate": "",
        "commerce_template_pay_status": "",
        "commerce_template_pay_type": "",
        "enter_from": "",
        "filter_category": "",
        "filter_detail": "",
        "is_brand": 0,
        "is_favorite": False,
        "is_from_artist_shop": 0,
        "is_limited": False,
        "is_similar_music": False,
        "is_vip": "0",
        "keywordSource": "",
        "materialCategory": "media",
        "materialId": hashlib.md5(material_name.encode()).hexdigest(),
        "materialName": material_name,
        "materialSubcategory": material_subcategory,
        "materialSubcategoryId": "",
        "materialThirdcategory": "Nhập",
        "materialThirdcategoryId": "",
        "material_copyright": "",
        "material_is_purchased": "",
        "music_source": "",
        "original_song_id": "",
        "original_song_name": "",
        "pgc_id": "",
        "search_id": "",
        "slot_music_id": "",
        "source_from": "",
        "source_type": 0,
        "third_resource_id": "",
    }


def _update_root_meta_info(capcut_dir: str, project_dir: Path, draft_id: str,
                           folder_name: str, total_duration: int,
                           draft_info_size: int):
    """Đăng ký project mới vào root_meta_info.json."""
    root_meta_path = Path(capcut_dir) / "root_meta_info.json"
    now_us = int(time.time() * US_PER_SEC)

    entry = {
        "cloud_draft_cover": False,
        "cloud_draft_sync": False,
        "draft_cloud_last_action_download": False,
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "",
        "draft_fold_path": str(project_dir),
        "draft_id": draft_id,
        "draft_is_ai_shorts": canvas_width < canvas_height,
        "draft_is_cloud_temp_draft": False,
        "draft_is_infinite_canvas_draft": False,
        "draft_is_invisible": False,
        "draft_is_pippit_draft": False,
        "draft_is_web_article_video": False,
        "draft_json_file": str(project_dir / "draft_info.json"),
        "draft_name": folder_name,
        "draft_new_version": "",
        "draft_root_path": capcut_dir,
        "draft_timeline_materials_size": draft_info_size,
        "draft_type": "",
        "draft_web_article_video_enter_from": "",
        "pippit_avatar_url": "",
        "pippit_extra_info": "",
        "pippit_id": "",
        "pippit_user_name": "",
        "streaming_edit_draft_ready": True,
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_entry_id": -1,
        "tm_draft_cloud_modified": 0,
        "tm_draft_cloud_parent_entry_id": -1,
        "tm_draft_cloud_space_id": -1,
        "tm_draft_cloud_user_id": -1,
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": total_duration,
    }

    if root_meta_path.exists():
        try:
            root_data = json.loads(root_meta_path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            root_data = {"all_draft_store": []}
    else:
        root_data = {"all_draft_store": []}

    # Prepend (newest first)
    root_data["all_draft_store"].insert(0, entry)
    root_meta_path.write_text(json.dumps(root_data, ensure_ascii=False), "utf-8")


def build_capcut_project(
    project_name: str,
    scenes: list,
    audio_path: Optional[str] = None,
    audio_duration_us: Optional[int] = None,
    projects_base: str = "",
    transition_duration_us: int = 500_000,
    enable_ken_burns: bool = False,
    enable_transitions: bool = False,
    enable_subtitles: bool = True,
    canvas_width: int = 1920,
    canvas_height: int = 1080,
) -> dict:
    """
    Build CapCut project from scenes.

    Args:
        project_name: Tên project
        scenes: List of dicts with keys:
            - scene_number: int
            - timestamp_start: float (seconds)
            - timestamp_end: float (seconds)
            - asset_path: str (path to image/video file)
            - visual_type: "image" | "video" (optional, default "image")
            - script_text: str (optional, subtitle text)
            - transition_note: str (optional, e.g. "Crossfade", "Cut", "Fade from black")
            - mood: str (optional, e.g. "epic", "calm", "tense")
        audio_path: Path to audio file (optional)
        audio_duration_us: Audio duration in microseconds (optional, auto-detect from scenes)
        projects_base: Custom base path for projects dir
        transition_duration_us: Default transition duration in microseconds (0.5s)

    Returns:
        dict with status, project_path, message
    """
    capcut_dir = projects_base or CAPCUT_PROJECTS_DIR

    if not Path(capcut_dir).exists():
        return {"status": "error", "message": f"CapCut projects directory not found: {capcut_dir}"}

    # Đọc device info từ project CapCut hiện có
    device_info = _get_device_info(capcut_dir)

    # Tìm folder ID tiếp theo
    existing = [d.name for d in Path(capcut_dir).iterdir() if d.is_dir()]
    max_id = 0
    for name in existing:
        try:
            num = int(name.split(" ")[0])
            if num > max_id:
                max_id = num
        except (ValueError, IndexError):
            pass
    folder_name = str(max_id + 1)
    project_dir = Path(capcut_dir) / folder_name

    # Tạo folder structure
    project_dir.mkdir(parents=True)
    (project_dir / "adjust_mask").mkdir()
    (project_dir / "attachment").mkdir()
    (project_dir / "common_attachment").mkdir()
    (project_dir / "matting").mkdir()
    (project_dir / "qr_upload").mkdir()
    resources_dir = project_dir / "Resources"
    resources_dir.mkdir()
    (project_dir / "smart_crop").mkdir()

    # Materials
    video_materials = []
    audio_materials = []
    speed_materials = []
    canvas_materials = []
    placeholder_infos = []
    sound_channel_mappings = []
    material_colors = []
    loudnesses = []
    vocal_separations = []
    text_materials = []
    material_animations = []
    transition_materials = []

    # Tracks
    video_segments = []
    audio_segments = []
    text_segments = []

    # Ken Burns keyframes
    all_video_keyframes = []

    # Import entries for draft_meta_info
    draft_material_entries = []
    # key_value entries
    key_value_data = {}

    # Ken Burns effect types — cycle through for variety
    kb_effects = ["zoom_in", "zoom_out", "pan_left", "pan_right"]

    # Sort scenes by timestamp
    scenes_sorted = sorted(scenes, key=lambda s: s.get("timestamp_start", 0))

    # Tính tổng duration
    if scenes_sorted:
        total_duration = int(scenes_sorted[-1].get("timestamp_end", 0) * US_PER_SEC)
    else:
        total_duration = 0

    if audio_duration_us:
        total_duration = max(total_duration, audio_duration_us)

    # Video segments + materials
    for scene in scenes_sorted:
        asset_path = scene.get("asset_path")
        if not asset_path or not Path(asset_path).exists():
            continue

        start_us = int(scene["timestamp_start"] * US_PER_SEC)
        end_us = int(scene["timestamp_end"] * US_PER_SEC)
        duration_us = end_us - start_us

        if duration_us <= 0:
            continue

        visual_type = scene.get("visual_type", "image")

        # Copy file vào Resources/ để CapCut có quyền truy cập
        src_path = Path(asset_path)
        local_name = src_path.name
        local_path = resources_dir / local_name
        # Tránh trùng tên
        counter = 1
        while local_path.exists():
            local_path = resources_dir / f"{src_path.stem}_{counter}{src_path.suffix}"
            local_name = local_path.name
            counter += 1
        shutil.copy2(src_path, local_path)
        local_path_str = str(local_path)

        # Create material
        if visual_type == "video":
            mat_id, mat = _make_video_material(local_path_str, duration_us, canvas_width, canvas_height)
            metetype = "video"
        else:
            mat_id, mat = _make_image_material(local_path_str, canvas_width, canvas_height)
            metetype = "photo"

        video_materials.append(mat)

        # Draft material entry for import list
        draft_material_entries.append(
            _make_draft_material_entry(local_path_str, metetype, duration_us, canvas_width, canvas_height)
        )

        # key_value entry
        mat_key = hashlib.md5(Path(asset_path).name.encode()).hexdigest()
        key_value_data[mat_key] = _make_key_value_entry(Path(asset_path).name)

        # Extra materials for this segment
        speed_id, speed_mat = _make_speed_material()
        speed_materials.append(speed_mat)

        canvas_id, canvas_mat = _make_canvas_material()
        canvas_materials.append(canvas_mat)

        ph_id, ph_mat = _make_placeholder_info()
        placeholder_infos.append(ph_mat)

        sc_id, sc_mat = _make_sound_channel_mapping()
        sound_channel_mappings.append(sc_mat)

        mc_id, mc_mat = _make_material_color()
        material_colors.append(mc_mat)

        loud_id, loud_mat = _make_loudness()
        loudnesses.append(loud_mat)

        vs_id, vs_mat = _make_vocal_separation()
        vocal_separations.append(vs_mat)

        # Create segment
        scene_idx = len(video_segments)
        seg = _make_segment_base(
            material_id=mat_id,
            target_start=start_us,
            target_duration=duration_us,
            source_start=0,
            source_duration=duration_us,
            render_index=scene_idx,
            track_render_index=0,
        )
        seg["extra_material_refs"] = [
            speed_id, ph_id, canvas_id, sc_id, mc_id, loud_id, vs_id,
        ]
        seg["clip"] = {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.0},
        }
        seg["uniform_scale"] = {"on": True, "value": 1.0}

        # Ken Burns effect cho ảnh tĩnh
        if enable_ken_burns and visual_type == "image":
            kb_type = kb_effects[scene_idx % len(kb_effects)]
            mood = scene.get("mood", "")
            if mood in ("epic", "dramatic"):
                kb_type = "zoom_in"
            elif mood in ("calm",):
                kb_type = kb_effects[2 + (scene_idx % 2)]
            elif mood in ("tense", "mysterious"):
                kb_type = "zoom_out" if scene_idx % 2 == 0 else "zoom_in"

            seg_id = seg["id"]
            kf_list = _make_ken_burns_keyframes(seg_id, duration_us, kb_type)
            seg["common_keyframes"] = kf_list
            all_video_keyframes.extend(kf_list)

        video_segments.append(seg)

        # Subtitle text segment
        if enable_subtitles:
            script_text = scene.get("script_text", "")
            if script_text:
                txt_mat_id, txt_mat = _make_text_material(script_text)
                text_materials.append(txt_mat)

                anim_id, anim_mat = _make_sticker_animation()
                material_animations.append(anim_mat)

                txt_seg = _make_text_segment(
                    material_id=txt_mat_id,
                    anim_id=anim_id,
                    target_start=start_us,
                    target_duration=duration_us,
                    render_index=14000 + scene_idx,
                    subtitle_y=-0.80 if canvas_width < canvas_height else -0.73,
                )
                text_segments.append(txt_seg)

        # Transition material (between this and next scene)
        if enable_transitions:
            transition_note = scene.get("transition_note", "")
            if transition_note and scene_idx > 0:
                note_lower = transition_note.lower()
                if "cut" in note_lower:
                    pass
                elif "fade" in note_lower and "black" in note_lower:
                    tr_id, tr_mat = _make_transition_material(800_000)
                    transition_materials.append(tr_mat)
                elif "crossfade" in note_lower or "cross" in note_lower:
                    tr_id, tr_mat = _make_transition_material(transition_duration_us)
                    transition_materials.append(tr_mat)
                else:
                    tr_id, tr_mat = _make_transition_material(transition_duration_us)
                    transition_materials.append(tr_mat)

    # Audio segment + material
    if audio_path and Path(audio_path).exists():
        audio_dur = audio_duration_us or total_duration

        # Copy audio vào Resources/
        audio_src = Path(audio_path)
        audio_local = resources_dir / audio_src.name
        shutil.copy2(audio_src, audio_local)
        audio_local_str = str(audio_local)

        aud_mat_id, aud_mat = _make_audio_material(audio_local_str, audio_dur)
        audio_materials.append(aud_mat)

        # Draft material entry for audio
        draft_material_entries.append(
            _make_draft_material_entry(audio_local_str, "music", audio_dur)
        )

        # key_value entry for audio
        aud_key = hashlib.md5(audio_src.name.encode()).hexdigest()
        key_value_data[aud_key] = _make_key_value_entry(audio_src.name)

        # Extra materials for audio segment
        speed_id, speed_mat = _make_speed_material()
        speed_materials.append(speed_mat)

        ph_id, ph_mat = _make_placeholder_info()
        placeholder_infos.append(ph_mat)

        sc_id, sc_mat = _make_sound_channel_mapping()
        sound_channel_mappings.append(sc_mat)

        loud_id, loud_mat = _make_loudness()
        loudnesses.append(loud_mat)

        vs_id, vs_mat = _make_vocal_separation()
        vocal_separations.append(vs_mat)

        aud_seg = _make_segment_base(
            material_id=aud_mat_id,
            target_start=0,
            target_duration=audio_dur,
            source_start=0,
            source_duration=audio_dur,
            render_index=0,
            track_render_index=1,
        )
        aud_seg["extra_material_refs"] = [speed_id, ph_id, sc_id, loud_id, vs_id]
        audio_segments.append(aud_seg)

    # Build draft_info.json
    draft_id = _uuid()
    now_us = int(time.time() * US_PER_SEC)

    draft_info = {
        "canvas_config": {
            "background": None,
            "height": canvas_height,
            "ratio": "original",
            "width": canvas_width,
        },
        "color_space": -1,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "hdr_vivid": False,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "multi_language_current": "none",
            "multi_language_list": [],
            "multi_language_main": "none",
            "multi_language_mode": "none",
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "use_float_render": False,
            "video_mute": False,
            "voice_change_sync": False,
            "zoom_info_params": None,
        },
        "cover": None,
        "create_time": 0,
        "draft_type": "video",
        "duration": total_duration,
        "extra_info": None,
        "fps": 30.0,
        "free_render_index_mode_on": False,
        "function_assistant_info": {
            "audio_noise_segid_list": [], "auto_adjust": False,
            "auto_adjust_fixed": False, "auto_adjust_fixed_value": 50.0,
            "auto_adjust_segid_list": [], "auto_caption": False,
            "auto_caption_segid_list": [], "auto_caption_template_id": "",
            "caption_opt": False, "caption_opt_segid_list": [],
            "color_correction": False, "color_correction_fixed": False,
            "color_correction_fixed_value": 50.0, "color_correction_segid_list": [],
            "deflicker_segid_list": [], "enhance_quality": False,
            "enhance_quality_fixed": False, "enhance_quality_segid_list": [],
            "enhance_voice_segid_list": [], "enhande_voice": False,
            "enhande_voice_fixed": False, "eye_correction": False,
            "eye_correction_segid_list": [], "fixed_rec_applied": False,
            "fps": {"den": 1, "num": 0}, "normalize_loudness": False,
            "normalize_loudness_audio_denoise_segid_list": [],
            "normalize_loudness_fixed": False, "normalize_loudness_segid_list": [],
            "retouch": False, "retouch_fixed": False, "retouch_segid_list": [],
            "smart_rec_applied": False, "smart_segid_list": [],
            "smooth_slow_motion": False, "smooth_slow_motion_fixed": False,
            "video_noise_segid_list": [],
        },
        "group_container": None,
        "id": draft_id,
        "is_drop_frame_timecode": False,
        "keyframe_graph_list": [],
        "keyframes": {
            "adjusts": [], "audios": [], "effects": [], "filters": [],
            "handwrites": [], "stickers": [], "texts": [], "videos": [],
        },
        "last_modified_platform": device_info,
        "lyrics_effects": [],
        "materials": {
            "ai_text_effects": [], "ai_translates": [], "audio_balances": [],
            "audio_effects": [], "audio_fades": [], "audio_pannings": [],
            "audio_pitch_shifts": [], "audio_track_indexes": [],
            "audios": audio_materials,
            "beats": [], "canvases": canvas_materials, "chromas": [],
            "color_curves": [], "common_mask": [],
            "digital_human_model_dressing": [], "digital_humans": [],
            "drafts": [], "effects": [], "flowers": [], "green_screens": [],
            "handwrites": [], "hsl": [], "hsl_curves": [], "images": [],
            "log_color_wheels": [],
            "loudnesses": loudnesses,
            "manual_beautys": [],
            "manual_deformations": [],
            "material_animations": material_animations,
            "material_colors": material_colors,
            "multi_language_refs": [],
            "placeholder_infos": placeholder_infos,
            "placeholders": [], "plugin_effects": [],
            "primary_color_wheels": [], "realtime_denoises": [], "shapes": [],
            "smart_crops": [], "smart_relights": [],
            "sound_channel_mappings": sound_channel_mappings,
            "speeds": speed_materials,
            "stickers": [], "tail_leaders": [], "text_templates": [],
            "texts": text_materials,
            "time_marks": [],
            "transitions": transition_materials,
            "video_effects": [], "video_radius": [], "video_shadows": [],
            "video_strokes": [], "video_trackings": [],
            "videos": video_materials,
            "vocal_beautifys": [],
            "vocal_separations": vocal_separations,
        },
        "mixed_track_mode_on": False,
        "mutable_config": None,
        "name": "",
        "new_version": "187.0.0",
        "path": "",
        "platform": device_info,
        "relationships": [],
        "render_index_track_mode_on": True,
        "retouch_cover": None,
        "smart_ads_info": {"draft_url": "", "page_from": "", "routine": ""},
        "source": "default",
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": [
            {
                "attribute": 0, "flag": 0, "id": _uuid(),
                "is_default_name": True, "name": "",
                "segments": video_segments, "type": "video",
            },
            *(
                [{
                    "attribute": 0, "flag": 0, "id": _uuid(),
                    "is_default_name": True, "name": "",
                    "segments": text_segments, "type": "text",
                }] if text_segments else []
            ),
            {
                "attribute": 0, "flag": 0, "id": _uuid(),
                "is_default_name": True, "name": "",
                "segments": audio_segments, "type": "audio",
            },
        ],
        "uneven_animation_template_info": {
            "composition": "", "content": "", "order": "",
            "sub_template_info_list": [],
        },
        "update_time": 0,
        "version": 360000,
    }

    # Write draft_info.json
    draft_info_json = json.dumps(draft_info, ensure_ascii=False)
    draft_info_path = project_dir / "draft_info.json"
    draft_info_path.write_text(draft_info_json, "utf-8")
    draft_info_size = len(draft_info_json.encode("utf-8"))

    # Backup
    shutil.copy2(draft_info_path, project_dir / "draft_info.json.bak")

    # template.tmp (CapCut uses this as initial state reference)
    shutil.copy2(draft_info_path, project_dir / "template.tmp")

    # draft_meta_info.json — with proper draft_materials
    meta = {
        "cloud_draft_cover": False,
        "cloud_draft_sync": False,
        "cloud_package_completed_time": "",
        "draft_cloud_capcut_purchase_info": "",
        "draft_cloud_last_action_download": False,
        "draft_cloud_package_type": "",
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "",
        "draft_deeplink_url": "",
        "draft_enterprise_info": {
            "draft_enterprise_extra": "",
            "draft_enterprise_id": "",
            "draft_enterprise_name": "",
            "enterprise_material": [],
        },
        "draft_fold_path": str(project_dir),
        "draft_has_unfinished_aigc_video_effect": False,
        "draft_id": draft_id,
        "draft_is_ae_produce": False,
        "draft_is_ai_packaging_used": False,
        "draft_is_ai_shorts": canvas_width < canvas_height,
        "draft_is_ai_translate": False,
        "draft_is_article_video_draft": False,
        "draft_is_cloud_temp_draft": False,
        "draft_is_from_deeplink": "false",
        "draft_is_infinite_canvas_draft": False,
        "draft_is_invisible": False,
        "draft_is_pippit_draft": False,
        "draft_is_web_article_video": False,
        "draft_materials": [
            {"type": 0, "value": draft_material_entries},
            {"type": 1, "value": []},
            {"type": 2, "value": []},
            {"type": 3, "value": []},
            {"type": 6, "value": []},
            {"type": 7, "value": []},
            {"type": 8, "value": []},
        ],
        "draft_materials_copied_info": [],
        "draft_name": folder_name,
        "draft_need_rename_folder": False,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": capcut_dir,
        "draft_segment_extra_info": [],
        "draft_timeline_materials_size_": draft_info_size,
        "draft_type": "",
        "draft_web_article_video_enter_from": "",
        "pippit_avatar_url": "",
        "pippit_extra_info": "",
        "pippit_id": "",
        "pippit_user_name": "",
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_entry_id": -1,
        "tm_draft_cloud_modified": 0,
        "tm_draft_cloud_parent_entry_id": -1,
        "tm_draft_cloud_space_id": -1,
        "tm_draft_cloud_user_id": -1,
        "tm_draft_create": now_us,
        "tm_draft_modified": now_us,
        "tm_draft_removed": 0,
        "tm_duration": total_duration,
    }
    (project_dir / "draft_meta_info.json").write_text(
        json.dumps(meta, ensure_ascii=False), "utf-8"
    )

    # Other required files
    (project_dir / "draft_agency_config.json").write_text(
        json.dumps({"agent_id": "", "enter_from": "", "scene_id": ""})
    )
    (project_dir / "draft_biz_config.json").write_text("")
    (project_dir / "draft_virtual_store.json").write_text(
        json.dumps({"draft_virtual_store_data": [], "id": _uuid()})
    )
    (project_dir / "draft_settings").write_text(
        json.dumps({"draft_settings_data": {}})
    )
    (project_dir / "key_value.json").write_text(
        json.dumps(key_value_data, ensure_ascii=False), "utf-8"
    )
    (project_dir / "performance_opt_info.json").write_text(
        json.dumps({"has_unadapted_effect_list": False})
    )

    # Đăng ký project vào root_meta_info.json
    _update_root_meta_info(
        capcut_dir, project_dir, draft_id, folder_name,
        total_duration, draft_info_size,
    )

    scenes_used = len(video_segments)
    return {
        "status": "ok",
        "project_path": str(project_dir),
        "project_name": folder_name,
        "message": f"Đã tạo project CapCut '{folder_name}' với {scenes_used} cảnh. Mở CapCut để xem.",
        "scenes_count": scenes_used,
        "total_duration_sec": total_duration / US_PER_SEC,
    }
