import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Project, Video
from src.services.file_sync import sync_video_status

router = APIRouter(prefix="/api/projects/{project_id}/videos", tags=["videos"])

PROJECTS_DIR = os.getenv("PROJECTS_DIR", "/app/projects")


class VideoCreate(BaseModel):
    title: str
    id: Optional[str] = None
    target_duration: Optional[int] = None  # minutes


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    flow_project_id: Optional[str] = None


class ScriptBody(BaseModel):
    content: str


def _video_dir(project_id: str, video_id: str) -> Path:
    return Path(PROJECTS_DIR) / project_id / "videos" / video_id


async def _get_project_or_404(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_video_or_404(project_id: str, video_id: str, db: AsyncSession) -> Video:
    result = await db.execute(
        select(Video).where(Video.id == video_id, Video.project_id == project_id)
    )
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("")
async def list_videos(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all videos in a project."""
    await _get_project_or_404(project_id, db)

    result = await db.execute(
        select(Video).where(Video.project_id == project_id).order_by(Video.created_at.desc())
    )
    videos = result.scalars().all()
    return [v.to_dict() for v in videos]


@router.post("", status_code=201)
async def create_video(project_id: str, body: VideoCreate, db: AsyncSession = Depends(get_db)):
    """Create a new video entry with folder structure."""
    await _get_project_or_404(project_id, db)

    # Generate video ID from title (normalize Vietnamese)
    if body.id:
        video_id = body.id
    else:
        slug = body.title.lower()
        slug = unicodedata.normalize("NFD", slug)
        slug = re.sub(r"[\u0300-\u036f]", "", slug)
        slug = slug.replace("đ", "d").replace("Đ", "d")
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = slug.strip()
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug[:50]
        short_id = uuid.uuid4().hex[:6]
        video_id = f"{slug}-{short_id}"

    video = Video(
        id=video_id,
        project_id=project_id,
        title=body.title,
        target_duration=body.target_duration,
        status="draft",
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Create folder structure
    vdir = _video_dir(project_id, video_id)
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "audio").mkdir(exist_ok=True)
    (vdir / "assets").mkdir(exist_ok=True)
    (vdir / "shorts").mkdir(exist_ok=True)
    (vdir / "shorts" / "audio").mkdir(exist_ok=True)
    (vdir / "shorts" / "assets").mkdir(exist_ok=True)

    return video.to_dict()


@router.get("/{video_id}")
async def get_video(project_id: str, video_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single video with synced status."""
    video = await _get_video_or_404(project_id, video_id, db)

    # Sync status from filesystem
    await sync_video_status(db, video)

    return video.to_dict()


@router.put("/{video_id}")
async def update_video(
    project_id: str, video_id: str, body: VideoUpdate, db: AsyncSession = Depends(get_db)
):
    """Update video metadata."""
    video = await _get_video_or_404(project_id, video_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(video, key, value)
    video.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(video)
    return video.to_dict()


@router.get("/{video_id}/script")
async def get_script(project_id: str, video_id: str, db: AsyncSession = Depends(get_db)):
    """Read the script.md file for a video."""
    await _get_video_or_404(project_id, video_id, db)

    script_path = _video_dir(project_id, video_id) / "script.md"
    if not script_path.exists():
        return {"content": "", "exists": False}

    content = script_path.read_text(encoding="utf-8")
    return {"content": content, "exists": True}


@router.put("/{video_id}/script")
async def save_script(
    project_id: str, video_id: str, body: ScriptBody, db: AsyncSession = Depends(get_db)
):
    """Save the script.md file and update status."""
    video = await _get_video_or_404(project_id, video_id, db)

    vdir = _video_dir(project_id, video_id)
    vdir.mkdir(parents=True, exist_ok=True)

    script_path = vdir / "script.md"
    script_path.write_text(body.content, encoding="utf-8")

    video.script_path = str(script_path)
    if video.status == "draft":
        video.status = "script_ready"
    video.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(video)
    return video.to_dict()


@router.post("/{video_id}/audio")
async def upload_audio(
    project_id: str,
    video_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an audio file for the video."""
    video = await _get_video_or_404(project_id, video_id, db)

    vdir = _video_dir(project_id, video_id)
    audio_dir = vdir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Save the uploaded file
    filename = file.filename or "narration.mp3"
    audio_path = audio_dir / filename

    content = await file.read()
    audio_path.write_bytes(content)

    video.audio_path = str(audio_path)
    if video.status in ("draft", "script_ready"):
        video.status = "audio_ready"
    video.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(video)
    return video.to_dict()


@router.get("/{video_id}/audio")
async def stream_audio(project_id: str, video_id: str, db: AsyncSession = Depends(get_db)):
    """Stream the audio file."""
    video = await _get_video_or_404(project_id, video_id, db)

    if not video.audio_path or not Path(video.audio_path).exists():
        # Try to find any audio file
        audio_dir = _video_dir(project_id, video_id) / "audio"
        if audio_dir.exists():
            audio_files = list(audio_dir.glob("*.*"))
            if audio_files:
                return FileResponse(str(audio_files[0]))

        raise HTTPException(status_code=404, detail="No audio file found")

    return FileResponse(video.audio_path)


@router.post("/{video_id}/srt")
async def upload_srt(
    project_id: str,
    video_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an SRT subtitle file."""
    video = await _get_video_or_404(project_id, video_id, db)

    vdir = _video_dir(project_id, video_id)
    audio_dir = vdir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    srt_path = audio_dir / "subtitles.srt"
    content = await file.read()
    srt_path.write_bytes(content)

    video.srt_path = str(srt_path)
    video.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(video)
    return video.to_dict()


@router.post("/{video_id}/export/capcut")
async def export_capcut(project_id: str, video_id: str, db: AsyncSession = Depends(get_db)):
    """Build CapCut project from approved scenes."""
    video = await _get_video_or_404(project_id, video_id, db)
    return {"status": "not_implemented", "message": "Chức năng xuất CapCut đang phát triển."}


@router.get("/{video_id}/srt")
async def get_srt(project_id: str, video_id: str, db: AsyncSession = Depends(get_db)):
    """Read the SRT file content."""
    video = await _get_video_or_404(project_id, video_id, db)

    srt_path = _video_dir(project_id, video_id) / "audio" / "subtitles.srt"
    if not srt_path.exists():
        return {"content": "", "exists": False}

    content = srt_path.read_text(encoding="utf-8")
    return {"content": content, "exists": True}


@router.delete("/{video_id}/srt")
async def delete_srt(project_id: str, video_id: str, db: AsyncSession = Depends(get_db)):
    """Xóa file SRT."""
    video = await _get_video_or_404(project_id, video_id, db)

    srt_path = _video_dir(project_id, video_id) / "audio" / "subtitles.srt"
    if srt_path.exists():
        srt_path.unlink()

    video.srt_path = None
    video.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "ok"}
