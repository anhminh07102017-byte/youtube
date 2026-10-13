import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/db.sqlite3")

# Convert sqlite:// to sqlite+aiosqlite://
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
else:
    ASYNC_DATABASE_URL = DATABASE_URL

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        from src.db.models import Project, Video, Character, Scene  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        # Auto-migrate: add missing columns to existing tables
        await conn.run_sync(_add_missing_columns)


def _add_missing_columns(conn):
    """Add columns that create_all won't add to existing tables."""
    import sqlalchemy as sa
    inspector = sa.inspect(conn)
    migrations = {
        "videos": {
            "target_duration": "INTEGER",
            "srt_path": "VARCHAR",
            "flow_project_id": "VARCHAR",
        },
        "scenes": {
            "content_tag": "VARCHAR",
            "edit_plan": "TEXT",
            "is_short": "BOOLEAN DEFAULT 0",
            "flow_characters": "TEXT",
        },
        "projects": {
            "flow_project_id": "VARCHAR",
            "base_style": "VARCHAR DEFAULT 'base_2d_style'",
        },
        "characters": {
            "reference_image_path": "VARCHAR",
            "flow_character_id": "VARCHAR",
            "video_id": "VARCHAR",
        },
    }
    for table, columns in migrations.items():
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        for col_name, col_type in columns.items():
            if col_name not in existing:
                conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))

