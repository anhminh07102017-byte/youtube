import json
from pathlib import Path
from .config import STYLE_GUIDES_DIR
from .character_manager import CharacterManager


class Veo3PromptEngine:
    def __init__(self, project_id: str, era: str):
        self.project_id = project_id
        self.era = era
        self.base_style = self._load_base_style()
        self.era_style = self._load_era_style(era)
        self.character_manager = CharacterManager(project_id)

    def _load_base_style(self) -> dict:
        path = STYLE_GUIDES_DIR / "base_2d_style.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def _load_era_style(self, era: str) -> dict:
        path = STYLE_GUIDES_DIR / "eras" / f"{era}.json"
        if not path.exists():
            path = STYLE_GUIDES_DIR / "world" / f"{era}.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def build_prompt(self, scene: dict) -> str:
        """Build full 3-layer prompt for a scene.

        scene = {
            "script_text": "...",
            "visual_type": "image" or "video",
            "character_ids": ["tran_hung_dao"],
            "character_variant": "battle",  # optional
            "scene_description": "...",
            "camera_movement": "slow pan left",
            "mood": "tense"
        }
        """
        layers = []

        # Layer 1: Base style
        if self.base_style:
            layers.append(self.base_style.get("base_prompt_prefix", ""))

        # Layer 2: Era style
        if self.era_style:
            layers.append(self.era_style.get("prompt_addition", ""))

        # Layer 3: Character + Scene
        character_prompts = []
        for cid in scene.get("character_ids", []):
            char = self.character_manager.get_character(cid)
            if char:
                variant = scene.get("character_variant")
                if variant and variant in char.get("visual_variants", {}):
                    character_prompts.append(char["visual_variants"][variant])
                else:
                    character_prompts.append(char.get("visual_prompt_base", ""))

        if character_prompts:
            layers.append(", ".join(character_prompts))

        # Scene description
        layers.append(scene.get("scene_description", ""))

        # Camera and mood
        if scene.get("camera_movement"):
            layers.append(f"camera {scene['camera_movement']}")
        if scene.get("mood"):
            layers.append(f"{scene['mood']} mood")

        # Suffix
        if self.base_style:
            layers.append(self.base_style.get("base_prompt_suffix", ""))

        prompt = ", ".join(filter(None, layers))

        # Giữ nguyên text tiếng Việt cho tên, title, text overlay trong ảnh
        # VD: text_overlay "Trần Hưng Đạo" → giữ nguyên, không dịch
        vn_texts = []
        if scene.get("text_overlay"):
            vn_texts.append(scene["text_overlay"])
        if scene.get("character_names_vi"):
            vn_texts.extend(scene["character_names_vi"])

        if vn_texts:
            vn_note = "IMPORTANT: Keep these Vietnamese texts exactly as-is in the image (do NOT translate): " + ", ".join(f'"{t}"' for t in vn_texts)
            prompt = f"{prompt}. {vn_note}"

        # Add negative prompts
        negative = self.base_style.get("negative_prompts", "")

        return {"positive": prompt, "negative": negative}

    def build_prompts_for_shotlist(self, scenes: list[dict]) -> list[dict]:
        """Build prompts for all scenes in a shot list"""
        results = []
        for scene in scenes:
            prompt = self.build_prompt(scene)
            results.append({
                "scene_number": scene.get("scene_number"),
                "prompt": prompt,
                "visual_type": scene.get("visual_type", "image"),
            })
        return results
