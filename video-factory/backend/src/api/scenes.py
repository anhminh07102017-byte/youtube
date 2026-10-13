import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

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
    edit_plan: Optional[Dict[str, Any]] = None
    flow_characters: Optional[List[str]] = None
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
    edit_plan: Optional[Dict[str, Any]] = None


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
    project_id: str, video_id: str, scene_number: int, db: AsyncSession,
    is_short: bool = False,
) -> Scene:
    result = await db.execute(
        select(Scene).where(
            Scene.video_id == video_id,
            Scene.project_id == project_id,
            Scene.scene_number == scene_number,
            Scene.is_short == is_short,
        )
    )
    scene = result.scalar_one_or_none()
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


@router.get("")
async def list_scenes(
    project_id: str, video_id: str,
    is_short: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List scenes for a video. is_short=true for short scenes."""
    await _get_video_or_404(project_id, video_id, db)

    result = await db.execute(
        select(Scene)
        .where(Scene.video_id == video_id, Scene.project_id == project_id, Scene.is_short == is_short)
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
    is_short: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Update a scene's prompt, timing, type, or status."""
    await _get_video_or_404(project_id, video_id, db)
    scene = await _get_scene_or_404(project_id, video_id, scene_number, db, is_short)

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
    is_short: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Update just the scene status (approve, redo, etc.)."""
    await _get_video_or_404(project_id, video_id, db)
    scene = await _get_scene_or_404(project_id, video_id, scene_number, db, is_short)

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


class SceneMerge(BaseModel):
    scene_numbers: List[int]  # phải liên tiếp


@router.post("/merge")
async def merge_scenes(
    project_id: str,
    video_id: str,
    body: SceneMerge,
    db: AsyncSession = Depends(get_db),
):
    """Gộp nhiều phân đoạn liên tiếp thành 1."""
    await _get_video_or_404(project_id, video_id, db)

    if len(body.scene_numbers) < 2:
        raise HTTPException(400, "Cần ít nhất 2 phân đoạn để gộp.")

    nums = sorted(body.scene_numbers)
    # Kiểm tra liên tiếp
    for i in range(1, len(nums)):
        if nums[i] != nums[i - 1] + 1:
            raise HTTPException(400, "Các phân đoạn phải liên tiếp.")

    # Lấy tất cả scenes
    result = await db.execute(
        select(Scene)
        .where(Scene.video_id == video_id, Scene.project_id == project_id)
        .order_by(Scene.scene_number)
    )
    all_scenes = result.scalars().all()
    scenes_map = {s.scene_number: s for s in all_scenes}

    # Kiểm tra tồn tại
    to_merge = []
    for n in nums:
        if n not in scenes_map:
            raise HTTPException(404, f"Không tìm thấy phân đoạn {n}")
        to_merge.append(scenes_map[n])

    # Gộp: scene đầu tiên giữ lại, mở rộng timestamp + ghép text
    keep = to_merge[0]
    keep.timestamp_end = to_merge[-1].timestamp_end
    keep.script_text = " ".join(s.script_text or "" for s in to_merge).strip()
    keep.veo3_prompt = None
    keep.mood = None
    keep.edit_plan = None
    keep.asset_path = None
    keep.asset_version = 0
    keep.status = "pending"
    keep.updated_at = datetime.now(timezone.utc)

    # Xóa scenes còn lại
    for s in to_merge[1:]:
        await db.delete(s)

    # Renumber: đánh lại số thứ tự liên tục
    await db.flush()
    result2 = await db.execute(
        select(Scene)
        .where(Scene.video_id == video_id, Scene.project_id == project_id)
        .order_by(Scene.scene_number)
    )
    remaining = result2.scalars().all()
    for i, s in enumerate(remaining):
        s.scene_number = i + 1

    await db.commit()

    # Trả về danh sách mới
    result3 = await db.execute(
        select(Scene)
        .where(Scene.video_id == video_id, Scene.project_id == project_id)
        .order_by(Scene.scene_number)
    )
    return [s.to_dict() for s in result3.scalars().all()]


class SceneBatchAction(BaseModel):
    scene_numbers: List[int]


@router.post("/batch-clear-prompts")
async def batch_clear_prompts(
    project_id: str,
    video_id: str,
    body: SceneBatchAction,
    db: AsyncSession = Depends(get_db),
):
    """Xóa prompt của các phân đoạn được chọn."""
    await _get_video_or_404(project_id, video_id, db)
    result = await db.execute(
        select(Scene).where(
            Scene.video_id == video_id,
            Scene.project_id == project_id,
            Scene.scene_number.in_(body.scene_numbers),
        )
    )
    scenes = result.scalars().all()
    for scene in scenes:
        scene.veo3_prompt = None
        scene.mood = None
        scene.edit_plan = None
        scene.status = "pending"
        scene.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ok", "cleared": len(scenes)}


@router.post("/batch-clear-assets")
async def batch_clear_assets(
    project_id: str,
    video_id: str,
    body: SceneBatchAction,
    db: AsyncSession = Depends(get_db),
):
    """Xóa assets của các phân đoạn được chọn."""
    await _get_video_or_404(project_id, video_id, db)
    result = await db.execute(
        select(Scene).where(
            Scene.video_id == video_id,
            Scene.project_id == project_id,
            Scene.scene_number.in_(body.scene_numbers),
        )
    )
    scenes = result.scalars().all()
    cleared = 0
    for scene in scenes:
        if scene.asset_path:
            asset_file = Path(scene.asset_path)
            if asset_file.exists():
                asset_file.unlink()
            scene.asset_path = None
            scene.asset_version = 0
            scene.status = "pending" if not scene.veo3_prompt else "review"
            scene.updated_at = datetime.now(timezone.utc)
            cleared += 1
    await db.commit()
    return {"status": "ok", "cleared": cleared}


@router.delete("/prompts")
async def clear_all_prompts(
    project_id: str,
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Xóa tất cả prompt đã tạo cho video này."""
    await _get_video_or_404(project_id, video_id, db)
    result = await db.execute(
        select(Scene).where(Scene.video_id == video_id, Scene.project_id == project_id)
    )
    scenes = result.scalars().all()
    cleared = 0
    for scene in scenes:
        if scene.veo3_prompt:
            scene.veo3_prompt = None
            scene.mood = None
            scene.edit_plan = None
            scene.flow_characters = None
            scene.status = "pending"
            scene.updated_at = datetime.now(timezone.utc)
            cleared += 1
    await db.commit()

    # Xóa director_plan.json và visual_plan.json
    video_dir = Path(PROJECTS_DIR) / project_id / "videos" / video_id
    for fname in ["director_plan.json", "visual_plan.json"]:
        p = video_dir / fname
        if p.exists():
            p.unlink()

    return {"status": "ok", "cleared": cleared}


@router.delete("/characters")
async def clear_scene_characters(
    project_id: str,
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Xóa nhân vật gắn trong tất cả cảnh (flow_characters)."""
    await _get_video_or_404(project_id, video_id, db)
    result = await db.execute(
        select(Scene).where(Scene.video_id == video_id, Scene.project_id == project_id)
    )
    scenes = result.scalars().all()
    cleared = 0
    for scene in scenes:
        if scene.flow_characters:
            scene.flow_characters = None
            scene.updated_at = datetime.now(timezone.utc)
            cleared += 1
    await db.commit()
    return {"status": "ok", "cleared": cleared}


@router.delete("/assets")
async def clear_all_assets(
    project_id: str,
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Xóa tất cả asset (ảnh/video) đã tạo cho video này."""
    import shutil

    await _get_video_or_404(project_id, video_id, db)
    result = await db.execute(
        select(Scene).where(Scene.video_id == video_id, Scene.project_id == project_id)
    )
    scenes = result.scalars().all()
    cleared = 0
    for scene in scenes:
        if scene.asset_path:
            # Xóa file thực
            asset_file = Path(scene.asset_path)
            if asset_file.exists():
                asset_file.unlink()
            scene.asset_path = None
            scene.asset_version = 0
            scene.status = "pending" if not scene.veo3_prompt else "review"
            scene.updated_at = datetime.now(timezone.utc)
            cleared += 1
    await db.commit()

    # Xóa toàn bộ thư mục assets
    assets_dir = Path(PROJECTS_DIR) / project_id / "videos" / video_id / "assets"
    if assets_dir.exists():
        shutil.rmtree(assets_dir)

    return {"status": "ok", "cleared": cleared}


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


@router.delete("")
async def delete_all_scenes(
    project_id: str,
    video_id: str,
    is_short: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Xóa tất cả phân đoạn của video (hoặc short)."""
    import shutil

    video = await _get_video_or_404(project_id, video_id, db)

    await db.execute(
        delete(Scene).where(
            Scene.video_id == video_id, Scene.project_id == project_id,
            Scene.is_short == is_short,
        )
    )

    if not is_short:
        # Reset video status
        if video.status not in ("draft", "script_ready", "audio_ready"):
            video.status = "audio_ready" if video.audio_path else "draft"
        video.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Xóa assets + plan files
    video_dir = Path(PROJECTS_DIR) / project_id / "videos" / video_id
    sub = video_dir / "shorts" if is_short else video_dir
    assets_dir = sub / "assets"
    if assets_dir.exists():
        shutil.rmtree(assets_dir)
        assets_dir.mkdir(exist_ok=True)
    for fname in ["director_plan.json", "visual_plan.json", "shot_list.json"]:
        p = sub / fname
        if p.exists():
            p.unlink()

    return {"status": "ok"}


@router.post("/bulk")
async def bulk_create_scenes(
    project_id: str,
    video_id: str,
    body: SceneBulkCreate,
    is_short: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Replace all scenes with a new set (from SRT/AI split)."""
    video = await _get_video_or_404(project_id, video_id, db)

    # Delete existing scenes (only same type)
    await db.execute(
        delete(Scene).where(
            Scene.video_id == video_id, Scene.project_id == project_id,
            Scene.is_short == is_short,
        )
    )

    # Create new scenes
    new_scenes = []
    for item in body.scenes:
        scene = Scene(
            video_id=video_id,
            project_id=project_id,
            is_short=is_short,
            scene_number=item.scene_number,
            timestamp_start=item.timestamp_start,
            timestamp_end=item.timestamp_end,
            script_text=item.script_text,
            visual_type=item.visual_type,
            veo3_prompt=item.veo3_prompt,
            mood=item.mood,
            effect=item.effect,
            edit_plan=item.edit_plan,
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
