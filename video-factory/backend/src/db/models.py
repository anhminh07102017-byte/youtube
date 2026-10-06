from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, JSON
from src.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False, default="custom")  # vietnamese_history, world_history, custom
    era = Column(String, nullable=False, default="")
    time_period = Column(String, nullable=True)
    tone = Column(String, nullable=False, default="dramatic_narrative")
    target_duration = Column(Integer, nullable=False, default=600)
    sources = Column(JSON, nullable=False, default=list)
    notes = Column(Text, nullable=True)
    style_override = Column(String, nullable=True)
    flow_project_id = Column(String, nullable=True)  # Google Flow project ID
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "era": self.era,
            "time_period": self.time_period,
            "tone": self.tone,
            "target_duration": self.target_duration,
            "sources": self.sources or [],
            "notes": self.notes,
            "style_override": self.style_override,
            "flow_project_id": self.flow_project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft")
    # status values: draft, script_ready, audio_ready, shotlist_ready,
    #                assets_generating, assets_review, capcut_ready, done
    target_duration = Column(Integer, nullable=True)  # minutes
    srt_path = Column(String, nullable=True)
    script_path = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    shotlist_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "status": self.status,
            "target_duration": self.target_duration,
            "srt_path": self.srt_path,
            "script_path": self.script_path,
            "audio_path": self.audio_path,
            "shotlist_path": self.shotlist_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Character(Base):
    __tablename__ = "characters"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    historical_name = Column(String, nullable=True)
    era = Column(String, nullable=False, default="")
    age_range = Column(String, nullable=True)
    reference_description = Column(Text, nullable=True)
    visual_prompt_base = Column(Text, nullable=False, default="")
    visual_variants = Column(JSON, nullable=True)
    color_palette = Column(JSON, nullable=True)
    consistency_anchors = Column(JSON, nullable=True)
    reference_image_path = Column(String, nullable=True)  # local path to generated image
    flow_character_id = Column(String, nullable=True)  # character ID on Google Flow
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "historical_name": self.historical_name,
            "era": self.era,
            "age_range": self.age_range,
            "reference_description": self.reference_description,
            "visual_prompt_base": self.visual_prompt_base,
            "visual_variants": self.visual_variants or {},
            "color_palette": self.color_palette or {},
            "consistency_anchors": self.consistency_anchors or [],
            "reference_image_path": self.reference_image_path,
            "flow_character_id": self.flow_character_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String, nullable=False)
    scene_number = Column(Integer, nullable=False)
    timestamp_start = Column(Float, nullable=False, default=0.0)
    timestamp_end = Column(Float, nullable=False, default=0.0)
    script_text = Column(Text, nullable=True)
    visual_type = Column(String, nullable=False, default="image")  # image, video
    content_tag = Column(String, nullable=True)  # hành động, đối thoại, bối cảnh, cảm xúc, bản đồ, thuyết minh
    veo3_prompt = Column(Text, nullable=True)
    camera_movement = Column(String, nullable=True)
    mood = Column(String, nullable=True)
    effect = Column(String, nullable=True)  # ken_burns_zoom_in, etc.
    text_overlay = Column(String, nullable=True)
    asset_path = Column(String, nullable=True)
    asset_version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="pending")
    # status values: pending, generating, review, approved, redo
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "project_id": self.project_id,
            "scene_number": self.scene_number,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "script_text": self.script_text,
            "visual_type": self.visual_type,
            "content_tag": self.content_tag,
            "veo3_prompt": self.veo3_prompt,
            "camera_movement": self.camera_movement,
            "mood": self.mood,
            "effect": self.effect,
            "text_overlay": self.text_overlay,
            "asset_path": self.asset_path,
            "asset_version": self.asset_version,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
