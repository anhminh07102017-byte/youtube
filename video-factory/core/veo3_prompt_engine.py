import json
from pathlib import Path
from .config import STYLE_GUIDES_DIR
from .character_manager import CharacterManager


class Veo3PromptEngine:
    def __init__(self, project_id: str, era: str, base_style_name: str = "base_2d_style"):
        self.project_id = project_id
        self.era = era
        self.base_style = self._load_base_style(base_style_name)
        self.era_style = self._load_era_style(era)
        self.character_manager = CharacterManager(project_id)

    def _load_base_style(self, base_style_name: str) -> dict:
        path = STYLE_GUIDES_DIR / f"{base_style_name}.json"
        if not path.exists():
            path = STYLE_GUIDES_DIR / "base_2d_style.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def _load_era_style(self, era: str) -> dict:
        path = STYLE_GUIDES_DIR / "eras" / f"{era}.json"
        if not path.exists():
            path = STYLE_GUIDES_DIR / "world" / f"{era}.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def _build_style_prefix(self) -> str:
        """Build style prefix từ base + era (Layer 1 + 2)."""
        parts = []
        if self.base_style:
            parts.append(self.base_style.get("base_prompt_prefix", ""))
        if self.era_style:
            parts.append(self.era_style.get("prompt_addition", ""))
        return ", ".join(filter(None, parts))

    def _build_character_desc(self, scene: dict) -> str:
        """Build character description (Layer 3)."""
        character_prompts = []
        for cid in scene.get("character_ids", []):
            char = self.character_manager.get_character(cid)
            if char:
                variant = scene.get("character_variant")
                if variant and variant in char.get("visual_variants", {}):
                    character_prompts.append(char["visual_variants"][variant])
                else:
                    character_prompts.append(char.get("visual_prompt_base", ""))
        return ", ".join(filter(None, character_prompts))

    def _build_text_preservation_note(self, scene: dict) -> str:
        """Build note giữ nguyên text gốc (tiếng Việt hoặc ngôn ngữ khác)."""
        texts = []
        if scene.get("text_overlay"):
            texts.append(scene["text_overlay"])
        # Backward compatible: hỗ trợ cả character_names_vi và character_names
        for key in ("character_names_vi", "character_names"):
            if scene.get(key):
                texts.extend(scene[key])
        if texts:
            return (
                'IMPORTANT: Keep these texts exactly as-is '
                '(do NOT translate or transliterate): '
                + ", ".join(f'"{t}"' for t in texts)
            )
        return ""

    # Backward compatible alias
    _build_vn_text_note = _build_text_preservation_note

    def build_prompt(self, scene: dict) -> dict:
        """Build prompt cho IMAGE (ảnh tĩnh).

        scene = {
            "scene_number": 1,
            "script_text": "...",
            "visual_type": "image",
            "character_ids": ["hai_ba_trung"],
            "character_variant": "battle",
            "scene_description": "Wide shot of Hai Ba Trung on elephant",
            "camera_shot": "establishing",
            "mood": "epic",
            "text_overlay": "TRƯNG TRẮC",
            "character_names_vi": ["Trưng Trắc", "Trưng Nhị"],
        }
        """
        parts = [self._build_style_prefix()]

        char_desc = self._build_character_desc(scene)
        if char_desc:
            parts.append(char_desc)

        if scene.get("scene_description"):
            parts.append(scene["scene_description"])
        if scene.get("camera_shot"):
            parts.append(f"camera: {scene['camera_shot']}")
        if scene.get("mood"):
            parts.append(f"{scene['mood']} mood")

        if self.base_style:
            parts.append(self.base_style.get("base_prompt_suffix", ""))

        prompt = ", ".join(filter(None, parts))

        vn_note = self._build_vn_text_note(scene)
        if vn_note:
            prompt = f"{prompt}. {vn_note}"

        return {
            "positive": prompt,
            "negative": self.base_style.get("negative_prompts", ""),
        }

    def build_video_prompt(self, scene: dict) -> dict:
        """Build prompt cho VIDEO (clip Veo 3) với timestamp-based timeline.

        scene = {
            "scene_number": 5,
            "visual_type": "video",
            "duration": 8,
            "character_ids": ["trung_trac"],
            "scene_description": "Hai Bà Trưng dẫn quân khởi nghĩa",
            "mood": "epic",
            "timeline": [
                {"time": "0-3s", "action": "Wide shot of misty river delta at dawn..."},
                {"time": "3-6s", "action": "War elephant emerges from fog..."},
                {"time": "6-8s", "action": "Close-up of Trung Trac's face..."},
            ],
            "camera_style": "cinematic, slow movements",
            "audio_direction": "war drums building, elephant footsteps, wind",
            "text_overlay": "TRƯNG TRẮC",
            "character_names_vi": ["Trưng Trắc"],
            "negative_instructions": [],
        }
        """
        sections = []

        # --- Header: style + character binding ---
        style = self._build_style_prefix()
        sections.append(f"{style}.")

        # Duration
        duration = scene.get("duration", 8)
        sections.append(f"Duration: {duration} seconds.")

        # Negative instructions (no subtitles, no BGM, etc.)
        neg_instructions = scene.get("negative_instructions", [])
        default_neg = ["No subtitles", "No on-screen text unless specified"]
        all_neg = list(set(default_neg + neg_instructions))
        if all_neg:
            sections.append(" ".join(f"{n}." for n in all_neg))

        # Character binding — mô tả nhân vật để giữ nhất quán
        char_desc = self._build_character_desc(scene)
        if char_desc:
            sections.append(f"Characters: {char_desc}.")

        # Camera style
        if scene.get("camera_style"):
            sections.append(f"Camera: {scene['camera_style']}.")

        # Mood
        if scene.get("mood"):
            sections.append(f"Mood: {scene['mood']}.")

        # Summary (mô tả tổng quan)
        if scene.get("scene_description"):
            sections.append(f"Summary: {scene['scene_description']}.")

        # --- Timeline: timestamp-based actions ---
        timeline = scene.get("timeline", [])
        if timeline:
            for entry in timeline:
                t = entry.get("time", "")
                action = entry.get("action", "")
                sections.append(f"{t}: {action}")

        # Audio direction
        if scene.get("audio_direction"):
            sections.append(f"Audio: {scene['audio_direction']}.")

        # Vietnamese text note
        vn_note = self._build_vn_text_note(scene)
        if vn_note:
            sections.append(vn_note)

        prompt = "\n".join(filter(None, sections))

        return {
            "positive": prompt,
            "negative": self.base_style.get("negative_prompts", ""),
            "type": "video",
            "duration": duration,
        }

    def build_prompt_for_scene(self, scene: dict) -> dict:
        """Auto-detect image/video và build prompt tương ứng."""
        gen_type = scene.get("generation_type", scene.get("visual_type", "image"))
        if gen_type == "video":
            return self.build_video_prompt(scene)
        return self.build_prompt(scene)

    def build_prompts_for_shotlist(self, scenes: list[dict]) -> list[dict]:
        """Build prompts cho toàn bộ shot list."""
        results = []
        for scene in scenes:
            prompt = self.build_prompt_for_scene(scene)
            results.append({
                "scene_number": scene.get("scene_number"),
                "prompt": prompt,
                "generation_type": scene.get("generation_type",
                                              scene.get("visual_type", "image")),
            })
        return results
