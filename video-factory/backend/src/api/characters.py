import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.models import Character

router = APIRouter(prefix="/api/projects/{project_id}/characters", tags=["characters"])


class CharacterCreate(BaseModel):
    name: str
    historical_name: Optional[str] = None
    era: str = ""
    age_range: Optional[str] = None
    reference_description: Optional[str] = None
    visual_prompt_base: str = ""
    visual_variants: Optional[Dict] = None
    color_palette: Optional[Dict] = None
    consistency_anchors: Optional[List[str]] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    historical_name: Optional[str] = None
    era: Optional[str] = None
    age_range: Optional[str] = None
    reference_description: Optional[str] = None
    visual_prompt_base: Optional[str] = None
    visual_variants: Optional[Dict] = None
    color_palette: Optional[Dict] = None
    consistency_anchors: Optional[List[str]] = None
    reference_image_path: Optional[str] = None
    flow_character_id: Optional[str] = None


def _generate_id(name: str) -> str:
    slug = name.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    short_id = uuid.uuid4().hex[:6]
    return f"{slug}-{short_id}"


@router.get("")
async def list_characters(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all characters in a project."""
    result = await db.execute(
        select(Character)
        .where(Character.project_id == project_id)
        .order_by(Character.name)
    )
    characters = result.scalars().all()
    return [c.to_dict() for c in characters]


@router.post("", status_code=201)
async def create_character(
    project_id: str, body: CharacterCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new character."""
    character_id = _generate_id(body.name)

    character = Character(
        id=character_id,
        project_id=project_id,
        name=body.name,
        historical_name=body.historical_name,
        era=body.era,
        age_range=body.age_range,
        reference_description=body.reference_description,
        visual_prompt_base=body.visual_prompt_base,
        visual_variants=body.visual_variants,
        color_palette=body.color_palette,
        consistency_anchors=body.consistency_anchors,
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return character.to_dict()


@router.get("/{character_id}")
async def get_character(
    project_id: str, character_id: str, db: AsyncSession = Depends(get_db)
):
    """Get a single character."""
    result = await db.execute(
        select(Character).where(
            Character.id == character_id, Character.project_id == project_id
        )
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return character.to_dict()


@router.put("/{character_id}")
async def update_character(
    project_id: str,
    character_id: str,
    body: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a character."""
    result = await db.execute(
        select(Character).where(
            Character.id == character_id, Character.project_id == project_id
        )
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)
    character.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(character)
    return character.to_dict()


@router.delete("/{character_id}", status_code=204)
async def delete_character(
    project_id: str, character_id: str, db: AsyncSession = Depends(get_db)
):
    """Delete a character."""
    result = await db.execute(
        select(Character).where(
            Character.id == character_id, Character.project_id == project_id
        )
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    await db.delete(character)
    await db.commit()
