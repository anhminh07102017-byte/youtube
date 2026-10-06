import json
from pathlib import Path
from typing import Optional
from .config import CHARACTER_DB_DIR


class CharacterManager:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = CHARACTER_DB_DIR / "projects" / project_id
        self.characters_file = self.project_dir / "characters.json"
        self.refs_dir = self.project_dir / "refs"

    def init_project(self):
        """Create project character directory structure"""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.refs_dir.mkdir(exist_ok=True)
        if not self.characters_file.exists():
            self._save({"characters": []})

    def list_characters(self) -> list[dict]:
        """List all characters in this project"""
        data = self._load()
        return data.get("characters", [])

    def get_character(self, character_id: str) -> Optional[dict]:
        """Get a specific character by ID"""
        data = self._load()
        for char in data.get("characters", []):
            if char.get("id") == character_id:
                return char
        return None

    def add_character(self, character: dict) -> dict:
        """Add a new character"""
        # Validate required fields
        required_fields = ["id", "name", "era", "visual_prompt_base"]
        for field in required_fields:
            if field not in character:
                raise ValueError(f"Missing required field: {field}")

        data = self._load()

        # Check for duplicate ID
        for existing in data.get("characters", []):
            if existing.get("id") == character["id"]:
                raise ValueError(f"Character with id '{character['id']}' already exists")

        data["characters"].append(character)
        self._save(data)
        return character

    def update_character(self, character_id: str, updates: dict) -> dict:
        """Update an existing character"""
        data = self._load()
        for i, char in enumerate(data.get("characters", [])):
            if char.get("id") == character_id:
                data["characters"][i].update(updates)
                self._save(data)
                return data["characters"][i]
        raise ValueError(f"Character not found: {character_id}")

    def delete_character(self, character_id: str):
        """Delete a character"""
        data = self._load()
        original_count = len(data.get("characters", []))
        data["characters"] = [
            c for c in data.get("characters", []) if c.get("id") != character_id
        ]
        if len(data["characters"]) == original_count:
            raise ValueError(f"Character not found: {character_id}")
        self._save(data)

    def get_characters_in_video(self, video_id: str) -> list[dict]:
        """Get characters that appear in a specific video"""
        data = self._load()
        return [
            char
            for char in data.get("characters", [])
            if video_id in char.get("appears_in_videos", [])
        ]

    def _load(self) -> dict:
        if self.characters_file.exists():
            return json.loads(self.characters_file.read_text())
        return {"characters": []}

    def _save(self, data: dict):
        self.characters_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
