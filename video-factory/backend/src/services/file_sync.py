import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Project, Video, Scene

PROJECTS_DIR = os.getenv("PROJECTS_DIR", "/app/projects")


def _generate_id() -> str:
    return uuid.uuid4().hex[:12]


async def scan_projects(db: AsyncSession):
    """Scan the projects directory and sync any existing projects to the database."""
    projects_path = Path(PROJECTS_DIR)
    if not projects_path.exists():
        return

    for entry in projects_path.iterdir():
        if not entry.is_dir():
            continue

        project_json = entry / "project.json"
        if not project_json.exists():
            continue

        try:
            with open(project_json, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        project_id = data.get("id", entry.name)

        # Check if project already exists in DB
        result = await db.execute(select(Project).where(Project.id == project_id))
        existing = result.scalar_one_or_none()

        if existing is None:
            project = Project(
                id=project_id,
                name=data.get("name", entry.name),
                type=data.get("type", "custom"),
                era=data.get("era", ""),
                time_period=data.get("time_period"),
                tone=data.get("tone", "dramatic_narrative"),
                target_duration=data.get("target_duration", 600),
                sources=data.get("sources", []),
                notes=data.get("notes"),
                base_style=data.get("base_style", "base_2d_style"),
                style_override=data.get("style_override"),
            )
            db.add(project)
        else:
            # Update fields from file
            existing.name = data.get("name", existing.name)
            existing.type = data.get("type", existing.type)
            existing.era = data.get("era", existing.era)
            existing.time_period = data.get("time_period", existing.time_period)
            existing.tone = data.get("tone", existing.tone)
            existing.target_duration = data.get("target_duration", existing.target_duration)
            existing.sources = data.get("sources", existing.sources)
            existing.notes = data.get("notes", existing.notes)
            existing.base_style = data.get("base_style", existing.base_style)
            existing.style_override = data.get("style_override", existing.style_override)
            existing.updated_at = datetime.now(timezone.utc)

        await db.commit()

        # Scan for videos inside this project
        await _scan_project_videos(db, project_id, entry)


async def _scan_project_videos(db: AsyncSession, project_id: str, project_path: Path):
    """Scan a project directory for video folders and sync them."""
    videos_dir = project_path / "videos"
    if not videos_dir.exists():
        return

    for video_entry in videos_dir.iterdir():
        if not video_entry.is_dir():
            continue

        video_id = video_entry.name

        result = await db.execute(select(Video).where(Video.id == video_id, Video.project_id == project_id))
        existing = result.scalar_one_or_none()

        if existing is None:
            video = Video(
                id=video_id,
                project_id=project_id,
                title=video_id.replace("-", " ").replace("_", " ").title(),
                status="draft",
            )
            db.add(video)
            await db.commit()
            existing = video

        # Sync status based on files
        await sync_video_status(db, existing, video_entry)


async def sync_video_status(db: AsyncSession, video: Video, video_path: Path = None):
    """Check what files exist and update video status accordingly."""
    if video_path is None:
        video_path = Path(PROJECTS_DIR) / video.project_id / "videos" / video.id

    if not video_path.exists():
        return

    script_path = video_path / "script.md"
    audio_dir = video_path / "audio"
    shotlist_path = video_path / "shot_list.json"
    assets_dir = video_path / "assets"

    updated = False

    # Check script
    if script_path.exists():
        video.script_path = str(script_path)
        if video.status == "draft":
            video.status = "script_ready"
            updated = True

    # Check audio
    if audio_dir.exists() and any(audio_dir.iterdir()):
        audio_files = list(audio_dir.glob("*.*"))
        if audio_files:
            video.audio_path = str(audio_files[0])
            if video.status in ("draft", "script_ready"):
                video.status = "audio_ready"
                updated = True

    # Check shot list
    if shotlist_path.exists():
        video.shotlist_path = str(shotlist_path)
        if video.status in ("draft", "script_ready", "audio_ready"):
            video.status = "shotlist_ready"
            updated = True

        # Import scenes from shot_list.json
        await _sync_scenes_from_shotlist(db, video, shotlist_path)

    # Check assets
    if assets_dir.exists() and any(assets_dir.iterdir()):
        if video.status == "shotlist_ready":
            video.status = "assets_generating"
            updated = True

    if updated:
        video.updated_at = datetime.now(timezone.utc)

    await db.commit()


async def _sync_scenes_from_shotlist(db: AsyncSession, video: Video, shotlist_path: Path):
    """Import scenes from a shot_list.json file into the database.
    Only imports if NO scenes exist yet (initial import).
    Once scenes are in DB, the DB is the source of truth — not the file.
    """
    # Skip if scenes already exist in DB (DB is source of truth after initial import)
    existing_count = await db.execute(
        select(Scene).where(Scene.video_id == video.id, Scene.project_id == video.project_id).limit(1)
    )
    if existing_count.scalar_one_or_none() is not None:
        return

    try:
        with open(shotlist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    scenes_data = data if isinstance(data, list) else data.get("scenes", [])

    for scene_data in scenes_data:
        scene_number = scene_data.get("scene_number", 0)
        if scene_number == 0:
            continue

        result = await db.execute(
            select(Scene).where(
                Scene.video_id == video.id,
                Scene.project_id == video.project_id,
                Scene.scene_number == scene_number,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            scene = Scene(
                video_id=video.id,
                project_id=video.project_id,
                scene_number=scene_number,
                timestamp_start=scene_data.get("timestamp_start", 0.0),
                timestamp_end=scene_data.get("timestamp_end", 0.0),
                script_text=scene_data.get("script_text"),
                visual_type=scene_data.get("visual_type", "image"),
                veo3_prompt=scene_data.get("veo3_prompt"),
                camera_movement=scene_data.get("camera_movement"),
                mood=scene_data.get("mood"),
                effect=scene_data.get("effect"),
                text_overlay=scene_data.get("text_overlay"),
                asset_path=scene_data.get("asset_path"),
                asset_version=scene_data.get("asset_version", 1),
                status=scene_data.get("status", "pending"),
            )
            db.add(scene)
        else:
            existing.timestamp_start = scene_data.get("timestamp_start", existing.timestamp_start)
            existing.timestamp_end = scene_data.get("timestamp_end", existing.timestamp_end)
            existing.script_text = scene_data.get("script_text", existing.script_text)
            existing.visual_type = scene_data.get("visual_type", existing.visual_type)
            existing.veo3_prompt = scene_data.get("veo3_prompt", existing.veo3_prompt)
            existing.camera_movement = scene_data.get("camera_movement", existing.camera_movement)
            existing.mood = scene_data.get("mood", existing.mood)
            existing.effect = scene_data.get("effect", existing.effect)
            existing.text_overlay = scene_data.get("text_overlay", existing.text_overlay)
            existing.asset_path = scene_data.get("asset_path", existing.asset_path)
            existing.asset_version = scene_data.get("asset_version", existing.asset_version)
            existing.status = scene_data.get("status", existing.status)
            existing.updated_at = datetime.now(timezone.utc)

    await db.commit()
