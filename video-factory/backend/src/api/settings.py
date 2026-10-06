import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_PATH = Path(os.getenv("SETTINGS_PATH", "/app/data/settings.json"))

DEFAULTS = {
    "export_method": "ffmpeg",  # "ffmpeg" | "capcut"
    "default_video_duration": 10,  # minutes
    "veo3_clip_duration": 8,  # seconds
    "bgm_volume": -18,  # dB
    "subtitle_burn_in": True,
    "transition_type": "crossfade",  # crossfade | fade_black | cut
    "transition_duration": 0.5,  # seconds
}


def _load() -> dict:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text("utf-8"))
            merged = {**DEFAULTS, **data}
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULTS)


def _save(data: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


class SettingsUpdate(BaseModel):
    export_method: Optional[str] = None
    default_video_duration: Optional[int] = None
    veo3_clip_duration: Optional[int] = None
    bgm_volume: Optional[int] = None
    subtitle_burn_in: Optional[bool] = None
    transition_type: Optional[str] = None
    transition_duration: Optional[float] = None


@router.get("")
async def get_settings():
    """Get all settings."""
    return _load()


@router.put("")
async def update_settings(body: SettingsUpdate):
    """Update settings (partial update)."""
    current = _load()
    update_data = body.model_dump(exclude_unset=True)
    current.update(update_data)
    _save(current)
    return current
