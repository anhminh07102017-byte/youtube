import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Project

router = APIRouter(prefix="/api/projects", tags=["projects"])

PROJECTS_DIR = os.getenv("PROJECTS_DIR", "/app/projects")


class ProjectCreate(BaseModel):
    name: str
    type: str = "custom"
    era: str = ""
    time_period: Optional[str] = None
    tone: str = "dramatic_narrative"
    target_duration: int = 600
    sources: List[str] = []
    notes: Optional[str] = None
    style_override: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    era: Optional[str] = None
    time_period: Optional[str] = None
    tone: Optional[str] = None
    target_duration: Optional[int] = None
    sources: Optional[List[str]] = None
    notes: Optional[str] = None
    style_override: Optional[str] = None
    flow_project_id: Optional[str] = None


def _generate_id(name: str) -> str:
    """Generate a slug-style ID from the project name."""
    slug = name.lower().replace(" ", "-")
    # Remove non-alphanumeric characters except hyphens
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    # Append short UUID to ensure uniqueness
    short_id = uuid.uuid4().hex[:6]
    return f"{slug}-{short_id}"


def _write_project_json(project_id: str, data: dict):
    """Write project.json to the project folder."""
    project_dir = Path(PROJECTS_DIR) / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    with open(project_dir / "project.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@router.get("")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects. Also syncs from filesystem."""
    # Sync from filesystem first
    from src.services.file_sync import scan_projects
    await scan_projects(db)

    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return [p.to_dict() for p in projects]


@router.post("", status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new project with folder structure."""
    project_id = _generate_id(body.name)

    project = Project(
        id=project_id,
        name=body.name,
        type=body.type,
        era=body.era,
        time_period=body.time_period,
        tone=body.tone,
        target_duration=body.target_duration,
        sources=body.sources,
        notes=body.notes,
        style_override=body.style_override,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Create folder structure
    project_dir = Path(PROJECTS_DIR) / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "videos").mkdir(exist_ok=True)
    (project_dir / "characters").mkdir(exist_ok=True)

    # Write project.json
    _write_project_json(project_id, project.to_dict())

    return project.to_dict()


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single project by ID."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.to_dict()


@router.put("/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    """Update a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    project.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(project)

    # Update project.json
    _write_project_json(project_id, project.to_dict())

    return project.to_dict()


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project from the database. Does NOT delete files."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
