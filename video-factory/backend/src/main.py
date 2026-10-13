import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.db.database import create_tables, async_session
from src.services.file_sync import scan_projects
from src.api import projects, videos, scenes, characters, guides, templates, settings, shorts


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure data directory exists, create tables, sync filesystem
    data_dir = Path("/app/data")
    data_dir.mkdir(parents=True, exist_ok=True)

    projects_dir = Path(os.getenv("PROJECTS_DIR", "/app/projects"))
    projects_dir.mkdir(parents=True, exist_ok=True)

    await create_tables()

    # Scan existing projects from filesystem into database
    async with async_session() as db:
        await scan_projects(db)

    yield

    # Shutdown: nothing to clean up


app = FastAPI(
    title="Minh Bi Youtube API",
    description="Backend cho hệ thống sản xuất video Minh Bi Youtube",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend at localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(projects.router)
app.include_router(videos.router)
app.include_router(scenes.router)
app.include_router(characters.router)
app.include_router(guides.router)
app.include_router(templates.router)
app.include_router(settings.router)
app.include_router(shorts.router)


# Serve project files (character images, assets, etc.)
projects_dir = Path(os.getenv("PROJECTS_DIR", "/app/projects"))
app.mount("/files/projects", StaticFiles(directory=str(projects_dir)), name="project_files")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "video-factory-backend"}
