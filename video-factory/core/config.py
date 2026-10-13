from pathlib import Path
import json
import os

BASE_DIR = Path(os.getenv("PROJECTS_DIR", "./projects"))
CHARACTER_DB_DIR = Path(os.getenv("CHARACTER_DB_DIR", "./character_db"))
STYLE_GUIDES_DIR = Path(os.getenv("STYLE_GUIDES_DIR", "./style_guides"))
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", "./templates"))

DEFAULT_TARGET_DURATION = 600  # 10 minutes in seconds
DEFAULT_SCRIPT_WORD_COUNT = (1500, 1800)
DEFAULT_SCENE_DURATION = (15, 30)  # seconds per scene
DEFAULT_SCENES_COUNT = (20, 30)

# Default script structure — lịch sử kể chuyện
SCRIPT_STRUCTURES = {
    "history_storytelling": {
        "hook": {"duration": (30, 45), "description": "Câu hỏi/tình huống gây tò mò"},
        "context": {"duration": (90, 120), "description": "Bối cảnh: thời đại, nhân vật, tình hình"},
        "development_1": {"duration": (120, 180), "description": "Diễn biến: nguyên nhân, chuỗi sự kiện"},
        "climax": {"duration": (120, 180), "description": "Cao trào: bước ngoặt, xung đột chính"},
        "conclusion": {"duration": (90, 120), "description": "Kết cục & bài học lịch sử"},
        "outro": {"duration": (15, 30), "description": "CTA: like, subscribe"},
    },
    "explainer": {
        "hook": {"duration": (15, 30), "description": "Câu hỏi trực tiếp hoặc sự thật bất ngờ"},
        "problem": {"duration": (60, 120), "description": "Trình bày vấn đề/hiện tượng cần giải thích"},
        "explanation": {"duration": (180, 300), "description": "Giải thích: 2-4 luận điểm với bằng chứng"},
        "counterpoint": {"duration": (60, 120), "description": "Phản biện hoặc góc nhìn khác"},
        "conclusion": {"duration": (30, 60), "description": "Tóm tắt + mở rộng"},
        "outro": {"duration": (15, 30), "description": "CTA"},
    },
    "documentary": {
        "opening": {"duration": (60, 120), "description": "Establishing shot + giới thiệu chủ đề"},
        "context": {"duration": (120, 180), "description": "Bối cảnh lịch sử/địa lý/xã hội"},
        "main_story": {"duration": (180, 240), "description": "Narrative chính, timeline hoặc chủ đề"},
        "depth": {"duration": (120, 180), "description": "Phân tích chiều sâu, ý nghĩa rộng hơn"},
        "closing": {"duration": (60, 120), "description": "Reflection, suy ngẫm"},
    },
    "listicle": {
        "hook": {"duration": (15, 30), "description": "Tease item hay nhất"},
        "intro": {"duration": (15, 30), "description": "Context ngắn: tại sao list này thú vị"},
        "items": {"duration": (420, 480), "description": "Các items (mỗi item 45-90 giây)"},
        "conclusion": {"duration": (30, 45), "description": "Recap + CTA tương tác"},
        "outro": {"duration": (15, 30), "description": "CTA"},
    },
}

# Backward compatibility
SCRIPT_STRUCTURE = SCRIPT_STRUCTURES["history_storytelling"]


def get_script_structure(structure_type: str = "history_storytelling") -> dict:
    """Lấy script structure theo loại content."""
    return SCRIPT_STRUCTURES.get(structure_type, SCRIPT_STRUCTURE)
