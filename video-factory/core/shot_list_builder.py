import json
from pathlib import Path
from .config import BASE_DIR, DEFAULT_SCENE_DURATION, SCRIPT_STRUCTURE


class ShotListBuilder:
    def __init__(self, project_id: str, video_id: str):
        self.project_id = project_id
        self.video_id = video_id
        self.video_dir = BASE_DIR / project_id / "videos" / video_id
        self.script_path = self.video_dir / "script.md"
        self.shotlist_path = self.video_dir / "shot_list.json"

    def load_script(self) -> str:
        """Load script content"""
        if self.script_path.exists():
            return self.script_path.read_text()
        raise FileNotFoundError(f"Script not found: {self.script_path}")

    def save_shot_list(self, scenes: list[dict]):
        """Save shot list to JSON"""
        data = {
            "project_id": self.project_id,
            "video_id": self.video_id,
            "total_scenes": len(scenes),
            "scenes": scenes
        }
        self.shotlist_path.parent.mkdir(parents=True, exist_ok=True)
        self.shotlist_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load_shot_list(self) -> dict:
        """Load existing shot list"""
        if self.shotlist_path.exists():
            return json.loads(self.shotlist_path.read_text())
        return {"scenes": []}

    def update_scene(self, scene_number: int, updates: dict):
        """Update a specific scene in the shot list"""
        data = self.load_shot_list()
        for scene in data["scenes"]:
            if scene["scene_number"] == scene_number:
                scene.update(updates)
                break
        self.save_shot_list(data["scenes"])
