import json
from pathlib import Path
from .config import BASE_DIR
from .asset_manager import AssetManager


class CapCutBuilder:
    """
    Builds CapCut Pro Desktop project files.

    NOTE: Full implementation requires reverse-engineering CapCut's
    draft_content.json format from a sample project. User needs to:
    1. Create a sample project in CapCut Pro
    2. Find the project folder (~/Movies/CapCut/User Data/Projects/)
    3. Share the draft_content.json file

    This stub provides the structure and will be completed after
    receiving the sample file.
    """

    def __init__(self, project_id: str, video_id: str):
        self.project_id = project_id
        self.video_id = video_id
        self.video_dir = BASE_DIR / project_id / "videos" / video_id
        self.asset_manager = AssetManager(project_id, video_id)

    def build_project(self, shot_list: dict, audio_path: str, bgm_path: str = None) -> Path:
        """
        Build a CapCut project file from shot list and assets.

        Args:
            shot_list: The shot list dict with scenes
            audio_path: Path to voice narration audio
            bgm_path: Optional path to background music

        Returns:
            Path to the generated project file
        """
        output_dir = self.video_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        project = self._build_project_structure(shot_list, audio_path, bgm_path)

        output_path = output_dir / "draft_content.json"
        output_path.write_text(json.dumps(project, ensure_ascii=False, indent=2))

        return output_path

    def update_scenes(self, scene_numbers: list[int], shot_list: dict) -> Path:
        """
        Partial update: only replace specific scenes in an existing project.

        Args:
            scene_numbers: List of scene numbers to update
            shot_list: Full shot list

        Returns:
            Path to the updated project file
        """
        output_path = self.video_dir / "output" / "draft_content.json"
        if not output_path.exists():
            raise FileNotFoundError("No existing project to update. Run build_project first.")

        project = json.loads(output_path.read_text())
        # TODO: Update specific scenes in the project structure
        # Will be implemented after reverse-engineering CapCut format

        output_path.write_text(json.dumps(project, ensure_ascii=False, indent=2))
        return output_path

    def _build_project_structure(self, shot_list: dict, audio_path: str, bgm_path: str = None) -> dict:
        """
        Build the CapCut project JSON structure.

        TODO: Implement after receiving sample draft_content.json from user.
        Current structure is a placeholder.
        """
        scenes = shot_list.get("scenes", [])

        tracks = {
            "audio_narration": {
                "track": 1,
                "type": "audio",
                "path": audio_path,
                "volume": 1.0
            },
            "visuals": {
                "track": 2,
                "type": "visual",
                "clips": []
            },
            "subtitles": {
                "track": 3,
                "type": "subtitle",
                "items": []
            },
            "bgm": {
                "track": 4,
                "type": "audio",
                "path": bgm_path,
                "volume": 0.18
            } if bgm_path else None,
            "text_overlays": {
                "track": 5,
                "type": "text",
                "items": []
            }
        }

        for scene in scenes:
            sn = scene["scene_number"]
            vt = scene.get("visual_type", "image")
            asset_path = self.asset_manager.get_asset_path(sn, vt)

            tracks["visuals"]["clips"].append({
                "scene_number": sn,
                "path": str(asset_path),
                "start": scene.get("timestamp_start", 0),
                "end": scene.get("timestamp_end", 0),
                "duration": scene.get("timestamp_end", 0) - scene.get("timestamp_start", 0),
                "type": vt,
                "effect": scene.get("effect", "ken_burns_zoom_in" if vt == "image" else None),
                "transition": "cross_dissolve"
            })

            # Subtitle
            if scene.get("script_text"):
                tracks["subtitles"]["items"].append({
                    "text": scene["script_text"],
                    "start": scene.get("timestamp_start", 0),
                    "end": scene.get("timestamp_end", 0)
                })

            # Text overlay
            if scene.get("text_overlay"):
                tracks["text_overlays"]["items"].append({
                    "text": scene["text_overlay"],
                    "start": scene.get("timestamp_start", 0),
                    "end": scene.get("timestamp_start", 0) + 3  # Show for 3 seconds
                })

        return {
            "project_id": self.project_id,
            "video_id": self.video_id,
            "format_version": "placeholder",
            "note": "This is a placeholder structure. Will be replaced with actual CapCut format after reverse-engineering.",
            "tracks": {k: v for k, v in tracks.items() if v is not None}
        }
