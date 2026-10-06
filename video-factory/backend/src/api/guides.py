import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/projects/{project_id}", tags=["guides"])

PROJECTS_DIR = os.getenv("PROJECTS_DIR", "/app/projects")

PROJECT_GUIDE_NAMES = {"style_guide", "content_guide"}
VIDEO_GUIDE_NAMES = {"content_brief", "visual_guide", "edit_guide", "brainstorm", "narration"}


class GuideBody(BaseModel):
    content: str


def _file_mtime_iso(path: Path) -> str:
    """Return the file's mtime as an ISO 8601 UTC string."""
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _validate_project_guide(guide_name: str) -> None:
    if guide_name not in PROJECT_GUIDE_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid guide name '{guide_name}'. Allowed: {sorted(PROJECT_GUIDE_NAMES)}",
        )


def _validate_video_guide(guide_name: str) -> None:
    if guide_name not in VIDEO_GUIDE_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid guide name '{guide_name}'. Allowed: {sorted(VIDEO_GUIDE_NAMES)}",
        )


# --- Project-level guides ---


@router.get("/guides/{guide_name}")
async def get_project_guide(project_id: str, guide_name: str):
    """Read a project-level guide markdown file."""
    _validate_project_guide(guide_name)

    guide_path = Path(PROJECTS_DIR) / project_id / f"{guide_name}.md"
    if not guide_path.exists():
        return {"content": "", "exists": False, "updated_at": None}

    content = guide_path.read_text(encoding="utf-8")
    return {"content": content, "exists": True, "updated_at": _file_mtime_iso(guide_path)}


@router.put("/guides/{guide_name}")
async def save_project_guide(project_id: str, guide_name: str, body: GuideBody):
    """Write a project-level guide markdown file."""
    _validate_project_guide(guide_name)

    guide_path = Path(PROJECTS_DIR) / project_id / f"{guide_name}.md"
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.write_text(body.content, encoding="utf-8")

    return {"content": body.content, "updated_at": _file_mtime_iso(guide_path)}


# --- Video-level guides ---


@router.get("/videos/{video_id}/guides/{guide_name}")
async def get_video_guide(project_id: str, video_id: str, guide_name: str):
    """Read a video-level guide markdown file."""
    _validate_video_guide(guide_name)

    guide_path = Path(PROJECTS_DIR) / project_id / "videos" / video_id / f"{guide_name}.md"
    if not guide_path.exists():
        return {"content": "", "exists": False, "updated_at": None}

    content = guide_path.read_text(encoding="utf-8")
    return {"content": content, "exists": True, "updated_at": _file_mtime_iso(guide_path)}


@router.put("/videos/{video_id}/guides/{guide_name}")
async def save_video_guide(project_id: str, video_id: str, guide_name: str, body: GuideBody):
    """Write a video-level guide markdown file."""
    _validate_video_guide(guide_name)

    guide_path = Path(PROJECTS_DIR) / project_id / "videos" / video_id / f"{guide_name}.md"
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.write_text(body.content, encoding="utf-8")

    return {"content": body.content, "updated_at": _file_mtime_iso(guide_path)}
