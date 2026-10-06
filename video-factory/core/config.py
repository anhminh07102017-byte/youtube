from pathlib import Path
import os

BASE_DIR = Path(os.getenv("PROJECTS_DIR", "./projects"))
CHARACTER_DB_DIR = Path(os.getenv("CHARACTER_DB_DIR", "./character_db"))
STYLE_GUIDES_DIR = Path(os.getenv("STYLE_GUIDES_DIR", "./style_guides"))

DEFAULT_TARGET_DURATION = 600  # 10 minutes in seconds
DEFAULT_SCRIPT_WORD_COUNT = (1500, 1800)
DEFAULT_SCENE_DURATION = (15, 30)  # seconds per scene
DEFAULT_SCENES_COUNT = (20, 30)

SCRIPT_STRUCTURE = {
    "hook": {"duration": (30, 45), "description": "Câu hỏi/tình huống gây tò mò"},
    "context": {"duration": (90, 120), "description": "Bối cảnh: thời đại, nhân vật, tình hình"},
    "development_1": {"duration": (120, 180), "description": "Diễn biến: nguyên nhân, chuỗi sự kiện"},
    "climax": {"duration": (120, 180), "description": "Cao trào: bước ngoặt, xung đột chính"},
    "conclusion": {"duration": (90, 120), "description": "Kết cục & bài học lịch sử"},
    "outro": {"duration": (15, 30), "description": "CTA: like, subscribe"},
}
