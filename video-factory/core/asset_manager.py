import json
import shutil
from pathlib import Path
from datetime import datetime
from .config import BASE_DIR


class AssetManager:
    def __init__(self, project_id: str, video_id: str):
        self.project_id = project_id
        self.video_id = video_id
        self.video_dir = BASE_DIR / project_id / "videos" / video_id
        self.images_dir = self.video_dir / "assets" / "images"
        self.videos_dir = self.video_dir / "assets" / "videos"
        self.log_path = self.video_dir / "assets" / "generation_log.json"

    def init_dirs(self):
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)

    def get_asset_path(self, scene_number: int, visual_type: str, version: int = None) -> Path:
        """Get path for an asset. If version not specified, get latest."""
        ext = "mp4" if visual_type == "video" else "png"
        base_dir = self.videos_dir if visual_type == "video" else self.images_dir

        if version:
            return base_dir / f"scene_{scene_number:03d}_v{version}.{ext}"

        # Find latest version
        pattern = f"scene_{scene_number:03d}_v*.{ext}"
        existing = sorted(base_dir.glob(pattern))
        if existing:
            return existing[-1]
        return base_dir / f"scene_{scene_number:03d}_v1.{ext}"

    def get_next_version(self, scene_number: int, visual_type: str) -> int:
        """Get next version number for a scene"""
        ext = "mp4" if visual_type == "video" else "png"
        base_dir = self.videos_dir if visual_type == "video" else self.images_dir
        pattern = f"scene_{scene_number:03d}_v*.{ext}"
        existing = sorted(base_dir.glob(pattern))
        if existing:
            last = existing[-1].stem
            current_v = int(last.split("_v")[-1])
            return current_v + 1
        return 1

    def list_versions(self, scene_number: int, visual_type: str) -> list[dict]:
        """List all versions of a scene asset"""
        ext = "mp4" if visual_type == "video" else "png"
        base_dir = self.videos_dir if visual_type == "video" else self.images_dir
        pattern = f"scene_{scene_number:03d}_v*.{ext}"
        versions = []
        for f in sorted(base_dir.glob(pattern)):
            v = int(f.stem.split("_v")[-1])
            versions.append({
                "version": v,
                "path": str(f),
                "filename": f.name,
                "size": f.stat().st_size,
                "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        return versions

    def log_generation(self, scene_number: int, prompt: str, version: int, status: str):
        """Log asset generation attempt"""
        log = self._load_log()
        log.append({
            "scene_number": scene_number,
            "prompt": prompt,
            "version": version,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
        self._save_log(log)

    def _load_log(self) -> list:
        if self.log_path.exists():
            return json.loads(self.log_path.read_text())
        return []

    def _save_log(self, log: list):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2))
