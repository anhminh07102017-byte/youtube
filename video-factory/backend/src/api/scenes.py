import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Video, Scene

router = APIRouter(
    prefix="/api/projects/{project_id}/videos/{video_id}/scenes",
    tags=["scenes"],
)

PROJECTS_DIR = os.getenv("PROJECTS_DIR", "/app/projects")


class SceneUpdate(BaseModel):
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    script_text: Optional[str] = None
    visual_type: Optional[str] = None
    content_tag: Optional[str] = None
    veo3_prompt: Optional[str] = None
    camera_movement: Optional[str] = None
    mood: Optional[str] = None
    effect: Optional[str] = None
    text_overlay: Optional[str] = None
    asset_path: Optional[str] = None
    asset_version: Optional[int] = None
    status: Optional[str] = None


class SceneStatusUpdate(BaseModel):
    status: str  # approved, redo, pending, generating, review


class SceneBulkItem(BaseModel):
    scene_number: int
    timestamp_start: float
    timestamp_end: float
    script_text: str = ""
    visual_type: str = "image"
    content_tag: Optional[str] = None
    veo3_prompt: Optional[str] = None
    mood: Optional[str] = None
    effect: Optional[str] = None


class SceneBulkCreate(BaseModel):
    scenes: List[SceneBulkItem]


def _assets_dir(project_id: str, video_id: str) -> Path:
    return Path(PROJECTS_DIR) / project_id / "videos" / video_id / "assets"


async def _get_video_or_404(project_id: str, video_id: str, db: AsyncSession) -> Video:
    result = await db.execute(
        select(Video).where(Video.id == video_id, Video.project_id == project_id)
    )
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


async def _get_scene_or_404(
    project_id: str, video_id: str, scene_number: int, db: AsyncSession
) -> Scene:
    result = await db.execute(
        select(Scene).where(
            Scene.video_id == video_id,
            Scene.project_id == project_id,
            Scene.scene_number == scene_number,
        )
    )
    scene = result.scalar_one_or_none()
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.get("")
async def list_scenes(
    project_id: str, video_id: str, db: AsyncSession = Depends(get_db)
):
    """List all scenes (shot list) for a video."""
    await _get_video_or_404(project_id, video_id, db)

    result = await db.execute(
        select(Scene)
        .where(Scene.video_id == video_id, Scene.project_id == project_id)
        .order_by(Scene.scene_number)
    )
    scenes = result.scalars().all()
    return [s.to_dict() for s in scenes]


@router.put("/{scene_number}")
async def update_scene(
    project_id: str,
    video_id: str,
    scene_number: int,
    body: SceneUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a scene's prompt, timing, type, or status."""
    await _get_video_or_404(project_id, video_id, db)
    scene = await _get_scene_or_404(project_id, video_id, scene_number, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(scene, key, value)
    scene.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(scene)
    return scene.to_dict()


@router.put("/{scene_number}/status")
async def update_scene_status(
    project_id: str,
    video_id: str,
    scene_number: int,
    body: SceneStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update just the scene status (approve, redo, etc.)."""
    await _get_video_or_404(project_id, video_id, db)
    scene = await _get_scene_or_404(project_id, video_id, scene_number, db)

    valid_statuses = {"pending", "generating", "review", "approved", "redo"}
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    scene.status = body.status
    scene.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(scene)
    return scene.to_dict()


@router.get("/{scene_number}/asset")
async def get_scene_asset(
    project_id: str,
    video_id: str,
    scene_number: int,
    db: AsyncSession = Depends(get_db),
):
    """Serve the asset file (image or video) for a scene."""
    await _get_video_or_404(project_id, video_id, db)
    scene = await _get_scene_or_404(project_id, video_id, scene_number, db)

    # If scene has an explicit asset_path, use it
    if scene.asset_path:
        asset_file = Path(scene.asset_path)
        if asset_file.exists():
            return FileResponse(str(asset_file))

    # Otherwise look in the assets directory with naming convention
    assets = _assets_dir(project_id, video_id)
    if not assets.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    # Look for scene_NNN.* pattern
    pattern = f"scene_{scene_number:03d}"
    for f in sorted(assets.iterdir(), reverse=True):
        if f.stem.startswith(pattern):
            return FileResponse(str(f))

    raise HTTPException(status_code=404, detail="Asset not found")


@router.get("/{scene_number}/versions")
async def list_asset_versions(
    project_id: str,
    video_id: str,
    scene_number: int,
    db: AsyncSession = Depends(get_db),
):
    """List all asset versions for a scene."""
    await _get_video_or_404(project_id, video_id, db)

    assets = _assets_dir(project_id, video_id)
    if not assets.exists():
        return []

    pattern = f"scene_{scene_number:03d}"
    versions = []
    for f in sorted(assets.iterdir()):
        if f.stem.startswith(pattern):
            stat = f.stat()
            versions.append({
                "filename": f.name,
                "path": str(f),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })

    return versions


@router.post("/bulk")
async def bulk_create_scenes(
    project_id: str,
    video_id: str,
    body: SceneBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    """Replace all scenes with a new set (from SRT/AI split)."""
    video = await _get_video_or_404(project_id, video_id, db)

    # Delete existing scenes
    await db.execute(
        delete(Scene).where(
            Scene.video_id == video_id, Scene.project_id == project_id
        )
    )

    # Create new scenes
    new_scenes = []
    for item in body.scenes:
        scene = Scene(
            video_id=video_id,
            project_id=project_id,
            scene_number=item.scene_number,
            timestamp_start=item.timestamp_start,
            timestamp_end=item.timestamp_end,
            script_text=item.script_text,
            visual_type=item.visual_type,
            veo3_prompt=item.veo3_prompt,
            mood=item.mood,
            effect=item.effect,
            status="pending",
        )
        db.add(scene)
        new_scenes.append(scene)

    if video.status in ("draft", "script_ready", "audio_ready"):
        video.status = "shotlist_ready"
    video.updated_at = datetime.now(timezone.utc)

    await db.commit()
    for s in new_scenes:
        await db.refresh(s)
    return [s.to_dict() for s in new_scenes]
