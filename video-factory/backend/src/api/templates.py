import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/templates", tags=["templates"])

TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", "/app/templates")


def _load_templates(category: str) -> list[dict]:
    """Load all template JSON files from a category directory."""
    cat_dir = Path(TEMPLATES_DIR) / category
    if not cat_dir.exists():
        return []
    templates = []
    for f in sorted(cat_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            templates.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return templates


@router.get("")
async def list_templates():
    """List all templates grouped by category."""
    image_styles = _load_templates("image_styles")
    edit_styles = _load_templates("edit_styles")
    storytelling_profiles = _load_templates("storytelling_profiles")
    return {
        "image_styles": image_styles,
        "edit_styles": edit_styles,
        "storytelling_profiles": storytelling_profiles,
    }


@router.get("/{category}/{template_id}")
async def get_template(category: str, template_id: str):
    """Get a single template by category and ID."""
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    category = CATEGORY_NORMALIZE.get(category, category)

    template_path = Path(TEMPLATES_DIR) / category / f"{template_id}.json"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    data = json.loads(template_path.read_text(encoding="utf-8"))
    return data


class ApplyBody(BaseModel):
    target_guide: str  # e.g. "project_style_guide", "video_visual_guide", "video_edit_guide"


# Map frontend target names to actual file names
TARGET_TO_FILE = {
    "project_style_guide": "style_guide",
    "project_content_guide": "content_guide",
    "project_storytelling_guide": "storytelling_guide",
    "video_visual_guide": "visual_guide",
    "video_edit_guide": "edit_guide",
    "video_content_brief": "content_brief",
    # Also accept direct file names
    "style_guide": "style_guide",
    "content_guide": "content_guide",
    "storytelling_guide": "storytelling_guide",
    "visual_guide": "visual_guide",
    "edit_guide": "edit_guide",
    "content_brief": "content_brief",
}


VALID_CATEGORIES = {
    "image_styles", "edit_styles", "storytelling_profiles",
    "image_style", "edit_style", "storytelling_profile",
}
CATEGORY_NORMALIZE = {
    "image_style": "image_styles",
    "edit_style": "edit_styles",
    "storytelling_profile": "storytelling_profiles",
}


@router.post("/{category}/{template_id}/apply/{project_id}")
async def apply_to_project(category: str, template_id: str, project_id: str, body: ApplyBody):
    """Apply a template to a project guide file."""
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    category = CATEGORY_NORMALIZE.get(category, category)

    file_name = TARGET_TO_FILE.get(body.target_guide)
    if not file_name:
        raise HTTPException(status_code=400, detail=f"Invalid target_guide: {body.target_guide}")

    template_path = Path(TEMPLATES_DIR) / category / f"{template_id}.json"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    data = json.loads(template_path.read_text(encoding="utf-8"))
    content = data.get("content", "")

    projects_dir = os.getenv("PROJECTS_DIR", "/app/projects")
    guide_path = Path(projects_dir) / project_id / f"{file_name}.md"
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.write_text(content, encoding="utf-8")

    return {"status": "applied", "project_id": project_id, "guide": file_name}


@router.post("/{category}/{template_id}/apply/{project_id}/{video_id}")
async def apply_to_video(category: str, template_id: str, project_id: str, video_id: str, body: ApplyBody):
    """Apply a template to a video guide file."""
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    category = CATEGORY_NORMALIZE.get(category, category)

    file_name = TARGET_TO_FILE.get(body.target_guide)
    if not file_name:
        raise HTTPException(status_code=400, detail=f"Invalid target_guide: {body.target_guide}")

    template_path = Path(TEMPLATES_DIR) / category / f"{template_id}.json"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    data = json.loads(template_path.read_text(encoding="utf-8"))
    content = data.get("content", "")

    projects_dir = os.getenv("PROJECTS_DIR", "/app/projects")
    guide_path = Path(projects_dir) / project_id / "videos" / video_id / f"{file_name}.md"
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.write_text(content, encoding="utf-8")

    return {"status": "applied", "project_id": project_id, "video_id": video_id, "guide": file_name}
