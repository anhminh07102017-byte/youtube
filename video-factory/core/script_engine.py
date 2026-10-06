from pathlib import Path
from .config import BASE_DIR, SCRIPT_STRUCTURE


class ScriptEngine:
    def __init__(self, project_id: str, video_id: str):
        self.project_id = project_id
        self.video_id = video_id
        self.video_dir = BASE_DIR / project_id / "videos" / video_id
        self.script_path = self.video_dir / "script.md"

    def save_script(self, content: str):
        """Save script content to file"""
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.script_path.write_text(content)

    def load_script(self) -> str:
        """Load script content"""
        if self.script_path.exists():
            return self.script_path.read_text()
        return ""

    def get_template(self, title: str = "", era: str = "") -> str:
        """Get script template with structure"""
        return f"""# {title}

**Thời kỳ:** {era}
**Nguồn tham khảo:**
- [Ghi nguồn sử liệu tại đây]

---

## HOOK (30-45 giây)
<!-- Câu hỏi/tình huống gây tò mò, preview cao trào -->



## BỐI CẢNH (1.5-2 phút)
<!-- Thời đại, nhân vật chính, tình hình chính trị/xã hội -->



## DIỄN BIẾN (2-3 phút)
<!-- Nguyên nhân, chuỗi sự kiện, chi tiết quan trọng -->



## CAO TRÀO (2-3 phút)
<!-- Bước ngoặt, xung đột chính, kịch tính -->



## KẾT CỤC & BÀI HỌC (1.5-2 phút)
<!-- Hệ quả, bài học lịch sử, liên hệ -->



## OUTRO (15-30 giây)
<!-- CTA: like, subscribe, gợi ý video tiếp theo -->

"""

    def estimate_duration(self, content: str) -> dict:
        """Estimate video duration from script word count"""
        words = len(content.split())
        # Vietnamese speech rate: ~150-170 words/minute
        duration_minutes = words / 160
        duration_seconds = duration_minutes * 60
        return {
            "word_count": words,
            "estimated_duration_seconds": round(duration_seconds),
            "estimated_duration_minutes": round(duration_minutes, 1),
            "target_word_count": "1500-1800 từ cho video 10 phút"
        }
