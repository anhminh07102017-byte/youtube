"""API endpoints cho YouTube Short data (guides, audio, SRT).

Short data lưu trong subfolder `shorts/` của video gốc:
  projects/{pid}/videos/{vid}/shorts/
    script.md, narration.md, brainstorm.md
    audio/narration.mp3, audio/subtitles.srt
"""
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/projects/{project_id}/videos/{video_id}/short",
    tags=["shorts"],
)

PROJECTS_DIR = os.getenv("PROJECTS_DIR", "/app/projects")

SHORT_GUIDE_NAMES = {"script", "narration", "brainstorm", "content_brief"}


class GuideBody(BaseModel):
    content: str


def _short_dir(project_id: str, video_id: str) -> Path:
    return Path(PROJECTS_DIR) / project_id / "videos" / video_id / "shorts"


def _file_mtime_iso(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# --- Short Guides ---

@router.get("/guides/{guide_name}")
async def get_short_guide(project_id: str, video_id: str, guide_name: str):
    """Read a short guide file (script, narration, brainstorm)."""
    if guide_name not in SHORT_GUIDE_NAMES:
        raise HTTPException(400, f"Invalid guide: {guide_name}. Allowed: {sorted(SHORT_GUIDE_NAMES)}")

    path = _short_dir(project_id, video_id) / f"{guide_name}.md"
    if not path.exists():
        return {"content": "", "exists": False, "updated_at": None}

    content = path.read_text(encoding="utf-8")
    return {"content": content, "exists": True, "updated_at": _file_mtime_iso(path)}


@router.put("/guides/{guide_name}")
async def save_short_guide(project_id: str, video_id: str, guide_name: str, body: GuideBody):
    """Write a short guide file."""
    if guide_name not in SHORT_GUIDE_NAMES:
        raise HTTPException(400, f"Invalid guide: {guide_name}. Allowed: {sorted(SHORT_GUIDE_NAMES)}")

    sdir = _short_dir(project_id, video_id)
    sdir.mkdir(parents=True, exist_ok=True)
    path = sdir / f"{guide_name}.md"
    path.write_text(body.content, encoding="utf-8")
    return {"content": body.content, "updated_at": _file_mtime_iso(path)}


# --- Short Audio ---

@router.post("/audio")
async def upload_short_audio(project_id: str, video_id: str, file: UploadFile = File(...)):
    """Upload audio file for short."""
    sdir = _short_dir(project_id, video_id)
    audio_dir = sdir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or "narration.mp3"
    audio_path = audio_dir / filename
    content = await file.read()
    audio_path.write_bytes(content)

    return {"status": "ok", "path": str(audio_path)}


@router.get("/audio")
async def stream_short_audio(project_id: str, video_id: str):
    """Stream the short audio file."""
    audio_dir = _short_dir(project_id, video_id) / "audio"
    if audio_dir.exists():
        for ext in ["*.mp3", "*.wav", "*.m4a", "*.aac"]:
            files = list(audio_dir.glob(ext))
            if files:
                return FileResponse(str(files[0]))
    raise HTTPException(404, "No short audio file found")


@router.get("/audio/status")
async def short_audio_status(project_id: str, video_id: str):
    """Check if short audio file exists."""
    audio_dir = _short_dir(project_id, video_id) / "audio"
    if audio_dir.exists():
        for ext in ["*.mp3", "*.wav", "*.m4a", "*.aac"]:
            if list(audio_dir.glob(ext)):
                return {"exists": True}
    return {"exists": False}


# --- Short SRT ---

@router.post("/srt")
async def upload_short_srt(project_id: str, video_id: str, file: UploadFile = File(...)):
    """Upload SRT subtitle file for short."""
    sdir = _short_dir(project_id, video_id)
    audio_dir = sdir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    srt_path = audio_dir / "subtitles.srt"
    content = await file.read()
    srt_path.write_bytes(content)

    return {"status": "ok", "path": str(srt_path)}


@router.get("/srt")
async def get_short_srt(project_id: str, video_id: str):
    """Read the short SRT file."""
    srt_path = _short_dir(project_id, video_id) / "audio" / "subtitles.srt"
    if not srt_path.exists():
        return {"content": "", "exists": False}
    content = srt_path.read_text(encoding="utf-8")
    return {"content": content, "exists": True}


@router.delete("/srt")
async def delete_short_srt(project_id: str, video_id: str):
    """Delete the short SRT file."""
    srt_path = _short_dir(project_id, video_id) / "audio" / "subtitles.srt"
    if srt_path.exists():
        srt_path.unlink()
    return {"status": "ok"}
