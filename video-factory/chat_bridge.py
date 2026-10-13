"""
Chat Bridge — Cầu nối giữa Web UI và Claude Code.
Chạy trên HOST (không phải Docker).

Sử dụng Claude Agent SDK (warm pool) thay vì spawn subprocess mỗi lần.
Latency: ~39s/tin (cũ) → ~1.5s/tin (SDK warm pool).

Chạy: source .venv/bin/activate && python chat_bridge.py
Hoặc: ./start_chat.sh
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("chat_bridge")

app = FastAPI(title="Minh Bi Youtube — Chat Bridge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", "./projects"))
LABS_DIR = Path(os.getenv("LABS_DIR", "./labs"))
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", "./templates"))
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")
SESSION_POOL_SIZE = int(os.getenv("SESSION_POOL_SIZE", "5"))

# Cancel flags cho batch jobs — key = "project::video", value = asyncio.Event (set = cancelled)
CANCEL_FLAGS: Dict[str, asyncio.Event] = {}

# ===== Monitor System =====
# Ring buffer lưu activity log, max 500 entries
from collections import deque
import uuid

ACTIVITY_LOG: deque = deque(maxlen=500)
# Active jobs tracker
ACTIVE_JOBS: Dict[str, dict] = {}
# SSE subscribers cho real-time stream
MONITOR_SUBSCRIBERS: Dict[str, asyncio.Queue] = {}


def _fix_flow_characters(ai_names: list, db_names: list) -> list:
    """Match tên nhân vật AI output (có thể rút gọn hoặc đặt lại) với tên chính xác trong DB.
    Dùng nhiều tín hiệu: từ khóa chung, số tuổi, tên riêng, substring.
    """
    import unicodedata

    def _normalize(s: str) -> str:
        s = unicodedata.normalize("NFC", s.lower().strip())
        return re.sub(r'[^\w\s]', ' ', s)

    def _extract_numbers(s: str) -> set:
        return set(re.findall(r'\d+', s))

    def _core_words(s: str) -> set:
        return set(w for w in _normalize(s).split() if len(w) > 1)

    if not ai_names or not db_names:
        return ai_names

    fixed = []
    for ai_name in ai_names:
        # Exact match
        if ai_name in db_names:
            fixed.append(ai_name)
            continue

        ai_norm = _normalize(ai_name)
        ai_words = _core_words(ai_name)
        ai_nums = _extract_numbers(ai_name)

        best_match = None
        best_score = -1

        for db_name in db_names:
            db_norm = _normalize(db_name)
            db_words = _core_words(db_name)
            db_nums = _extract_numbers(db_name)
            score = 0

            # 1. Substring match (AI name chứa trong DB name hoặc ngược lại)
            if ai_norm in db_norm or db_norm in ai_norm:
                score += 5

            # 2. Overlap từ (cả 2 chiều)
            if ai_words and db_words:
                overlap = ai_words & db_words
                score += len(overlap) * 2

            # 3. Số trùng (tuổi: 29, 16, 21, etc.)
            num_overlap = ai_nums & db_nums
            score += len(num_overlap) * 3  # Số tuổi rất quan trọng

            # 4. Từ đầu tiên trùng (tên chính, VD: "Bạn", "Bà")
            ai_first = ai_norm.split()[0] if ai_norm.split() else ""
            db_first = db_norm.split()[0] if db_norm.split() else ""
            if ai_first and db_first and ai_first == db_first:
                score += 3

            if score > best_score:
                best_score = score
                best_match = db_name

        # Cần ít nhất score 3 để match (tránh false positive)
        if best_match and best_score >= 3:
            fixed.append(best_match)
        else:
            fixed.append(ai_name)

    return fixed


def _emit_activity(
    category: str,
    action: str,
    detail: str = "",
    project_id: str = "",
    video_id: str = "",
    status: str = "info",
    job_id: str = "",
):
    """Ghi 1 activity entry và push tới tất cả subscribers."""
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": category,  # chat, prompt, character, shotlist, system
        "action": action,
        "detail": detail[:500],
        "project_id": project_id,
        "video_id": video_id,
        "status": status,  # info, success, error, working
        "job_id": job_id,
    }
    ACTIVITY_LOG.append(entry)
    # Push tới tất cả SSE subscribers
    for q in MONITOR_SUBSCRIBERS.values():
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            pass


def _start_job(category: str, action: str, project_id: str = "", video_id: str = "", total: int = 0) -> str:
    """Đăng ký 1 job đang chạy. Trả về job_id."""
    job_id = str(uuid.uuid4())[:8]
    ACTIVE_JOBS[job_id] = {
        "job_id": job_id,
        "category": category,
        "action": action,
        "project_id": project_id,
        "video_id": video_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "completed": 0,
        "status": "running",
    }
    _emit_activity(category, action, f"Bắt đầu job", project_id, video_id, "working", job_id)
    return job_id


def _update_job(job_id: str, completed: int = 0, status: str = "running", detail: str = "", total: int = 0):
    """Cập nhật tiến trình job."""
    if job_id in ACTIVE_JOBS:
        ACTIVE_JOBS[job_id]["completed"] = completed
        ACTIVE_JOBS[job_id]["status"] = status
        if total:
            ACTIVE_JOBS[job_id]["total"] = total
        if status in ("done", "error", "stopped"):
            ACTIVE_JOBS[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


def _finish_job(job_id: str, status: str = "done", detail: str = ""):
    """Đánh dấu job hoàn thành và xóa khỏi active."""
    if job_id in ACTIVE_JOBS:
        job = ACTIVE_JOBS[job_id]
        _emit_activity(job["category"], job["action"], detail or f"Hoàn thành", job["project_id"], job["video_id"], "success" if status == "done" else status, job_id)
        del ACTIVE_JOBS[job_id]


def _session_key(project_id: str, video_id: str) -> str:
    return f"{project_id}::{video_id}"


# ===== Background Job System =====
# Job chạy độc lập khỏi SSE connection — browser tắt, job vẫn chạy.

class BackgroundJob:
    """Background job — SSE chỉ subscribe theo dõi, không điều khiển."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.events: list = []
        self._done = False
        self._waiters: list = []
        self._created_at = time.time()

    def emit(self, event: dict):
        """Push event — tất cả subscribers nhận ngay."""
        self.events.append(event)
        for w in self._waiters:
            w.set()

    def finish(self):
        """Đánh dấu job hoàn tất."""
        self._done = True
        for w in self._waiters:
            w.set()

    @property
    def is_done(self) -> bool:
        return self._done

    async def subscribe(self, from_idx: int = 0):
        """Async generator — yields events. Hỗ trợ reconnect từ bất kỳ index."""
        idx = from_idx
        while True:
            while idx < len(self.events):
                yield self.events[idx]
                idx += 1
            if self._done:
                return
            waiter = asyncio.Event()
            self._waiters.append(waiter)
            try:
                await waiter.wait()
            finally:
                if waiter in self._waiters:
                    self._waiters.remove(waiter)


BACKGROUND_JOBS: Dict[str, BackgroundJob] = {}


async def _run_bg(bg_job: BackgroundJob, job_id: str, gen):
    """Chạy async generator như background task, push events vào BackgroundJob."""
    try:
        async for event in gen:
            bg_job.emit(event)
    except Exception as e:
        log.error(f"Background job {job_id} error: {e}")
        bg_job.emit({"type": "error", "message": f"Lỗi không mong đợi: {str(e)[:200]}"})
    finally:
        if job_id in ACTIVE_JOBS:
            _finish_job(job_id, "error", "Unexpected termination")
        bg_job.finish()


def _find_running_bg_job(action: str, project_id: str, video_id: str = "") -> Optional[str]:
    """Tìm background job đang chạy theo action + project + video."""
    for jid, job in ACTIVE_JOBS.items():
        if (job["action"] == action and job["project_id"] == project_id
                and job.get("video_id", "") == video_id and job["status"] == "running"
                and jid in BACKGROUND_JOBS):
            return jid
    return None


def _sse_from_bg_job(bg_job: BackgroundJob, from_idx: int = 0):
    """Tạo SSE StreamingResponse từ BackgroundJob (subscribe)."""
    async def _sse():
        async for event in bg_job.subscribe(from_idx):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    return StreamingResponse(_sse(), media_type="text/event-stream")


async def _cleanup_finished_bg_jobs():
    """Dọn BackgroundJob đã xong sau 5 phút."""
    while True:
        await asyncio.sleep(60)
        now = time.time()
        expired = [jid for jid, job in BACKGROUND_JOBS.items()
                   if job.is_done and now - job._created_at > 300]
        for jid in expired:
            BACKGROUND_JOBS.pop(jid, None)


# ===== SessionManager — Warm Pool Claude SDK =====

DISALLOWED_TOOLS = [
    "Write", "Edit", "Bash", "Read", "Glob", "Grep",
    "NotebookEdit", "WebFetch", "WebSearch",
]


class SessionManager:
    """Warm pool of ClaudeSDKClient — giảm latency từ ~39s xuống ~1.5s/query.

    Thay vì spawn `claude -p` subprocess mới mỗi lần (cold start ~39s),
    giữ sẵn pool process sống để query ngay (~1.5s).
    """

    def __init__(self, pool_size: int = 5):
        self._pool: asyncio.Queue[ClaudeSDKClient] = asyncio.Queue()
        self._pool_size = pool_size
        self._total_created = 0
        self._lock = asyncio.Lock()

    async def _create_client(self) -> ClaudeSDKClient:
        t0 = time.time()
        options = ClaudeAgentOptions(
            disallowed_tools=DISALLOWED_TOOLS,
            cwd=str(PROJECTS_DIR.parent),
            permission_mode="bypassPermissions",
            max_turns=100,
            include_partial_messages=True,
            setting_sources=["user"],
            max_buffer_size=10 * 1024 * 1024,  # 10MB
        )
        client = ClaudeSDKClient(options=options)
        await client.connect()
        log.info(f"🔥 SDK client created ({time.time() - t0:.1f}s)")
        return client

    async def _acquire(self) -> ClaudeSDKClient:
        """Lấy warm client từ pool, tạo mới nếu chưa đủ."""
        try:
            return self._pool.get_nowait()
        except asyncio.QueueEmpty:
            pass
        if self._total_created < self._pool_size:
            async with self._lock:
                if self._total_created < self._pool_size:
                    client = await self._create_client()
                    self._total_created += 1
                    log.info(f"📊 Pool: {self._total_created}/{self._pool_size} clients")
                    return client
        log.info("⏳ Pool full, waiting for available client...")
        return await self._pool.get()

    async def _release(self, client: ClaudeSDKClient):
        await self._pool.put(client)

    async def _replace_dead(self, dead: ClaudeSDKClient):
        """Thay client chết bằng client mới trong pool."""
        try:
            await dead.disconnect()
        except Exception:
            pass
        try:
            new = await self._create_client()
            await self._pool.put(new)
        except Exception as e:
            self._total_created -= 1
            log.error(f"❌ Failed to replace dead client: {e}")

    async def query(self, prompt: str, emit_context: Optional[dict] = None) -> str:
        """Blocking query — trả về full response text."""
        prompt_preview = prompt[:120].replace("\n", " ")
        log.info(f"🤖 SDK query: \"{prompt_preview}...\" ({len(prompt)} chars)")
        t0 = time.time()

        ctx = emit_context or {}
        cat = ctx.get("category", "system")
        pid, vid = ctx.get("project_id", ""), ctx.get("video_id", "")
        jid, label = ctx.get("job_id", ""), ctx.get("label", "")
        if emit_context:
            _emit_activity(cat, "working", f"{label} đang chờ Claude...", pid, vid, "working", jid)

        client = await self._acquire()
        try:
            sid = str(uuid.uuid4())[:12]
            await client.query(prompt, session_id=sid)
            full_text = ""
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    current = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
                    if current:
                        full_text = current
                    if emit_context:
                        for block in msg.content:
                            if isinstance(block, ThinkingBlock) and block.thinking:
                                preview = block.thinking[:300].replace("\n", " ").strip()
                                _emit_activity(cat, "thinking", f"{label}: {preview}{'...' if len(block.thinking) > 300 else ''}", pid, vid, "info", jid)

            elapsed = time.time() - t0
            result = full_text.strip() or "[Không có phản hồi]"
            log.info(f"✅ SDK done ({elapsed:.1f}s, {len(result)} chars)")
            if emit_context:
                status = "error" if result == "[Không có phản hồi]" else "success"
                _emit_activity(cat, "done", f"{label} xong ({elapsed:.0f}s, {len(result)} ký tự)", pid, vid, status, jid)
            await self._release(client)
            return result

        except Exception as e:
            log.error(f"❌ SDK query error: {e}")
            asyncio.create_task(self._replace_dead(client))
            return f"[Lỗi] {str(e)[:200]}"

    async def query_stream(self, prompt: str):
        """Streaming query — yields (type, data) tuples: delta, thinking, new_turn, error."""
        client = await self._acquire()
        healthy = True
        try:
            sid = str(uuid.uuid4())[:12]
            await client.query(prompt, session_id=sid)
            prev_text_len = 0
            prev_thinking_len = 0
            last_had_text = False
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    text = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
                    thinking = "".join(b.thinking for b in msg.content if isinstance(b, ThinkingBlock))
                    # Detect new turn (text reset after tool use)
                    if len(text) < prev_text_len and last_had_text:
                        yield ("new_turn", "")
                        prev_text_len = 0
                    if len(text) > prev_text_len:
                        yield ("delta", text[prev_text_len:])
                        prev_text_len = len(text)
                        last_had_text = True
                    if len(thinking) > prev_thinking_len:
                        yield ("thinking", thinking)
                        prev_thinking_len = len(thinking)
        except Exception as e:
            healthy = False
            log.error(f"❌ SDK stream error: {e}")
            yield ("error", str(e)[:200])
        finally:
            if healthy:
                await self._release(client)
            else:
                asyncio.create_task(self._replace_dead(client))

    async def warm_up(self, count: int = 2):
        """Pre-warm clients in background at startup."""
        for _ in range(min(count, self._pool_size)):
            try:
                if self._total_created < self._pool_size:
                    async with self._lock:
                        if self._total_created < self._pool_size:
                            client = await self._create_client()
                            self._total_created += 1
                            await self._pool.put(client)
                            log.info(f"🔥 Pre-warmed {self._total_created}/{self._pool_size}")
            except Exception as e:
                log.error(f"Pre-warm failed: {e}")

    @property
    def stats(self) -> dict:
        return {
            "pool_size": self._pool_size,
            "total_created": self._total_created,
            "available": self._pool.qsize(),
            "in_use": self._total_created - self._pool.qsize(),
        }

    async def shutdown(self):
        log.info("🛑 Shutting down SessionManager...")
        while not self._pool.empty():
            try:
                client = self._pool.get_nowait()
                await client.disconnect()
            except Exception:
                pass
        self._total_created = 0
        log.info("✅ SessionManager shut down")


session_manager = SessionManager(pool_size=max(SESSION_POOL_SIZE, 8))  # Chat pool: 8 clients
lab_session_manager = SessionManager(pool_size=5)  # Lab pool riêng: 5 clients


def _history_path(project_id: str, video_id: str) -> Path:
    return PROJECTS_DIR / project_id / "videos" / video_id / "chat_history.json"


def _load_history(project_id: str, video_id: str) -> List[dict]:
    path = _history_path(project_id, video_id)
    if path.exists():
        try:
            return json.loads(path.read_text("utf-8")).get("messages", [])
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_history(project_id: str, video_id: str, messages: List[dict]):
    path = _history_path(project_id, video_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"messages": messages}, ensure_ascii=False, indent=2), "utf-8")


def _short_dir(project_id: str, video_id: str) -> Path:
    """Path to shorts subfolder."""
    return PROJECTS_DIR / project_id / "videos" / video_id / "shorts"


def _load_full_context(project_id: str, video_id: str, parent_video_id: str = None) -> str:
    """Đọc TẤT CẢ thông tin có sẵn của dự án và video."""
    parts = []
    project_dir = PROJECTS_DIR / project_id
    video_dir = project_dir / "videos" / video_id

    # 1. Project metadata
    pj = project_dir / "project.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text("utf-8"))
            info = []
            if data.get("name"):
                info.append(f"Tên dự án: {data['name']}")
            if data.get("type"):
                info.append(f"Loại: {data['type']}")
            if data.get("era"):
                info.append(f"Thời kỳ: {data['era']}")
            if data.get("time_period"):
                info.append(f"Giai đoạn: {data['time_period']}")
            if data.get("sources"):
                sources = data["sources"]
                if isinstance(sources, list):
                    info.append(f"Nguồn tham khảo: {', '.join(str(s) for s in sources[:10])}")
            if data.get("notes"):
                info.append(f"Ghi chú: {data['notes'][:500]}")
            if info:
                parts.append("=== THÔNG TIN DỰ ÁN ===\n" + "\n".join(info))
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Project-level guides
    for name, label in [
        ("content_guide.md", "QUY ĐỊNH NỘI DUNG (DỰ ÁN)"),
        ("style_guide.md", "QUY ĐỊNH HÌNH ẢNH (DỰ ÁN)"),
        ("storytelling_guide.md", "CÁCH KỂ CHUYỆN (DỰ ÁN)"),
    ]:
        p = project_dir / name
        if p.exists():
            content = p.read_text("utf-8").strip()
            if content:
                parts.append(f"=== {label} ===\n{content[:3000]}")

    # 3. Video-level guides
    for name, label in [
        ("content_brief.md", "TÓM TẮT NỘI DUNG VIDEO"),
        ("visual_guide.md", "QUY ĐỊNH HÌNH ẢNH (VIDEO)"),
        ("edit_guide.md", "HƯỚNG DẪN EDIT (VIDEO)"),
    ]:
        p = video_dir / name
        if p.exists():
            content = p.read_text("utf-8").strip()
            if content:
                parts.append(f"=== {label} ===\n{content[:3000]}")

    # 4. Script (nếu có)
    script_path = video_dir / "script.md"
    if script_path.exists():
        content = script_path.read_text("utf-8").strip()
        if content:
            parts.append(f"=== KỊCH BẢN HIỆN TẠI ===\n{content[:4000]}")

    # 5. Characters
    char_dir = project_dir / "characters"
    if not char_dir.exists():
        char_dir = PROJECTS_DIR.parent / "character_db"
    if char_dir.exists():
        chars = []
        for f in sorted(char_dir.glob("*.json"))[:10]:
            try:
                c = json.loads(f.read_text("utf-8"))
                name = c.get("name", f.stem)
                desc = c.get("reference_description", c.get("description", ""))
                if desc:
                    chars.append(f"- {name}: {desc[:200]}")
            except (json.JSONDecodeError, OSError):
                pass
        if chars:
            parts.append("=== NHÂN VẬT ===\n" + "\n".join(chars))

    # 6. Brainstorm (nếu có)
    brainstorm = video_dir / "brainstorm.md"
    if brainstorm.exists():
        content = brainstorm.read_text("utf-8").strip()
        if content:
            parts.append(f"=== GHI CHÚ BRAINSTORM ===\n{content[:2000]}")

    # 7. Parent video context (cho shorts)
    if parent_video_id:
        parent_dir = project_dir / "videos" / parent_video_id
        parent_parts = []
        for name, label in [
            ("script.md", "KỊCH BẢN VIDEO GỐC"),
            ("narration.md", "NỘI DUNG THUYẾT MINH VIDEO GỐC"),
        ]:
            p = parent_dir / name
            if p.exists():
                content = p.read_text("utf-8").strip()
                if content:
                    parent_parts.append(f"=== {label} ===\n{content[:4000]}")
        if parent_parts:
            parts.append("=== NỘI DUNG VIDEO GỐC (để tham khảo khi lên short) ===\n" + "\n\n".join(parent_parts))

    return "\n\n".join(parts) if parts else ""


def _build_system_prompt(project_id: str, video_id: str) -> str:
    """Xây dựng system prompt với đầy đủ context dự án."""
    ctx = _load_full_context(project_id, video_id)

    return f"""Bạn đang giúp sản xuất video cho kênh YouTube lịch sử. Project: {project_id}, Video: {video_id}.

QUY TẮC VỀ TOOLS — ĐỌC KỸ:
Bạn CÓ Playwright MCP tools đã được cài sẵn và cấp quyền. Danh sách tools bạn CÓ THỂ dùng:
- mcp__plugin_playwright_playwright__browser_navigate — mở URL
- mcp__plugin_playwright_playwright__browser_snapshot — chụp DOM
- mcp__plugin_playwright_playwright__browser_click — click element
- mcp__plugin_playwright_playwright__browser_take_screenshot — chụp ảnh màn hình
- mcp__plugin_playwright_playwright__browser_type — gõ text
- mcp__plugin_playwright_playwright__browser_press_key — nhấn phím
- mcp__plugin_playwright_playwright__browser_find — tìm element
Khi user gửi link YouTube hoặc yêu cầu mở browser: HÃY DÙNG các tool trên ngay, KHÔNG từ chối.
Quyền đã bypass — không cần hỏi permission.

Tool BỊ CẤM (KHÔNG dùng): Write, Edit, Bash, Read, Glob, Grep, NotebookEdit, WebFetch, WebSearch.
Khi user nói "Chốt", trả về nội dung kịch bản trong message, hệ thống tự lưu file.

Vai trò của bạn:
- Lên kịch bản: brainstorm ý tưởng, viết kịch bản, chốt nội dung
- Tạo shot list: phân cảnh, mô tả hình ảnh cho từng cảnh
- Hỗ trợ generate hình ảnh/video qua Veo 3
- Hỗ trợ build project CapCut
- Trả lời bằng tiếng Việt
- Prompt Veo 3 phải bằng tiếng Anh, NHƯNG giữ nguyên tiếng Việt cho:
  + Tên nhân vật (VD: "Trần Hưng Đạo", "Hai Bà Trưng")
  + Tiêu đề, text overlay hiển thị trong ảnh/video (VD: "Đại Việt", "Bạch Đằng")
  + Địa danh, tên triều đại (VD: "Thăng Long", "nhà Trần")
  Ví dụ đúng: "2D animated style, ancient Vietnamese general named Trần Hưng Đạo standing on warship, text overlay showing 'Bạch Đằng 1288'"
  Ví dụ sai: "general named Tran Hung Dao" (mất dấu tiếng Việt)
- Nội dung phải dựa trên sử liệu uy tín, KHÔNG bịa đặt
- Tham chiếu các quy định nội dung, hình ảnh, edit đã có sẵn bên dưới

{f"--- CONTEXT DỰ ÁN ---{chr(10)}{ctx}" if ctx else "(Chưa có thông tin dự án)"}

QUY TẮC VỀ KỊCH BẢN VÀ NỘI DUNG:
Có 2 loại output khác nhau:

1. **KỊCH BẢN** (tag [KB:xx]) — Tài liệu sản xuất đầy đủ:
   - Bối cảnh lịch sử, phân tích
   - Nguồn sử liệu tham khảo (Đại Việt Sử Ký Toàn Thư, v.v.)
   - Bố cục từng phần (Hook, Bối cảnh, Diễn biến, Cao trào, Kết, Outro)
   - Ghi chú sản xuất, hướng dẫn hình ảnh
   Ví dụ:
   [KB:01]
   # Trận Bạch Đằng 1288
   ## Nguồn sử liệu
   - Đại Việt Sử Ký Toàn Thư, Quyển 6...
   ## Hook (0:00-0:30)
   [Bối cảnh: Quân Nguyên Mông 3 lần xâm lược...]
   Nội dung đọc: "Năm 1288, khi 30 vạn quân Nguyên Mông..."
   ## Bối cảnh (0:30-2:30)
   ...
   [/KB:01]

2. **NỘI DUNG** (tag [ND:xx]) — Chỉ phần voice/đọc, text sạch:
   - CHỈ có lời thoại sẽ ghi âm
   - KHÔNG có ghi chú, nguồn, bối cảnh, hướng dẫn sản xuất
   - Đây là script để đọc thành voice
   Ví dụ:
   [ND:01]
   Năm 1288, khi 30 vạn quân Nguyên Mông lần thứ ba tràn vào Đại Việt, một vị tướng già đã đặt cược tất cả vào một con sông...

   Để hiểu được thiên tài quân sự của Trần Hưng Đạo, ta phải quay lại...
   [/ND:01]

Quy tắc:
- Mã tăng dần: KB:01, KB:02... và ND:01, ND:02...
- Khi viết kịch bản xong, LUÔN viết nội dung voice kèm theo (hoặc user yêu cầu riêng).
- User bấm "Chốt" → hệ thống tự lưu file. KHÔNG cần bạn ghi file."""


async def _call_claude_async(
    prompt: str,
    timeout: int = 0,
    model: str = "",
    emit_context: Optional[dict] = None,
) -> str:
    """Query Claude via warm SDK pool. Drop-in replacement for old subprocess version."""
    return await session_manager.query(prompt, emit_context=emit_context)


def _build_chat_prompt(project_id: str, video_id: str, messages: List[dict], new_message: str) -> str:
    """Xây prompt cho chat (dùng chung cho cả stream và non-stream)."""
    system = _build_system_prompt(project_id, video_id)
    if len(messages) <= 1:
        return f"{system}\n\nUser: {new_message}"
    recent = messages[-10:]
    history = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:3000]}"
        for m in recent[:-1]
    )
    return f"{system}\n\nLịch sử chat:\n{history}\n\nUser: {new_message}"


class ChatRequest(BaseModel):
    message: str


@app.get("/api/chat/{project_id}/{video_id}")
async def get_history(project_id: str, video_id: str):
    """Lấy lịch sử chat."""
    messages = _load_history(project_id, video_id)
    return {"messages": messages}


@app.post("/api/chat/{project_id}/{video_id}")
async def send_message(project_id: str, video_id: str, body: ChatRequest):
    """Gửi tin nhắn, nhận phản hồi từ Claude (non-streaming fallback)."""
    messages = _load_history(project_id, video_id)

    _emit_activity("chat", "send_message", body.message[:100], project_id, video_id, "working")

    now = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": body.message, "timestamp": now}
    messages.append(user_msg)

    prompt = _build_chat_prompt(project_id, video_id, messages, body.message)
    response = await session_manager.query(prompt)

    assistant_msg = {
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    messages.append(assistant_msg)
    _save_history(project_id, video_id, messages)

    _emit_activity("chat", "response", f"Phản hồi {len(response)} ký tự", project_id, video_id, "success")

    return assistant_msg


@app.post("/api/chat/{project_id}/{video_id}/stream")
async def stream_message(project_id: str, video_id: str, body: ChatRequest):
    """Gửi tin nhắn, stream phản hồi từ Claude qua SSE (SDK warm pool)."""
    messages = _load_history(project_id, video_id)

    now = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": body.message, "timestamp": now}
    messages.append(user_msg)
    _save_history(project_id, video_id, messages)

    prompt = _build_chat_prompt(project_id, video_id, messages, body.message)
    _emit_activity("chat", "stream_start", body.message[:100], project_id, video_id, "working")

    async def event_stream():
        full_text = ""
        try:
            async for msg_type, data in session_manager.query_stream(prompt):
                if msg_type == "delta":
                    full_text += data
                    yield f"data: {json.dumps({'type': 'delta', 'text': data}, ensure_ascii=False)}\n\n"
                elif msg_type == "thinking":
                    preview = data[:300].replace("\n", " ").strip()
                    _emit_activity("chat", "thinking", f"{preview}{'...' if len(data) > 300 else ''}", project_id, video_id, "info")
                elif msg_type == "error":
                    full_text = full_text or f"[Lỗi] {data}"
                    yield f"data: {json.dumps({'type': 'error', 'text': data[:200]}, ensure_ascii=False)}\n\n"
        except Exception as e:
            full_text = full_text or f"[Lỗi] {str(e)[:200]}"
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)[:200]}, ensure_ascii=False)}\n\n"

        # Lưu message hoàn chỉnh
        assistant_msg = {
            "role": "assistant",
            "content": full_text or "[Không có phản hồi]",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        msgs = _load_history(project_id, video_id)
        msgs.append(assistant_msg)
        _save_history(project_id, video_id, msgs)

        _emit_activity("chat", "stream_done", f"Phản hồi {len(full_text)} ký tự", project_id, video_id, "success")
        yield f"data: {json.dumps({'type': 'done', 'text': full_text}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/api/chat/{project_id}/{video_id}")
async def clear_history(project_id: str, video_id: str):
    """Xóa lịch sử chat."""
    path = _history_path(project_id, video_id)
    if path.exists():
        path.unlink()
    return {"status": "cleared"}


import re as _re


def _extract_tagged_content(text: str, tag: str, code: Optional[str] = None) -> Optional[str]:
    """Trích nội dung từ message theo mã [TAG:xx]...[/TAG:xx].
    tag = "KB" hoặc "ND". Nếu code=None, lấy bản mới nhất."""
    if code:
        pattern = rf'\[{tag}:{_re.escape(code)}\]\s*([\s\S]*?)\s*\[/{tag}:{_re.escape(code)}\]'
        match = _re.search(pattern, text)
        return match.group(1).strip() if match else None
    else:
        pattern = rf'\[{tag}:\d+\]\s*([\s\S]*?)\s*\[/{tag}:\d+\]'
        matches = _re.findall(pattern, text)
        return matches[-1].strip() if matches else None


def _find_tagged_message(messages: List[dict], tag: str, code: Optional[str] = None) -> Optional[Tuple[dict, str]]:
    """Tìm message chứa mã tag. Trả về (message, extracted_content)."""
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        extracted = _extract_tagged_content(content, tag, code)
        if extracted:
            return msg, extracted
    return None


def _save_draft(project_id: str, video_id: str, messages: List[dict], tag: str, code: Optional[str], filename: str) -> Optional[str]:
    """Tìm và lưu nội dung theo tag. Trả về source hoặc None."""
    video_dir = PROJECTS_DIR / project_id / "videos" / video_id
    video_dir.mkdir(parents=True, exist_ok=True)

    result = _find_tagged_message(messages, tag, code)
    if result:
        _, content = result
        (video_dir / filename).write_text(content, "utf-8")
        return "tag"

    # Fallback cho KB: lấy assistant message dài nhất
    if tag == "KB":
        for msg in reversed(messages):
            if msg.get("role") == "assistant" and len(msg.get("content", "")) > 200:
                (video_dir / filename).write_text(msg["content"], "utf-8")
                return "last_message"
    return None


class FinalizeRequest(BaseModel):
    kb_code: Optional[str] = None  # VD: "01", "02". None = lấy bản mới nhất
    nd_code: Optional[str] = None


@app.post("/api/chat/{project_id}/{video_id}/finalize")
async def finalize(project_id: str, video_id: str, body: Optional[FinalizeRequest] = None):
    """Chốt kịch bản + nội dung — tìm trong chat history và lưu file. Không gọi Claude."""
    messages = _load_history(project_id, video_id)
    if not messages:
        raise HTTPException(400, "Chưa có nội dung chat để chốt")

    kb_code = body.kb_code if body else None
    nd_code = body.nd_code if body else None

    saved = {}

    # Lưu kịch bản (KB)
    kb_src = _save_draft(project_id, video_id, messages, "KB", kb_code, "script.md")
    if kb_src:
        saved["script"] = kb_src

    # Lưu nội dung voice (ND)
    nd_src = _save_draft(project_id, video_id, messages, "ND", nd_code, "narration.md")
    if nd_src:
        saved["narration"] = nd_src

    if not saved:
        raise HTTPException(400, "Không tìm thấy kịch bản hoặc nội dung trong chat.")

    _emit_activity("chat", "finalize", f"Chốt: {', '.join(saved.keys())}", project_id, video_id, "success")
    return {"status": "finalized", "saved": saved}


@app.get("/api/chat/{project_id}/{video_id}/drafts")
async def list_drafts(project_id: str, video_id: str):
    """Liệt kê các bản KB và ND có trong chat history."""
    messages = _load_history(project_id, video_id)
    drafts = []  # type: List[dict]
    for i, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        for tag, label in [("KB", "Kịch bản"), ("ND", "Nội dung")]:
            codes = _re.findall(rf'\[{tag}:(\d+)\]', content)
            for code in codes:
                extracted = _extract_tagged_content(content, tag, code)
                if extracted:
                    preview = extracted[:80].replace("\n", " ").strip()
                    drafts.append({
                        "tag": tag,
                        "code": code,
                        "label": label,
                        "preview": preview + ("..." if len(extracted) > 80 else ""),
                        "length": len(extracted),
                        "message_index": i,
                    })
    return {"drafts": drafts}


# ===== Short Chat Endpoints =====

def _short_history_path(project_id: str, video_id: str) -> Path:
    return _short_dir(project_id, video_id) / "chat_history.json"


def _load_short_history(project_id: str, video_id: str) -> List[dict]:
    path = _short_history_path(project_id, video_id)
    if path.exists():
        try:
            return json.loads(path.read_text("utf-8")).get("messages", [])
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_short_history(project_id: str, video_id: str, messages: List[dict]):
    path = _short_history_path(project_id, video_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"messages": messages}, ensure_ascii=False, indent=2), "utf-8")


def _build_short_system_prompt(project_id: str, video_id: str) -> str:
    """System prompt cho short — load context video gốc."""
    # Load full context của video gốc (kịch bản, nội dung, guides, characters)
    ctx = _load_full_context(project_id, video_id)

    # Load short brainstorm nếu có
    short_brainstorm = ""
    bp = _short_dir(project_id, video_id) / "brainstorm.md"
    if bp.exists():
        short_brainstorm = bp.read_text("utf-8").strip()[:2000]

    # Load short script nếu có
    short_script = ""
    sp = _short_dir(project_id, video_id) / "script.md"
    if sp.exists():
        short_script = sp.read_text("utf-8").strip()[:3000]

    return f"""Bạn đang giúp sản xuất **YouTube Short** (45-50 giây, format dọc 9:16) cho kênh YouTube lịch sử.
Project: {project_id}, Video gốc: {video_id}.

ĐỊNH DẠNG SHORT:
- Thời lượng: 45-50 giây (~110-130 từ tiếng Việt)
- Format: Vertical 9:16 (1080x1920)
- Dựa trên nội dung video gốc (kịch bản và thông tin bên dưới) để lên ý tưởng short
- Short phải là nội dung standalone, thu hút viewer xem full video
- Hook phải nằm trong 1-2 giây đầu tiên
- Nhịp nhanh xuyên suốt, không có đoạn chậm
- Một short chỉ một ý, đừng nhồi nhiều sự kiện

QUAN TRỌNG — QUY TẮC BẮT BUỘC:
- Bạn KHÔNG được ghi file, tạo file, hay dùng bất kỳ tool nào (Write, Edit, Bash, Read...).
- Bạn CHỈ trả lời bằng text thuần. Hệ thống sẽ tự xử lý việc lưu file.
- Khi user nói "Chốt", hãy trả về nội dung kịch bản short trực tiếp trong message.

Vai trò của bạn:
- Lên ý tưởng short dựa trên nội dung video gốc
- Viết kịch bản short (hook, nội dung, kết)
- Trả lời bằng tiếng Việt
- Nội dung phải dựa trên sử liệu uy tín, KHÔNG bịa đặt

QUY TẮC VỀ KỊCH BẢN VÀ NỘI DUNG:
1. **KỊCH BẢN SHORT** (tag [KB:xx]) — Gồm hook, nội dung chính, kết
2. **NỘI DUNG SHORT** (tag [ND:xx]) — Chỉ phần voice 45-50 giây

--- CONTEXT VIDEO GỐC (tham khảo để lên short) ---
{ctx}

{f"--- KỊCH BẢN SHORT HIỆN TẠI ---{chr(10)}{short_script}" if short_script else ""}
{f"--- GHI CHÚ BRAINSTORM SHORT ---{chr(10)}{short_brainstorm}" if short_brainstorm else ""}"""


def _build_short_chat_prompt(project_id: str, video_id: str, messages: List[dict], new_message: str) -> str:
    system = _build_short_system_prompt(project_id, video_id)
    if len(messages) <= 1:
        return f"{system}\n\nUser: {new_message}"
    recent = messages[-10:]
    history = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:3000]}"
        for m in recent[:-1]
    )
    return f"{system}\n\nLịch sử chat:\n{history}\n\nUser: {new_message}"


@app.get("/api/chat/{project_id}/{video_id}/short")
async def get_short_history(project_id: str, video_id: str):
    """Lấy lịch sử chat short."""
    messages = _load_short_history(project_id, video_id)
    return {"messages": messages}


@app.post("/api/chat/{project_id}/{video_id}/short/stream")
async def stream_short_message(project_id: str, video_id: str, body: ChatRequest):
    """Stream phản hồi Claude cho short brainstorm."""
    messages = _load_short_history(project_id, video_id)

    now = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": body.message, "timestamp": now}
    messages.append(user_msg)
    _save_short_history(project_id, video_id, messages)

    prompt = _build_short_chat_prompt(project_id, video_id, messages, body.message)
    _emit_activity("chat", "short_stream", body.message[:100], project_id, video_id, "working")

    async def event_stream():
        full_text = ""
        try:
            async for msg_type, data in session_manager.query_stream(prompt):
                if msg_type == "delta":
                    full_text += data
                    yield f"data: {json.dumps({'type': 'delta', 'text': data}, ensure_ascii=False)}\n\n"
                elif msg_type == "thinking":
                    preview = data[:300].replace("\n", " ").strip()
                    _emit_activity("chat", "short_thinking", f"{preview}{'...' if len(data) > 300 else ''}", project_id, video_id, "info")
                elif msg_type == "error":
                    full_text = full_text or f"[Lỗi] {data}"
                    yield f"data: {json.dumps({'type': 'error', 'text': data[:200]}, ensure_ascii=False)}\n\n"
        except Exception as e:
            full_text = full_text or f"[Lỗi] {str(e)[:200]}"
            log.error(f"Short stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)[:200]}, ensure_ascii=False)}\n\n"

        assistant_msg = {
            "role": "assistant",
            "content": full_text or "[Không có phản hồi]",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        msgs = _load_short_history(project_id, video_id)
        msgs.append(assistant_msg)
        _save_short_history(project_id, video_id, msgs)

        _emit_activity("chat", "short_response", f"Short: {len(full_text)} ký tự", project_id, video_id, "success")
        yield f"data: {json.dumps({'type': 'done', 'text': full_text}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.delete("/api/chat/{project_id}/{video_id}/short")
async def clear_short_history(project_id: str, video_id: str):
    """Xóa lịch sử chat short."""
    path = _short_history_path(project_id, video_id)
    if path.exists():
        path.unlink()
    return {"status": "ok"}


@app.post("/api/chat/{project_id}/{video_id}/short/finalize")
async def finalize_short(project_id: str, video_id: str):
    """Trích xuất KB/ND từ chat short và lưu vào shorts/ folder."""
    messages = _load_short_history(project_id, video_id)
    sdir = _short_dir(project_id, video_id)
    sdir.mkdir(parents=True, exist_ok=True)

    saved = []
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        # Tìm [KB:xx]...[/KB:xx]
        kb_match = re.search(r'\[KB:\d+\](.*?)\[/KB:\d+\]', content, re.DOTALL)
        if kb_match and "script" not in [s.get("type") for s in saved]:
            (sdir / "script.md").write_text(kb_match.group(1).strip(), "utf-8")
            saved.append({"type": "script", "tag": "KB"})
        # Tìm [ND:xx]...[/ND:xx]
        nd_match = re.search(r'\[ND:\d+\](.*?)\[/ND:\d+\]', content, re.DOTALL)
        if nd_match and "narration" not in [s.get("type") for s in saved]:
            (sdir / "narration.md").write_text(nd_match.group(1).strip(), "utf-8")
            saved.append({"type": "narration", "tag": "ND"})
        if len(saved) >= 2:
            break

    if not saved:
        return {"status": "empty", "message": "Không tìm thấy [KB] hoặc [ND] trong chat."}

    return {"status": "ok", "saved": saved}


def _parse_srt(srt_text: str) -> list[dict]:
    """Parse SRT text → list of {index, start, end, text} entries."""
    import re as _re
    entries = []
    blocks = _re.split(r'\n\s*\n', srt_text.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        # Parse timestamp line: 00:01:23,456 --> 00:01:26,789
        ts_match = _re.match(
            r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})',
            lines[1].strip(),
        )
        if not ts_match:
            continue
        g = [int(x) for x in ts_match.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = ' '.join(l.strip() for l in lines[2:] if l.strip())
        entries.append({"start": start, "end": end, "text": text})
    return entries


def _parse_pacing_rules(edit_guide: str) -> list[dict]:
    """Parse edit_guide.md → list of {start, end, min_dur, max_dur} pacing rules.

    Tìm pattern như: **Hook (0:00 - 0:45)**: ... 2-4 giây/cảnh
    hoặc: **Bối cảnh (0:45 - 2:30)**: ... 5-8 giây/cảnh
    """
    import re as _re
    rules = []
    # Match: (M:SS - M:SS) ... N-N giây  hoặc  N giây
    pattern = _re.compile(
        r'\((\d+):(\d{2})\s*-\s*(\d+):(\d{2})\)[^)]*?(\d+)\s*-\s*(\d+)\s*giây',
        _re.IGNORECASE,
    )
    for m in pattern.finditer(edit_guide):
        start = int(m.group(1)) * 60 + int(m.group(2))
        end = int(m.group(3)) * 60 + int(m.group(4))
        min_dur = int(m.group(5))
        max_dur = int(m.group(6))
        rules.append({"start": start, "end": end, "min_dur": min_dur, "max_dur": max_dur})
    # Sắp xếp theo thời gian bắt đầu
    rules.sort(key=lambda r: r["start"])
    return rules


def _get_target_duration(timestamp: float, pacing_rules: list[dict]) -> float:
    """Trả về target duration cho 1 thời điểm, dựa trên pacing rules.

    Lấy trung bình min_dur và max_dur. Fallback = 6s nếu không match rule nào.
    """
    for rule in pacing_rules:
        if rule["start"] <= timestamp < rule["end"]:
            return (rule["min_dur"] + rule["max_dur"]) / 2
    return 6.0  # fallback hợp lý


def _classify_scene(text: str) -> tuple:
    """Phân loại scene dựa trên nội dung text → (visual_type, content_tag).

    Returns:
        visual_type: "video" nếu có hành động/chuyển động, "image" nếu tĩnh
        content_tag: nhãn nội dung để hiển thị trên UI
    """
    t = text.lower()

    # --- Từ khóa hành động → video ---
    action_keywords = [
        "tấn công", "tiến công", "xông vào", "lao vào", "đánh", "chiến đấu",
        "chạy", "chạy trốn", "rút lui", "rút quân", "truy đuổi",
        "hành quân", "tiến quân", "kéo quân", "xuất quân", "dẫn quân",
        "nổ", "bắn", "phá", "đốt", "cháy", "sụp đổ", "đổ sập",
        "vượt sông", "vượt biển", "dong buồm", "ra khơi", "lên đường",
        "giao tranh", "đụng độ", "giáp mặt", "bao vây",
        "di chuyển", "đi", "đến", "rời", "quay về",
        "dâng", "tràn", "lan rộng", "bùng nổ",
    ]
    # --- Từ khóa đối thoại/tuyên bố ---
    dialog_keywords = [
        "nói", "tuyên bố", "ra lệnh", "hạ lệnh", "ban chiếu",
        "hô hào", "kêu gọi", "thề", "hứa", "đáp",
        "hỏi", "trả lời", "bàn bạc", "họp", "hội nghị",
    ]
    # --- Từ khóa miêu tả/bối cảnh → image ---
    desc_keywords = [
        "là", "được", "có", "nằm", "thuộc", "gồm",
        "thời kỳ", "triều đại", "năm", "thế kỷ",
        "dân số", "diện tích", "kinh đô", "thủ đô",
    ]
    # --- Từ khóa cảm xúc/suy ngẫm ---
    emotion_keywords = [
        "đau", "buồn", "vui", "tự hào", "xúc động",
        "hy sinh", "mất mát", "bi thương", "vinh quang",
        "bài học", "di sản", "nhớ", "tưởng nhớ",
    ]
    # --- Từ khóa bản đồ/sơ đồ ---
    map_keywords = [
        "bản đồ", "lãnh thổ", "biên giới", "vùng", "miền",
        "phía bắc", "phía nam", "phía đông", "phía tây",
    ]

    has_action = any(kw in t for kw in action_keywords)
    has_dialog = any(kw in t for kw in dialog_keywords)
    has_desc = any(kw in t for kw in desc_keywords)
    has_emotion = any(kw in t for kw in emotion_keywords)
    has_map = any(kw in t for kw in map_keywords)

    # Xác định visual_type
    if has_action:
        visual_type = "video"
    else:
        visual_type = "image"

    # Xác định content_tag (ưu tiên theo thứ tự)
    if has_action:
        content_tag = "hành động"
    elif has_dialog:
        content_tag = "đối thoại"
    elif has_map:
        content_tag = "bản đồ"
    elif has_emotion:
        content_tag = "cảm xúc"
    elif has_desc:
        content_tag = "bối cảnh"
    else:
        content_tag = "thuyết minh"

    return visual_type, content_tag


def _group_srt_to_scenes(entries: list, pacing_rules=None) -> list:
    """Group SRT entries into scenes based on pacing rules from edit guide."""
    if not entries:
        return []

    scenes = []
    scene_num = 1
    group_start = entries[0]["start"]
    group_texts = []

    for i, entry in enumerate(entries):
        group_texts.append(entry["text"])
        group_end = entry["end"]
        duration = group_end - group_start

        # Lấy target duration dựa trên vị trí trong video
        if pacing_rules:
            target = _get_target_duration(group_start, pacing_rules)
        else:
            target = 6.0

        # Tạo scene mới khi: đủ dài HOẶC là entry cuối
        is_last = (i == len(entries) - 1)
        # Kiểm tra khoảng trống lớn với entry tiếp (>1.5s = có thể chuyển ý)
        has_gap = (not is_last and entries[i + 1]["start"] - group_end > 1.5)

        if duration >= target or is_last or has_gap:
            script_text = ' '.join(group_texts)
            scenes.append({
                "scene_number": scene_num,
                "timestamp_start": round(group_start, 2),
                "timestamp_end": round(group_end, 2),
                "script_text": script_text,
            })
            scene_num += 1
            group_texts = []
            if not is_last:
                group_start = entries[i + 1]["start"]

    return scenes


@app.post("/api/generate-shotlist/{project_id}/{video_id}")
async def generate_shotlist(project_id: str, video_id: str, is_short: bool = False):
    """Dùng Claude phân tích kịch bản + SRT để chia phân đoạn thông minh."""
    _emit_activity("shotlist", "generate", "Đang phân tích nội dung để chia phân đoạn...", project_id, video_id, "working")
    video_dir = PROJECTS_DIR / project_id / "videos" / video_id
    data_dir = video_dir / "shorts" if is_short else video_dir

    # Đọc SRT
    srt_path = data_dir / "audio" / "subtitles.srt"
    if not srt_path.exists():
        _emit_activity("shotlist", "generate", "Lỗi: chưa có SRT", project_id, video_id, "error")
        raise HTTPException(400, "Chưa có file SRT. Hãy upload trước.")
    srt_content = srt_path.read_text("utf-8")

    # Parse SRT
    entries = _parse_srt(srt_content)
    if not entries:
        return {"status": "error", "message": "Không parse được nội dung SRT. Kiểm tra lại file."}

    # Đọc nội dung voice (narration) — bản text đúng chính tả, đầy đủ dấu câu
    narration_content = ""
    narration_path = data_dir / "narration.md"
    if narration_path.exists():
        narration_content = narration_path.read_text("utf-8")

    # Đọc kịch bản (nếu có) để Claude hiểu cấu trúc nội dung
    script_content = ""
    script_path = data_dir / "script.md"
    if script_path.exists():
        script_content = script_path.read_text("utf-8")[:5000]

    # Đọc edit guide (nếu có) — short dùng edit guide của video gốc
    edit_guide = ""
    edit_guide_path = video_dir / "edit_guide.md"
    if edit_guide_path.exists():
        edit_guide = edit_guide_path.read_text("utf-8")[:2000]

    # Chuẩn bị SRT dạng text cho Claude — giữ chính xác millisecond
    srt_lines = []
    for i, e in enumerate(entries):
        srt_lines.append(f"#{i+1} [{e['start']:.3f}s – {e['end']:.3f}s] {e['text']}")
    srt_text = "\n".join(srt_lines)

    if is_short:
        duration_rule = "3. Video ngắn 45-50 giây. Mỗi phân đoạn nên dài 3–8 giây. Tổng khoảng 5-10 phân đoạn"
    else:
        duration_rule = "3. Mỗi phân đoạn nên dài 4–10 giây. Có thể ngắn hơn (2-3s) cho hook/chuyển cảnh, dài hơn (12-15s) cho đoạn mô tả phức tạp"

    prompt = f"""Phân chia nội dung thuyết minh video thành các phân đoạn (scene) để tạo hình ảnh/video minh họa.

=== NGUYÊN TẮC CHIA PHÂN ĐOẠN ===
1. Mỗi phân đoạn chỉ tập trung vào MỘT ý/nội dung duy nhất (1 sự kiện, 1 mô tả, 1 hành động)
2. KHÔNG được cắt ngang giữa 1 câu hay 1 ý — nội dung phải trọn vẹn trong phân đoạn
{duration_rule}
4. GIỮ CHÍNH XÁC MILLISECOND (3 chữ số thập phân) từ SRT
5. Khi có khoảng trống thời gian (gap) giữa 2 SRT entries liền kề → chia đều gap cho 2 phân đoạn:
   - Phân đoạn trước: timestamp_end = end_SRT_cuối + (gap / 2)
   - Phân đoạn sau: timestamp_start = start_SRT_đầu - (gap / 2)
   - Nếu 2 entries ở cùng 1 phân đoạn thì KHÔNG chia gap
6. Phân đoạn đầu tiên: timestamp_start = 0.000 (bắt đầu video)
7. **QUAN TRỌNG — script_text**: SRT thường sai chính tả, thiếu dấu câu. Phải dùng NỘI DUNG GỐC (bên dưới) làm text đúng.
   - So khớp (match) từng đoạn SRT với đoạn tương ứng trong NỘI DUNG GỐC dựa trên nghĩa/từ khóa
   - script_text = đoạn text tương ứng từ NỘI DUNG GỐC (đúng chính tả, đầy đủ dấu câu)
   - Timestamp lấy từ SRT, text lấy từ NỘI DUNG GỐC
   - Nếu không có NỘI DUNG GỐC thì mới dùng text SRT

=== NỘI DUNG SRT (timestamp chính xác, nhưng text có thể sai chính tả) ===
{srt_text}

{"=== NỘI DUNG GỐC (đúng chính tả, đầy đủ dấu câu — dùng làm script_text) ===" + chr(10) + narration_content if narration_content else ""}

{f"=== KỊCH BẢN GỐC (tham khảo cấu trúc nội dung) ==={chr(10)}{script_content}" if script_content else ""}

{f"=== HƯỚNG DẪN EDIT ==={chr(10)}{edit_guide}" if edit_guide else ""}

Trả về ĐÚNG format JSON array (không có text khác):
[
  {{
    "scene_number": 1,
    "timestamp_start": 0.000,
    "timestamp_end": 5.520,
    "script_text": "Text đúng chính tả từ NỘI DUNG GỐC, có dấu câu đầy đủ."
  }},
  ...
]"""

    response = await session_manager.query(prompt)

    # Kiểm tra lỗi từ Claude
    if response.startswith("[Lỗi]") or response.startswith("[Timeout]") or response.startswith("[Không có"):
        _emit_activity("shotlist", "generate", f"Lỗi: {response[:100]}", project_id, video_id, "error")
        return {"status": "error", "message": response}

    # Parse JSON
    try:
        import re as _re
        json_match = _re.search(r'\[[\s\S]*\]', response)
        if json_match:
            scenes = json.loads(json_match.group())
        else:
            raise ValueError("Không tìm thấy JSON array trong response")
    except (json.JSONDecodeError, ValueError) as e:
        _emit_activity("shotlist", "generate", f"Lỗi parse: {e}", project_id, video_id, "error")
        return {"status": "error", "message": f"Không parse được: {str(e)}", "raw": response[:500]}

    # Validate & normalize
    for i, s in enumerate(scenes):
        s["scene_number"] = i + 1  # đảm bảo đánh số liên tục

    # Lưu shot_list.json
    shot_list = {
        "project_id": project_id,
        "video_id": video_id,
        "total_scenes": len(scenes),
        "scenes": scenes,
    }
    (data_dir / "shot_list.json").write_text(
        json.dumps(shot_list, ensure_ascii=False, indent=2), "utf-8"
    )

    _emit_activity("shotlist", "generate", f"Tạo xong {len(scenes)} phân đoạn", project_id, video_id, "success")
    return {"status": "ok", "scenes": scenes}


@app.post("/api/generate-scene-prompt/{project_id}/{video_id}/{scene_number}")
async def generate_scene_prompt(project_id: str, video_id: str, scene_number: int):
    """Gọi Claude tạo Veo3 prompt cho 1 scene cụ thể."""
    video_dir = PROJECTS_DIR / project_id / "videos" / video_id

    # Đọc style guide (nếu có)
    style_guide = ""
    for p in [video_dir / "visual_guide.md", PROJECTS_DIR / project_id / "style_guide.md"]:
        if p.exists():
            style_guide = p.read_text("utf-8")[:2000]
            break

    # Đọc shot_list.json để lấy thông tin scene
    shot_list_path = video_dir / "shot_list.json"
    if not shot_list_path.exists():
        raise HTTPException(400, "Chưa có danh sách cảnh. Hãy tạo từ SRT trước.")

    shot_list = json.loads(shot_list_path.read_text("utf-8"))
    scene_data = None
    for s in shot_list.get("scenes", []):
        if s["scene_number"] == scene_number:
            scene_data = s
            break

    if not scene_data:
        raise HTTPException(404, f"Không tìm thấy cảnh số {scene_number}")

    # Đọc danh sách nhân vật từ DB
    char_info = ""
    char_names = []
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/characters")
            if resp.status_code == 200:
                chars = resp.json()
                if chars:
                    char_names = [c["name"] for c in chars]
                    char_lines = [f"- {c['name']}: {c.get('visual_prompt_base', '')[:200]}" for c in chars]
                    char_info = "=== NHÂN VẬT ===\n" + "\n".join(char_lines)
    except Exception:
        pass

    prompt = f"""Tạo prompt tiếng Anh cho Veo 3 (AI video/image generation) dựa trên nội dung cảnh sau.

=== NỘI DUNG CẢNH ===
Cảnh số: {scene_data['scene_number']}
Thời gian: {scene_data['timestamp_start']}s — {scene_data['timestamp_end']}s
Nội dung thuyết minh: {scene_data['script_text']}

{f"=== PHONG CÁCH HÌNH ẢNH ==={chr(10)}{style_guide}" if style_guide else ""}
{char_info}

Yêu cầu:
- Prompt bằng TIẾNG ANH
- Tuân theo phong cách hình ảnh trong PHONG CÁCH HÌNH ẢNH ở trên (nếu có)
- Mô tả chi tiết: nhân vật, bối cảnh, hành động, góc máy, ánh sáng, mood
- Cũng cho biết visual_type phù hợp: "image" (cảnh tĩnh) hoặc "video" (có chuyển động)
- LƯU Ý: Tỷ lệ video chỉ chiếm khoảng 1/10 tổng số cảnh, ưu tiên cho đoạn mở đầu. Phần lớn cảnh nên là "image".
- Nếu visual_type là "video": prompt PHẢI có "No voice, no speech, no dialogue, no narration." Ambient/SFX nhẹ nhàng.
- Và mood: dramatic, calm, tense, happy, sad, epic, mysterious
- flow_characters: PHẢI COPY CHÍNH XÁC tên từ danh sách NHÂN VẬT ở trên. KHÔNG viết tắt, KHÔNG đổi tên. Chỉ dùng tên CÓ SẴN. Nếu không có → mảng rỗng [].
- Kịch bản dùng "bạn" = nhân vật chính → PHẢI thêm vào flow_characters.
- Nếu nhân vật có nhiều phiên bản (tuổi khác), chọn ĐÚNG phiên bản theo ngữ cảnh.

Trả về ĐÚNG format JSON (không có text khác):
{{
  "veo3_prompt": "prompt tiếng Anh ở đây...",
  "visual_type": "image hoặc video",
  "mood": "mood ở đây",
  "flow_characters": ["COPY CHÍNH XÁC tên từ danh sách nhân vật ở trên"]
}}"""

    response = await session_manager.query(prompt)

    # Kiểm tra lỗi từ Claude CLI
    if response.startswith("[Lỗi]") or response.startswith("[Timeout]") or response.startswith("[Không có"):
        return {"status": "error", "message": response}

    # Parse JSON
    try:
        import re as _re
        result = None
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
        for m in re.finditer(r'\{', cleaned):
            try:
                result = json.loads(cleaned[m.start():])
                break
            except json.JSONDecodeError:
                depth = 0
                for i, c in enumerate(cleaned[m.start():]):
                    if c == '{': depth += 1
                    elif c == '}': depth -= 1
                    if depth == 0:
                        try:
                            result = json.loads(cleaned[m.start():m.start()+i+1])
                        except json.JSONDecodeError:
                            pass
                        break
                if result:
                    break
        if not result:
            raise ValueError("Không tìm thấy JSON trong response")
    except (json.JSONDecodeError, ValueError) as e:
        return {"status": "error", "message": f"Không parse được: {str(e)}", "raw": response[:500]}

    # Fix flow_characters: match tên AI rút gọn → tên đúng trong DB
    veo3_prompt = result.get("veo3_prompt", "")
    flow_chars = result.get("flow_characters", [])
    if flow_chars and char_names:
        flow_chars = _fix_flow_characters(flow_chars, char_names)

    # Thêm @TênNhânVật vào prompt
    if flow_chars:
        char_tags = " ".join(f"@{name}" for name in flow_chars)
        veo3_prompt = f"{char_tags} {veo3_prompt}"

    return {
        "status": "ok",
        "scene_number": scene_number,
        "veo3_prompt": veo3_prompt,
        "visual_type": result.get("visual_type", "image"),
        "mood": result.get("mood", ""),
        "flow_characters": flow_chars,
    }


@app.post("/api/generate-all-prompts/{project_id}/{video_id}")
async def generate_all_prompts(project_id: str, video_id: str, mode: str = "missing", is_short: bool = False):
    """3-tier agent: Director → Segment Supervisors → Prompt Writers.
    mode: 'all' = tạo lại tất cả, 'missing' = chỉ cảnh chưa có prompt.
    """
    video_dir = PROJECTS_DIR / project_id / "videos" / video_id
    data_dir = video_dir / "shorts" if is_short else video_dir

    # Đọc shot_list.json
    shot_list_path = data_dir / "shot_list.json"
    if not shot_list_path.exists():
        raise HTTPException(400, "Chưa có danh sách cảnh. Hãy tạo từ SRT trước.")
    shot_list = json.loads(shot_list_path.read_text("utf-8"))
    all_scenes = shot_list.get("scenes", [])
    if not all_scenes:
        raise HTTPException(400, "Danh sách cảnh rỗng.")

    # Đọc visual_type hiện tại từ DB để giữ nguyên khi tạo lại prompt
    db_visual_types: Dict[int, str] = {}
    db_scenes_list = []
    try:
        import urllib.request
        scenes_resp = urllib.request.urlopen(
            f"http://localhost:8000/api/projects/{project_id}/videos/{video_id}/scenes", timeout=5
        )
        db_scenes_list = json.loads(scenes_resp.read().decode())
        for s in db_scenes_list:
            sn = s.get("scene_number")
            if sn is not None:
                db_visual_types[sn] = s.get("visual_type", "image")
    except Exception:
        pass

    # Lọc scenes theo mode
    if mode == "missing":
        existing_prompts = {s.get("scene_number") for s in db_scenes_list if s.get("veo3_prompt")}
        all_scenes = [s for s in all_scenes if s["scene_number"] not in existing_prompts]
        if not all_scenes:
            raise HTTPException(400, "Tất cả cảnh đã có prompt.")

    # Đọc guides
    style_guide = ""
    for p in [video_dir / "visual_guide.md", PROJECTS_DIR / project_id / "style_guide.md"]:
        if p.exists():
            style_guide = p.read_text("utf-8")[:3000]
            break

    edit_guide = ""
    eg_path = video_dir / "edit_guide.md"
    if eg_path.exists():
        edit_guide = eg_path.read_text("utf-8")[:3000]

    # Đọc characters từ backend API (DB)
    char_info = ""
    char_prompts = {}
    char_names_db = []  # Tên chính xác từ DB — dùng để validate AI output
    try:
        import urllib.request, urllib.parse
        encoded_url = f"http://localhost:8000/api/projects/{urllib.parse.quote(project_id, safe='')}/videos/{urllib.parse.quote(video_id, safe='')}/characters"
        char_resp = urllib.request.urlopen(encoded_url, timeout=5)
        chars = json.loads(char_resp.read().decode())
        if chars:
            char_lines = []
            for c in chars:
                name = c.get("name", "?")
                char_names_db.append(name)
                desc = c.get("reference_description", "")[:200]
                prompt_base = c.get("visual_prompt_base", "")
                anchors = ", ".join(c.get("consistency_anchors", [])[:5])
                char_lines.append(f"- {name}: {desc}")
                if prompt_base:
                    char_lines.append(f"  Visual prompt: {prompt_base[:300]}")
                if anchors:
                    char_lines.append(f"  Consistency anchors: {anchors}")
                if prompt_base:
                    char_prompts[name] = prompt_base
            char_info = "\n".join(char_lines)[:3000]
            # Build danh sách tên dạng đánh số cho prompt (ép AI dùng đúng tên)
            char_name_list = "\n".join(f"  {i+1}. \"{name}\"" for i, name in enumerate(char_names_db))
            log.info(f"[char_names_db] Loaded {len(char_names_db)} characters: {char_names_db}")
    except Exception as e:
        log.error(f"[char_names_db] Failed to load characters: {e}")
        pass

    scenes_summary = "\n".join(
        f"  Cảnh {s['scene_number']} ({s['timestamp_start']}s–{s['timestamp_end']}s): {s['script_text'][:120]}"
        for s in all_scenes
    )
    scenes_by_number = {s["scene_number"]: s for s in all_scenes}

    cancel_key = f"{project_id}::{video_id}"

    # Reconnect nếu job đang chạy
    existing_jid = _find_running_bg_job("generate_all", project_id, video_id)
    if existing_jid:
        return _sse_from_bg_job(BACKGROUND_JOBS[existing_jid])

    # Start background job
    job_id = _start_job("prompt", "generate_all", project_id, video_id, len(all_scenes))
    bg_job = BackgroundJob(job_id)
    BACKGROUND_JOBS[job_id] = bg_job

    async def work():
      """Generator yields event dicts — chạy background, không phụ thuộc SSE."""
      cancel_flag = asyncio.Event()
      CANCEL_FLAGS[cancel_key] = cancel_flag
      try:

        # ===== PHASE 1: Đạo diễn — chia segments + tiêu chuẩn chung =====
        yield {"type": "status", "message": "Đạo diễn đang phân tích kịch bản..."}

        format_note = ""
        if is_short:
            format_note = """
LƯU Ý — ĐÂY LÀ YOUTUBE SHORT:
- Format dọc 9:16 (1080x1920)
- Video ngắn 45-50 giây, chỉ cần 1-2 segments
- Chỉ khoảng 3 PHÂN CẢNH ĐẦU TIÊN là video clip, CÒN LẠI dùng hình ảnh tĩnh (image)
- Compose cho vertical — chủ thể giữa khung, close-up nhiều hơn wide shot
- Mọi prompt phải thêm: "Vertical 9:16 aspect ratio, 1080x1920"
"""

        director_prompt = f"""Bạn là đạo diễn hình ảnh cho video hoạt hình ({len(all_scenes)} cảnh).
{format_note}
NHIỆM VỤ: Đọc toàn bộ kịch bản VÀ các quy định hình ảnh/edit bên dưới, chia thành các ĐOẠN CÂU CHUYỆN (story segments) và đặt TIÊU CHUẨN CHUNG.
KHÔNG cần tạo visual plan chi tiết cho từng cảnh — việc đó sẽ do các agent khác làm.

=== DANH SÁCH CẢNH ===
{scenes_summary}

{f"=== PHONG CÁCH HÌNH ẢNH (QUY ĐỊNH CỦA DỰ ÁN — BẮT BUỘC TUÂN THEO) ==={chr(10)}{style_guide}" if style_guide else ""}
{f"=== HƯỚNG DẪN EDIT (QUY ĐỊNH CỦA DỰ ÁN — BẮT BUỘC TUÂN THEO) ==={chr(10)}{edit_guide}" if edit_guide else ""}
{f"=== NHÂN VẬT ==={chr(10)}{char_info}" if char_info else ""}

Trả về ĐÚNG format JSON (không text khác):
{{
  "segments": [
    {{
      "name": "tên đoạn (VD: Hook - Pháo đài bí ẩn)",
      "scene_numbers": [1, 2, 3, 4, 5, 6],
      "description": "mô tả ngắn nội dung đoạn này",
      "mood_progression": "mysterious → dramatic",
      "color_tone": "warm, muted",
      "characters": {{
        "COPY NGUYÊN VĂN tên từ DANH SÁCH TÊN NHÂN VẬT bên dưới": "mô tả ngoại hình + trang phục TIẾNG ANH cho đoạn này. Chi tiết: khuôn mặt, tuổi, dáng, tóc, râu, trang phục cụ thể theo ngữ cảnh đoạn"
      }},
      "camera_notes": "gợi ý góc máy cho đoạn (VD: wide establishing shots, then medium close-ups)",
      "video_count": "số cảnh nên là video trong đoạn này (số nguyên)"
    }}
  ],
  "global_rules": {{
    "art_style": "tóm tắt quy tắc phong cách hình ảnh (lấy từ QUY ĐỊNH ở trên)",
    "character_distinction": "quy tắc phân biệt nhân vật (tuổi, dáng, mặt khác nhau)",
    "consistency_notes": "quy tắc nhất quán (cùng đoạn = cùng trang phục)"
  }}
}}

QUY TẮC:
- Chia đoạn theo CỐT TRUYỆN, không theo thời gian cơ học
- Mỗi đoạn khoảng 5-15 cảnh
- Mô tả characters bằng TIẾNG ANH, giữ tên tiếng Việt CÓ DẤU
- Phân bổ video/image và các quy tắc khác: tuân theo QUY ĐỊNH HÌNH ẢNH và HƯỚNG DẪN EDIT ở trên

QUY TẮC CỨNG VỀ NHÂN VẬT:
- CÙNG ĐOẠN = CÙNG TRANG PHỤC: Tất cả nhân vật trong cùng 1 segment phải mặc cùng 1 bộ trang phục xuyên suốt. Chỉ thay đổi trang phục khi sang segment khác có ngữ cảnh khác.
- NHÂN VẬT PHỤ PHẢI KHÁC MẶT NHÂN VẬT CHÍNH: Nhân vật quần chúng, lính, dân thường PHẢI có ngoại hình KHÁC BIỆT RÕ RÀNG với nhân vật chính (khác kiểu tóc, râu, tuổi, dáng). KHÔNG được giống mặt nhân vật chính.
- Mỗi nhân vật chính PHẢI có ngoại hình ĐỘC NHẤT — phân biệt rõ ràng bằng khuôn mặt, tuổi, dáng, tóc, râu.
- Trang phục nhân vật có thể KHÁC nhau giữa các đoạn nếu ngữ cảnh thay đổi (VD: triều phục → giáp chiến).
{f'''
=== DANH SÁCH TÊN NHÂN VẬT (BẮT BUỘC DÙNG ĐÚNG) ===
{char_name_list}

QUAN TRỌNG: Key trong "characters" PHẢI COPY NGUYÊN VĂN từ danh sách trên. KHÔNG được viết tắt, đổi tên, hay nghĩ ra tên mới. Chỉ dùng tên CÓ SẴN trong danh sách.
''' if char_names_db else ''}

QUY TẮC CỨNG VỀ TỶ LỆ VIDEO/IMAGE:
- Tổng số cảnh video TOÀN BỘ VIDEO chỉ khoảng 1/10 tổng số cảnh (VD: 20 cảnh → tối đa 2 cảnh video)
- Cảnh video NÊN TẬP TRUNG ở đoạn mở đầu (Hook, Bối cảnh) để tạo ấn tượng đầu tiên
- Các đoạn giữa và cuối CHỦ YẾU dùng ảnh tĩnh + Ken Burns
- video_count: CHỈ ĐỊNH CỤ THỂ số cảnh video cho từng đoạn, đảm bảo TỔNG chỉ khoảng 1/10"""

        director_response = await _call_claude_async(director_prompt, emit_context={
            "category": "prompt", "project_id": project_id, "video_id": video_id,
            "job_id": job_id, "label": "Đạo diễn",
        })

        if director_response.startswith("[Lỗi]") or director_response.startswith("[Không có"):
            yield {"type": "error", "message": f"Đạo diễn lỗi: {director_response}"}
            return

        # Parse director plan
        director_plan = None
        try:
            cleaned = re.sub(r'```json\s*', '', director_response)
            cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
            json_match = re.search(r'\{\s*"segments"[\s\S]*\}', cleaned)
            if json_match:
                director_plan = json.loads(json_match.group())
            else:
                raise ValueError("Không tìm thấy JSON")
        except (json.JSONDecodeError, ValueError) as e:
            log.error(f"Director JSON parse error: {e}\nRaw: {director_response[:500]}")
            _emit_activity("prompt", "error", f"Đạo diễn trả lỗi format — {e}", project_id, video_id, "error", job_id)
            yield {"type": "error", "message": f"Đạo diễn trả lỗi format: {e}", "raw_preview": director_response[:300]}
            return

        segments = director_plan.get("segments", [])
        global_rules = director_plan.get("global_rules", {})

        # Fix character keys trong director output: match tên rút gọn → tên đúng DB
        if char_names_db:
            for seg in segments:
                chars_dict = seg.get("characters", {})
                if chars_dict and isinstance(chars_dict, dict):
                    fixed_chars = {}
                    for ai_key, desc in chars_dict.items():
                        fixed_keys = _fix_flow_characters([ai_key], char_names_db)
                        fixed_chars[fixed_keys[0]] = desc
                    seg["characters"] = fixed_chars

        # Lưu director plan
        (data_dir / "director_plan.json").write_text(json.dumps(director_plan, ensure_ascii=False, indent=2), "utf-8")

        _emit_activity("prompt", "director_done", f"Chia {len(segments)} đoạn: {', '.join(seg['name'][:20] for seg in segments)}", project_id, video_id, "success", job_id)
        yield {"type": "plan_done", "message": f"Đạo diễn chia {len(segments)} đoạn. Bắt đầu tạo visual plan...", "plan": segments}

        if cancel_flag.is_set():
            yield {"type": "stopped", "message": "Đã dừng."}
            return

        # ===== PHASE 2: Segment Supervisors — song song, mỗi agent lên visual plan cho 1 đoạn =====
        global_rules_text = json.dumps(global_rules, ensure_ascii=False, indent=2) if global_rules else ""
        master_plan = []  # Tích lũy visual plan từ tất cả segments

        async def segment_supervisor(segment):
            seg_name = segment["name"]
            seg_scene_nums = segment.get("scene_numbers", [])
            seg_scenes = [scenes_by_number[n] for n in seg_scene_nums if n in scenes_by_number]
            if not seg_scenes:
                return []

            seg_scenes_text = "\n".join(
                f"  Cảnh {s['scene_number']} ({s['timestamp_start']}s–{s['timestamp_end']}s): {s['script_text'][:150]}"
                for s in seg_scenes
            )
            # Merge: director characters + DB info, ưu tiên DB names
            director_chars = segment.get("characters", {})
            seg_chars = json.dumps(director_chars, ensure_ascii=False, indent=2)
            # Build danh sách tên DB đánh số cho supervisor (ép dùng index)
            db_char_indexed = ""
            if char_names_db:
                lines = [f'  CHAR_{i}: "{name}"' for i, name in enumerate(char_names_db)]
                db_char_indexed = "\n=== BẢNG MÃ NHÂN VẬT (DÙNG MÃ CHAR_N TRONG flow_characters) ===\n" + "\n".join(lines) + "\n"

            sup_prompt = f"""Bạn là trợ lý đạo diễn hình ảnh. Tạo visual plan CHI TIẾT cho đoạn "{seg_name}" ({len(seg_scenes)} cảnh).

=== TIÊU CHUẨN CHUNG TỪ ĐẠO DIỄN ===
{global_rules_text}

=== THÔNG TIN ĐOẠN ===
Tên: {seg_name}
Mô tả: {segment.get('description', '')}
Mood: {segment.get('mood_progression', '')}
Color tone: {segment.get('color_tone', '')}
Gợi ý góc máy: {segment.get('camera_notes', '')}
Số cảnh video yêu cầu: {segment.get('video_count', 1)} (đạo diễn chỉ định — phải đúng con số này)

=== NHÂN VẬT TRONG ĐOẠN (ngoại hình + trang phục đã xác định) ===
{seg_chars}

{db_char_indexed}

=== DANH SÁCH CẢNH ===
{seg_scenes_text}

{f"=== PHONG CÁCH HÌNH ẢNH (QUY ĐỊNH CỦA DỰ ÁN — BẮT BUỘC TUÂN THEO) ==={chr(10)}{style_guide[:1500]}" if style_guide else ""}

Tạo visual plan cho TỪNG CẢNH. Trả về ĐÚNG format JSON array:
[
  {{
    "scene_number": N,
    "visual_brief": "mô tả tiếng Anh 2-3 câu: nhân vật + trang phục, bối cảnh, hành động, góc máy, ánh sáng",
    "characters": {{"Tên nhân vật": "COPY NGUYÊN VĂN mô tả từ mục nhân vật ở trên"}},
    "flow_characters": ["CHAR_0", "CHAR_1"],
    "story_segment": "{seg_name}",
    "visual_type": "image hoặc video",
    "mood": "dramatic/calm/tense/epic/mysterious/sad",
    "color_tone": "warm/cool/muted/vibrant/dark",
    "edit_plan": {{
      "transition_in": "loại chuyển cảnh vào (crossfade/cut/fade_from_black)",
      "transition_out": "loại chuyển cảnh ra",
      "ken_burns": "nếu image — hướng zoom/pan (VD: slow zoom in to face, pan left to right). Nếu video: null",
      "pacing": "nhịp cho cảnh này (VD: 4s hold, quick 2s cut)",
      "text_overlay": "text cần hiển thị (tên nhân vật, năm, địa điểm) hoặc null",
      "sound_note": "ghi chú âm thanh/nhạc nền nếu cần thay đổi"
    }},
    "duration": "CHỈ khi video — thời lượng clip (5-8 giây). Nếu image: bỏ field này",
    "timeline_hints": "CHỈ khi video — array chia nhỏ hành động theo thời gian, VD: [{{\"time\": \"0-3s\", \"action\": \"Wide shot of misty river delta, war elephant emerges from fog\"}}, {{\"time\": \"3-6s\", \"action\": \"Camera tilts up revealing warrior on elephant, army behind\"}}]. Nếu image: bỏ field này",
    "camera_style": "CHỈ khi video — phong cách camera (VD: 'cinematic slow push-in', 'handheld tracking'). Nếu image: bỏ field này",
    "audio_direction": "CHỈ khi video — mô tả SFX + ambient (VD: 'war drums, elephant footsteps, wind'). Nếu image: bỏ field này"
  }}
]

{f"=== HƯỚNG DẪN EDIT (QUY ĐỊNH CỦA DỰ ÁN — BẮT BUỘC TUÂN THEO) ==={chr(10)}{edit_guide[:1500]}" if edit_guide else ""}

QUY TẮC:
- Characters: COPY NGUYÊN VĂN mô tả trang phục từ mục nhân vật, KHÔNG diễn giải lại
- visual_brief: PHẢI nhắc trang phục cụ thể, KHÔNG nói "same outfit"
- Nhân vật phụ/quần chúng PHẢI có ngoại hình KHÁC mặt nhân vật chính (khác tóc, râu, tuổi, dáng). Ghi rõ trong visual_brief.
- flow_characters: Dùng MÃ CHAR_N từ BẢNG MÃ NHÂN VẬT ở trên. VD: ["CHAR_0", "CHAR_2"]. Nếu cảnh không có nhân vật → mảng rỗng []. KHÔNG dùng tên, CHỈ dùng mã CHAR_N.
- QUAN TRỌNG: Kịch bản dùng ngôi "bạn" để chỉ nhân vật chính. Nếu cảnh có "bạn" trong nội dung thuyết minh → PHẢI thêm mã CHAR_N tương ứng vào flow_characters.
- Nếu cùng 1 nhân vật có NHIỀU PHIÊN BẢN (VD: tuổi trẻ vs trưởng thành), PHẢI chọn ĐÚNG phiên bản (ĐÚNG mã CHAR_N) dựa trên ngữ cảnh kịch bản.
- Mọi cảnh nhắc đến nhân vật (trực tiếp hoặc gián tiếp) đều PHẢI liệt kê mã CHAR_N trong flow_characters.
- Đa dạng góc máy (wide, medium, close-up xen kẽ)
- visual_type: ĐÚNG {segment.get('video_count', 1)} cảnh phải là "video", còn lại là "image" (đạo diễn chỉ định)
- QUY TẮC CỨNG: Tổng video toàn bộ video chỉ khoảng 1/10 tổng cảnh, tập trung ở đoạn mở đầu
- Ưu tiên "video" cho cảnh mở đầu, hành động mạnh. Các đoạn giữa và cuối chủ yếu dùng "image"
- Cảnh tĩnh, miêu tả, bối cảnh → "image"
- edit_plan: PHẢI có cho mỗi cảnh, tuân theo hướng dẫn edit ở trên. KHÔNG để trong visual_brief hay prompt
- Cảnh video PHẢI có: duration (5-8s), timeline_hints (2-3 đoạn action TIẾNG ANH), camera_style, audio_direction
- timeline_hints: TIẾNG ANH, chi tiết hành động + camera movement + lighting. KHÔNG có chữ tiếng Việt hay dấu
- audio_direction: TIẾNG ANH, mô tả SFX + ambient sound (KHÔNG phải nhạc nền). BẮT BUỘC: No voice, no speech, no dialogue, no narration. Ambient/SFX phải nhẹ (subtle, low volume)
- Text tiếng Việt (tên nhân vật, địa danh, năm) → vào edit_plan.text_overlay, KHÔNG vào timeline_hints"""

            resp = await _call_claude_async(sup_prompt, emit_context={
                "category": "prompt", "project_id": project_id, "video_id": video_id,
                "job_id": job_id, "label": f"Đoạn: {seg_name[:25]}",
            })

            if resp.startswith("[Lỗi]") or resp.startswith("[Không có"):
                _emit_activity("prompt", "error", f"Đoạn '{seg_name}' lỗi: {resp[:100]}", project_id, video_id, "error", job_id)
                return []

            try:
                cleaned = re.sub(r'```json\s*', '', resp)
                cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
                jm = re.search(r'\[\s*\{[\s\S]*\}\s*\]', cleaned)
                if jm:
                    plans = json.loads(jm.group())
                    # Convert CHAR_N codes → DB names + fuzzy fallback
                    log.info(f"[resolve] char_names_db has {len(char_names_db)} items: {char_names_db[:3]}")
                    if char_names_db:
                        def _resolve_char(name):
                            """Convert CHAR_N → DB name, hoặc fuzzy match."""
                            m = re.match(r'^CHAR_(\d+)$', name.strip())
                            if m:
                                idx = int(m.group(1))
                                if 0 <= idx < len(char_names_db):
                                    return char_names_db[idx]
                            # Fallback: fuzzy match
                            return _fix_flow_characters([name], char_names_db)[0]

                        for p in plans:
                            # Fix flow_characters
                            fc = p.get("flow_characters", [])
                            if fc:
                                resolved = [_resolve_char(n) for n in fc]
                                log.info(f"[resolve] scene {p.get('scene_number')}: {fc} → {resolved}")
                                p["flow_characters"] = resolved
                            # Fix characters dict keys
                            chars_dict = p.get("characters", {})
                            if chars_dict and isinstance(chars_dict, dict):
                                fixed_chars = {}
                                for ai_key, desc in chars_dict.items():
                                    fixed_chars[_resolve_char(ai_key)] = desc
                                p["characters"] = fixed_chars
                    return plans
                raise ValueError("No JSON array")
            except (json.JSONDecodeError, ValueError) as e:
                log.error(f"Segment '{seg_name}' parse error: {e}")
                _emit_activity("prompt", "error", f"Đoạn '{seg_name}' parse lỗi: {e}", project_id, video_id, "error", job_id)
                return []

        # Chạy tất cả segment supervisors song song
        _emit_activity("prompt", "segments_start", f"Chạy {len(segments)} segment agents song song...", project_id, video_id, "working", job_id)
        yield {"type": "status", "message": f"Đang tạo visual plan cho {len(segments)} đoạn..."}

        seg_tasks = [asyncio.create_task(segment_supervisor(seg)) for seg in segments]
        for i, coro in enumerate(asyncio.as_completed(seg_tasks)):
            if cancel_flag.is_set():
                for t in seg_tasks:
                    t.cancel()
                yield {"type": "stopped", "message": "Đã dừng."}
                return
            seg_plan = await coro
            master_plan.extend(seg_plan)
            _emit_activity("prompt", "segment_done", f"Đoạn {i+1}/{len(segments)} xong — {len(seg_plan)} cảnh", project_id, video_id, "success", job_id)
            yield {"type": "status", "message": f"Visual plan: {i+1}/{len(segments)} đoạn xong ({len(master_plan)} cảnh)"}

        # Lưu master plan tổng hợp
        (data_dir / "visual_plan.json").write_text(json.dumps(master_plan, ensure_ascii=False, indent=2), "utf-8")
        plan_by_scene = {p["scene_number"]: p for p in master_plan}

        _emit_activity("prompt", "plan_done", f"Visual plan xong — {len(master_plan)} cảnh. Bắt đầu viết prompt...", project_id, video_id, "success", job_id)
        yield {"type": "plan_done", "message": f"Visual plan xong — {len(master_plan)} cảnh. Bắt đầu viết Veo3 prompt...", "plan": master_plan}

        if cancel_flag.is_set():
            yield {"type": "stopped", "message": "Đã dừng."}
            return

        # ===== PHASE 3: Prompt Writers — song song, mỗi agent viết Veo3 prompt cho 1 cảnh =====
        semaphore = asyncio.Semaphore(10)

        async def prompt_writer(scene_data):
            async with semaphore:
                sn = scene_data["scene_number"]
                plan = plan_by_scene.get(sn, {})

                plan_characters = plan.get("characters", {})
                scene_chars = ""
                if isinstance(plan_characters, dict) and plan_characters:
                    char_lines = [f"- {name}: {desc}" for name, desc in plan_characters.items()]
                    scene_chars = f"=== NHÂN VẬT — NGOẠI HÌNH & TRANG PHỤC (đoạn: {plan.get('story_segment', '?')}) ===\n" + "\n".join(char_lines)
                elif char_prompts:
                    script = scene_data.get("script_text", "")
                    matched = [f"- {name}: {prompt}" for name, prompt in char_prompts.items() if name in script]
                    if matched:
                        scene_chars = "=== NHÂN VẬT TRONG CẢNH ===\n" + "\n".join(matched)

                edit_plan_from_sup = json.dumps(plan.get("edit_plan", {}), ensure_ascii=False) if plan.get("edit_plan") else "Chưa có"
                visual_type = plan.get("visual_type", "image")

                if visual_type == "video":
                    # === VIDEO PROMPT — structured, timestamp-based ===
                    duration = plan.get("duration", 8)
                    timeline_hints = json.dumps(plan.get("timeline_hints", []), ensure_ascii=False)
                    camera_style = plan.get("camera_style", "cinematic")
                    audio_direction = plan.get("audio_direction", "")

                    writer_prompt = f"""Tạo STRUCTURED VIDEO PROMPT tiếng Anh cho Veo 3.

=== THÔNG TIN CẢNH ===
Cảnh số: {sn}
Nội dung thuyết minh: {scene_data['script_text']}

=== VISUAL PLAN ===
Brief: {plan.get('visual_brief', 'N/A')}
Duration: {duration}s
Camera style: {camera_style}
Audio direction: {audio_direction}
Timeline hints: {timeline_hints}
Mood: {plan.get('mood', 'N/A')}
Color: {plan.get('color_tone', 'N/A')}

{scene_chars}

{f"=== PHONG CÁCH HÌNH ẢNH (QUY ĐỊNH DỰ ÁN) ==={chr(10)}{style_guide[:1000]}" if style_guide else ""}

Yêu cầu — tạo prompt VIDEO có cấu trúc NHIỀU DÒNG, format CHÍNH XÁC:

Dòng 1: (style prefix — lấy từ phong cách hình ảnh của dự án ở trên, VD: art style, shading, outlines){". Thêm: Vertical 9:16 aspect ratio, 1080x1920 pixels." if is_short else ""}
Dòng 2: Duration: {duration} seconds.
Dòng 3: No subtitles. No on-screen text. No background music.
Dòng 4: Characters: (COPY NGUYÊN VĂN mô tả nhân vật từ visual plan — khuôn mặt, trang phục, dáng người)
Dòng 5: Camera: (camera style cụ thể)
Dòng 6: Mood: (mood)
Dòng 7: Summary: (tóm tắt tổng quan 1 câu tiếng Anh)
Dòng 8+: Timestamp segments — chia hành động theo thời gian:
  0-3s: (hành động chi tiết, camera movement, lighting)
  3-6s: (hành động tiếp)
  6-{duration}s: (kết thúc)
Dòng tiếp: Audio: (SFX + ambient sound — subtle, low volume)
Dòng cuối: Additional notes: No voice, no speech, no dialogue, no narration. One continuous shot, no cuts.

QUY TẮC BẮT BUỘC:
- TOÀN BỘ bằng TIẾNG ANH, KHÔNG có chữ tiếng Việt hay dấu
- Thay tên riêng bằng mô tả: "Trưng Trắc" → "the fierce woman warrior leader"
- COPY mô tả nhân vật chi tiết (khuôn mặt, trang phục, dáng) từ visual plan
- Timestamp segments PHẢI cộng đúng = {duration}s
- KHÔNG đưa thông tin edit (transition, text overlay) vào prompt
- Video KHÔNG ĐƯỢC CÓ tiếng nói/lời thoại. Âm thanh môi trường (ambient, SFX) phải nhẹ nhàng

Trả về JSON:
{{
  "veo3_prompt": "toàn bộ structured prompt ở đây, mỗi dòng cách nhau bằng \\n"
}}"""
                else:
                    # === IMAGE PROMPT — flat, 2-4 câu ===
                    writer_prompt = f"""Tạo prompt tiếng Anh chi tiết cho Veo 3 để tạo ẢNH TĨNH.

=== THÔNG TIN CẢNH ===
Cảnh số: {sn}
Nội dung: {scene_data['script_text']}

=== VISUAL PLAN ===
Brief: {plan.get('visual_brief', 'N/A')}
Mood: {plan.get('mood', 'N/A')}
Color: {plan.get('color_tone', 'N/A')}
Segment: {plan.get('story_segment', 'N/A')}

{scene_chars}

{f"=== PHONG CÁCH HÌNH ẢNH (QUY ĐỊNH DỰ ÁN) ==={chr(10)}{style_guide[:1000]}" if style_guide else ""}

Yêu cầu:
- Prompt TIẾNG ANH, 2-4 câu, tuân theo phong cách hình ảnh của dự án ở trên
{f"- Thêm vào prompt: 'Vertical 9:16 aspect ratio, 1080x1920 pixels. Subject centered, portrait framing, tight crop.'" if is_short else ""}
- COPY NGUYÊN VĂN mô tả nhân vật vào prompt
- Mô tả cụ thể: bối cảnh, ánh sáng, composition, camera angle
- KHÔNG đưa thông tin edit (chuyển cảnh, ken burns, text overlay) vào prompt

Trả về JSON:
{{
  "veo3_prompt": "prompt tiếng Anh 2-4 câu cho Veo 3"
}}"""

                resp = await _call_claude_async(writer_prompt, emit_context={
                    "category": "prompt", "project_id": project_id, "video_id": video_id,
                    "job_id": job_id, "label": f"Cảnh {sn}",
                })

                if resp.startswith("[Lỗi]") or resp.startswith("[Không có"):
                    return {"scene_number": sn, "status": "error", "message": resp}

                try:
                    cleaned = re.sub(r'```json\s*', '', resp)
                    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
                    # Tìm JSON object — thử parse từ mỗi '{' cho đến khi thành công
                    result = None
                    for m in re.finditer(r'\{', cleaned):
                        try:
                            result = json.loads(cleaned[m.start():])
                            break
                        except json.JSONDecodeError:
                            # Thử tìm closing brace matching
                            depth = 0
                            for i, c in enumerate(cleaned[m.start():]):
                                if c == '{': depth += 1
                                elif c == '}': depth -= 1
                                if depth == 0:
                                    try:
                                        result = json.loads(cleaned[m.start():m.start()+i+1])
                                    except json.JSONDecodeError:
                                        pass
                                    break
                            if result:
                                break
                    if not result:
                        raise ValueError("No JSON found")
                except (json.JSONDecodeError, ValueError) as e:
                    _append_gen_error(project_id, video_id, {
                        "scene_number": sn,
                        "type": "prompt",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    })
                    return {"scene_number": sn, "status": "error", "message": str(e)}

                # Thêm @TênNhânVật vào đầu prompt cho Google Flow
                veo3_prompt = result.get("veo3_prompt", "")
                flow_chars = plan.get("flow_characters", [])
                if flow_chars:
                    char_tags = " ".join(f"@{name}" for name in flow_chars)
                    veo3_prompt = f"{char_tags} {veo3_prompt}"

                return {
                    "scene_number": sn,
                    "status": "ok",
                    "veo3_prompt": veo3_prompt,
                    "visual_type": plan.get("visual_type", "image"),
                    "mood": plan.get("mood", result.get("mood", "")),
                    "edit_plan": plan.get("edit_plan", {}),
                    "flow_characters": flow_chars,
                }

        tasks = [asyncio.create_task(prompt_writer(s)) for s in all_scenes]
        completed = 0
        total = len(tasks)
        for coro in asyncio.as_completed(tasks):
            if cancel_flag.is_set():
                for t in tasks:
                    t.cancel()
                yield {"type": "stopped", "message": f"Đã dừng — {completed}/{total} cảnh."}
                _finish_job(job_id, "stopped", f"Dừng tại {completed}/{total} cảnh")
                break
            result = await coro
            completed += 1
            result["progress"] = f"{completed}/{total}"
            _update_job(job_id, completed)
            sn = result.get("scene_number", "?")
            st = result.get("status", "ok")
            vt = result.get("visual_type", "?")
            # Lưu prompt + visual_type vào DB ngay từ server (không phụ thuộc frontend)
            if st == "ok" and isinstance(sn, int):
                update_payload = {
                    "veo3_prompt": result.get("veo3_prompt", ""),
                    "visual_type": result.get("visual_type", "image"),
                    "mood": result.get("mood", ""),
                }
                ep = result.get("edit_plan")
                if ep:
                    update_payload["edit_plan"] = ep
                fc = result.get("flow_characters")
                if fc:
                    update_payload["flow_characters"] = fc
                try:
                    scene_url = f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/scenes/{sn}"
                    if is_short:
                        scene_url += "?is_short=true"
                    async with httpx.AsyncClient() as client:
                        await client.put(scene_url, json=update_payload, timeout=10)
                except Exception as e:
                    log.warning(f"Cảnh {sn} — lưu DB lỗi: {e}")

            _emit_activity("prompt", "scene_prompt", f"Cảnh {sn} — {st} [{vt}] ({completed}/{total})", project_id, video_id, "success" if st == "ok" else "error", job_id)
            yield {"type": "scene_done", **result}
        else:
            _finish_job(job_id, "done", f"Hoàn tất {total} cảnh")
            yield {"type": "all_done", "message": f"Hoàn tất {total} cảnh."}

        await asyncio.gather(*tasks, return_exceptions=True)
      finally:
        CANCEL_FLAGS.pop(cancel_key, None)

    asyncio.create_task(_run_bg(bg_job, job_id, work()))
    return _sse_from_bg_job(bg_job)


@app.post("/api/extract-characters/{project_id}/{video_id}")
async def extract_characters(project_id: str, video_id: str):
    """Phân tích kịch bản và trích xuất nhân vật lịch sử bằng Claude."""
    _emit_activity("character", "extract", "Phân tích nhân vật từ kịch bản", project_id, video_id, "working")
    video_dir = PROJECTS_DIR / project_id / "videos" / video_id

    # 1. Đọc script content (thử theo thứ tự ưu tiên)
    script_content = ""
    script_source = ""
    for fname, label in [
        ("narration.md", "narration"),
        ("script.md", "script"),
    ]:
        p = video_dir / fname
        if p.exists():
            script_content = p.read_text("utf-8").strip()
            if script_content:
                script_source = label
                break

    # Fallback: SRT
    if not script_content:
        srt_path = video_dir / "audio" / "subtitles.srt"
        if srt_path.exists():
            srt_text = srt_path.read_text("utf-8").strip()
            if srt_text:
                # Trích text thuần từ SRT (bỏ index, timestamp)
                lines = []
                for block in re.split(r'\n\s*\n', srt_text):
                    block_lines = block.strip().split('\n')
                    if len(block_lines) >= 3:
                        lines.extend(block_lines[2:])
                script_content = ' '.join(l.strip() for l in lines if l.strip())
                script_source = "srt"

    if not script_content:
        raise HTTPException(400, "Chưa có kịch bản (narration.md, script.md, hoặc subtitles.srt).")

    # 2. Đọc project info
    project_info = ""
    pj_path = PROJECTS_DIR / project_id / "project.json"
    if pj_path.exists():
        try:
            pj_data = json.loads(pj_path.read_text("utf-8"))
            info_parts = []
            if pj_data.get("name"):
                info_parts.append(f"Dự án: {pj_data['name']}")
            if pj_data.get("era"):
                info_parts.append(f"Thời kỳ: {pj_data['era']}")
            if pj_data.get("type"):
                info_parts.append(f"Loại: {pj_data['type']}")
            if pj_data.get("time_period"):
                info_parts.append(f"Giai đoạn: {pj_data['time_period']}")
            project_info = "\n".join(info_parts)
        except (json.JSONDecodeError, OSError):
            pass

    # 3. Đọc visual guide (ưu tiên video-level, fallback project-level style guide)
    style_guide = ""
    video_visual_guide_path = video_dir / "visual_guide.md"
    if video_visual_guide_path.exists():
        style_guide = video_visual_guide_path.read_text("utf-8").strip()[:3000]
    if not style_guide:
        sg_path = PROJECTS_DIR / project_id / "style_guide.md"
        if sg_path.exists():
            style_guide = sg_path.read_text("utf-8").strip()[:2000]

    # 4. Gọi Claude phân tích
    prompt = f"""Phân tích kịch bản video sau và trích xuất TẤT CẢ nhân vật quan trọng xuất hiện.

=== KỊCH BẢN ===
{script_content[:5000]}

{f"=== THÔNG TIN DỰ ÁN ==={chr(10)}{project_info}" if project_info else ""}
{f"=== PHONG CÁCH HÌNH ẢNH (QUY ĐỊNH CỦA DỰ ÁN — BẮT BUỘC TUÂN THEO) ==={chr(10)}{style_guide}" if style_guide else ""}

Với mỗi nhân vật, hãy cung cấp thông tin CHI TIẾT:
- Nếu là NHÂN VẬT CÓ THẬT (lịch sử, người nổi tiếng, vận động viên...): mô phỏng theo ngoại hình thật, dựa trên ảnh chụp, tranh vẽ, tư liệu. Ghi rõ nguồn tham khảo.
- Nếu là NHÂN VẬT HƯ CẤU: thiết kế ngoại hình phù hợp với ngữ cảnh kịch bản.

Trả về ĐÚNG format JSON array (KHÔNG có text nào khác ngoài JSON):
[
  {{
    "name": "Tên nhân vật (có dấu nếu tiếng Việt)",
    "historical_name": "Tên đầy đủ / tên thật (nếu là người có thật). Nếu hư cấu: để trống",
    "era": "Thời kỳ / bối cảnh (VD: 'Thế kỷ 13', 'Hiện đại', 'Esports 2020s')",
    "age_range": "VD: 30-40",
    "reference_description": "Mô tả bằng tiếng Việt: ngoại hình dựa trên tư liệu thật (nếu người có thật) hoặc thiết kế (nếu hư cấu). Ghi rõ nguồn nếu có.",
    "visual_prompt_base": "English prompt theo phong cách hình ảnh của dự án (đọc từ QUY ĐỊNH ở trên). MUST start with: 'Front-facing portrait, medium shot, looking directly at camera.' Then include art style từ quy định dự án. Describe in detail: face shape, facial hair, hair style and color, skin tone, exact clothing with accurate details (patterns, materials, colors), body build, posture. Nếu là người có thật: MÔ PHỎNG theo ngoại hình thật (VD: Faker → young Korean male, sharp jawline, short black hair...). Character must be centered, symmetrical, on a simple neutral background. This prompt will be reused across ALL scenes for consistency.",
    "color_palette": {{
      "skin": "hex hoặc mô tả",
      "hair": "hex hoặc mô tả",
      "primary_outfit": "hex hoặc mô tả",
      "secondary_outfit": "hex hoặc mô tả"
    }},
    "consistency_anchors": ["3-5 đặc điểm nhận dạng PHẢI giữ nhất quán, VD: sharp jawline, short black hair, team jersey with number 1"]
  }}
]

QUAN TRỌNG:
- visual_prompt_base phải bằng TIẾNG ANH, chi tiết và cụ thể để đảm bảo nhất quán xuyên suốt video
- Giữ tên tiếng Việt CÓ DẤU trong visual_prompt_base (VD: "Trần Hưng Đạo", không phải "Tran Hung Dao")
- Phong cách BẮT BUỘC: tuân theo quy định hình ảnh của dự án ở trên
- Nhân vật có thật: MÔ PHỎNG ngoại hình giống nguyên tác nhất có thể
- Nhân vật hư cấu: thiết kế phù hợp ngữ cảnh, đảm bảo phân biệt rõ với nhân vật khác
- consistency_anchors là những đặc điểm KHÔNG ĐƯỢC thay đổi giữa các cảnh
- Nếu không có nhân vật nào, trả về mảng rỗng: []"""

    response = await _call_claude_async(prompt, emit_context={
        "category": "character", "project_id": project_id, "video_id": video_id,
        "job_id": "", "label": "Trích xuất nhân vật",
    })

    # 5. Kiểm tra lỗi
    if response.startswith("[Lỗi]") or response.startswith("[Timeout]") or response.startswith("[Không có"):
        return {"status": "error", "message": response}

    # 6. Parse JSON response
    try:
        json_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', response)
        if json_match:
            characters = json.loads(json_match.group())
        else:
            # Có thể là mảng rỗng
            empty_match = re.search(r'\[\s*\]', response)
            if empty_match:
                characters = []
            else:
                raise ValueError("Không tìm thấy JSON array trong response")
    except (json.JSONDecodeError, ValueError) as e:
        return {"status": "error", "message": f"Không parse được kết quả: {e}", "raw": response[:500]}

    _emit_activity("character", "extract", f"Trích xuất {len(characters)} nhân vật", project_id, video_id, "success")
    return {"status": "ok", "characters": characters}


# ─────────────────────────────────────────────
# Google Flow (Veo 3) — Playwright automation
# ─────────────────────────────────────────────
FLOW_BROWSER_DIR = Path.home() / ".video-factory-browser"
_playwright_instance = None
_browser_context = None
_browser_lock: Optional[asyncio.Lock] = None


def _get_browser_lock() -> asyncio.Lock:
    """Lazy-init lock trên event loop hiện tại."""
    global _browser_lock
    if _browser_lock is None:
        _browser_lock = asyncio.Lock()
    return _browser_lock


async def _get_flow_browser():
    """Lấy hoặc tạo persistent browser context cho Google Flow. Thread-safe với asyncio.Lock."""
    global _playwright_instance, _browser_context
    async with _get_browser_lock():
        if _browser_context is not None:
            try:
                test_page = await _browser_context.new_page()
                await test_page.close()
                return _browser_context
            except Exception:
                log.warning("⚠️ Browser context chết, tạo lại...")
                try:
                    await _browser_context.close()
                except Exception:
                    pass
                _browser_context = None
                # Kill playwright instance cũ luôn
                try:
                    if _playwright_instance:
                        await _playwright_instance.stop()
                except Exception:
                    pass
                _playwright_instance = None

        # Kill mọi Chrome process dùng user-data-dir này
        try:
            subprocess.run(["pkill", "-f", str(FLOW_BROWSER_DIR)], capture_output=True, timeout=5)
            import asyncio as _aio
            await _aio.sleep(1)
        except Exception:
            pass

        from playwright.async_api import async_playwright
        _playwright_instance = await async_playwright().start()

        # Xóa stale SingletonLock nếu không có Chrome process nào đang dùng user-data-dir này
        lock_file = FLOW_BROWSER_DIR / "SingletonLock"
        if lock_file.exists():
            try:
                result = subprocess.run(
                    ["pgrep", "-f", str(FLOW_BROWSER_DIR)],
                    capture_output=True, text=True, timeout=5,
                )
                chrome_running = bool(result.stdout.strip())
            except Exception:
                chrome_running = False
            if not chrome_running:
                lock_file.unlink(missing_ok=True)
                log.info("Đã xóa stale SingletonLock")

        FLOW_BROWSER_DIR.mkdir(parents=True, exist_ok=True)
        _browser_context = await _playwright_instance.chromium.launch_persistent_context(
            str(FLOW_BROWSER_DIR),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,900",
            ],
            viewport={"width": 1280, "height": 900},
            locale="vi-VN",
        )
        return _browser_context


async def _check_flow_login():
    """Kiểm tra đã đăng nhập Google Flow chưa. Trả về True/False."""
    try:
        ctx = await _get_flow_browser()
        pages = ctx.pages
        # Tìm page Flow đang mở
        for p in pages:
            if "flow.google.com" in p.url:
                # Kiểm tra có bị redirect sang login không
                if "accounts.google.com" in p.url:
                    return False
                return True
        # Mở page mới để check
        page = await ctx.new_page()
        try:
            await page.goto("https://flow.google.com", wait_until="networkidle", timeout=15000)
            current_url = page.url
            if "accounts.google.com" in current_url:
                # Đang ở trang login → chưa đăng nhập, giữ page mở để user login
                return False
            return True
        except Exception:
            return False
    except Exception:
        return False


@app.post("/api/flow-login")
async def flow_login():
    """Mở browser Flow để đăng nhập. User đăng nhập thủ công trong cửa sổ browser."""
    try:
        ctx = await _get_flow_browser()
        # Kiểm tra đã login chưa
        page = None
        for p in ctx.pages:
            if "flow.google.com" in p.url or "accounts.google.com" in p.url:
                page = p
                break
        if page is None:
            page = await ctx.new_page()
            await page.goto("https://flow.google.com", wait_until="networkidle", timeout=15000)

        current_url = page.url
        if "accounts.google.com" not in current_url and "flow.google.com" in current_url:
            return {"status": "ok", "logged_in": True, "message": "Đã đăng nhập Google Flow."}

        # Chưa login — browser đang mở trang đăng nhập, chờ user tự đăng nhập
        return {
            "status": "ok",
            "logged_in": False,
            "message": "Cửa sổ trình duyệt đã mở. Hãy đăng nhập Google trong cửa sổ đó, sau đó quay lại đây nhấn 'Tạo ảnh'.",
        }
    except Exception as e:
        raise HTTPException(500, f"Không mở được trình duyệt: {str(e)}")


@app.get("/api/flow-status")
async def flow_status():
    """Kiểm tra trạng thái đăng nhập Google Flow."""
    logged_in = await _check_flow_login()
    return {"logged_in": logged_in}


async def _flow_create_character(flow_project_id, char_name, visual_prompt):
    """Tạo nhân vật trên Google Flow và trả về ảnh + character ID."""
    ctx = await _get_flow_browser()
    page = await ctx.new_page()

    try:
        # 1. Navigate to character creation page
        url = f"https://flow.google.com/u/1/project/{flow_project_id}/character"
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # 2. Check if logged in
        if "accounts.google.com" in page.url:
            await page.close()
            raise Exception("NOT_LOGGED_IN")

        # Wait for description input to appear
        desc_input = page.locator('p').first
        try:
            await desc_input.wait_for(state="visible", timeout=10000)
        except Exception:
            if "accounts.google.com" in page.url:
                raise Exception("NOT_LOGGED_IN")
            raise Exception("Không tải được trang tạo nhân vật Flow.")

        # 3. Type character visual prompt
        await desc_input.click()
        await desc_input.fill(visual_prompt)

        # 4. Wait for "Bắt đầu tạo" to become enabled, then click
        submit_btn = page.get_by_role("button", name="Bắt đầu tạo")
        for _ in range(30):
            if await submit_btn.is_enabled():
                break
            await asyncio.sleep(0.5)
        else:
            raise Exception("Nút 'Bắt đầu tạo' không kích hoạt được.")
        await submit_btn.click()

        # 5. URL changes to include character ID
        await asyncio.sleep(3)
        current_url = page.url
        flow_char_id = None
        if "/character/" in current_url:
            parts = current_url.rstrip("/").split("/")
            if parts[-1] != "character":
                flow_char_id = parts[-1]

        # 6. Wait for generated portrait image (up to 3 minutes)
        generated_img = page.locator('img[alt="Hình ảnh nhân vật đã tạo"]')
        await generated_img.wait_for(state="visible", timeout=180000)
        await asyncio.sleep(2)

        # 7. Get image URL
        image_url = await generated_img.get_attribute("src")

        # 8. Download image via browser fetch (needs auth cookies)
        import base64
        image_base64 = await page.evaluate('''async (url) => {
            const resp = await fetch(url);
            const blob = await resp.blob();
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            });
        }''', image_url)
        _, b64_data = image_base64.split(',', 1)
        image_bytes = base64.b64decode(b64_data)

        # 9. Rename character on Flow
        try:
            name_input = page.get_by_role("textbox", name="Tên nhân vật")
            await name_input.click(click_count=3)
            await name_input.fill(char_name)
            await asyncio.sleep(0.5)
        except Exception:
            pass  # Không bắt buộc

        # 10. Click "Xong" to save
        try:
            done_btn = page.get_by_role("button", name="Xong")
            await done_btn.click()
            await asyncio.sleep(1)
        except Exception:
            pass

        return {
            "image_bytes": image_bytes,
            "image_url": image_url,
            "flow_character_id": flow_char_id,
            "page_url": current_url,
        }

    finally:
        await page.close()


@app.post("/api/generate-character-image/{project_id}/{video_id}/{character_id}")
async def generate_character_image(project_id: str, video_id: str, character_id: str):
    """Tạo ảnh nhân vật trên Google Flow (Veo 3) bằng Playwright."""
    import httpx

    # 1. Get character info from backend
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/characters/{character_id}")
        if resp.status_code != 200:
            raise HTTPException(404, "Không tìm thấy nhân vật.")
        character = resp.json()

    if not character.get("visual_prompt_base"):
        raise HTTPException(400, "Nhân vật chưa có visual_prompt_base.")

    # 2. Get flow_project_id từ video (fallback sang project)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}")
        video_data = resp.json() if resp.status_code == 200 else {}
    flow_project_id = video_data.get("flow_project_id")
    if not flow_project_id:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND}/api/projects/{project_id}")
            project = resp.json() if resp.status_code == 200 else {}
        flow_project_id = project.get("flow_project_id")
    if not flow_project_id:
        raise HTTPException(400, "Video/dự án chưa cấu hình Flow Project ID.")

    # 3. Build prompt with character name for Flow
    prompt = f"Front-facing portrait, medium shot, centered, looking directly at camera. {character['name']}. {character['visual_prompt_base']}"

    # 4. Automate Flow
    try:
        result = await _flow_create_character(flow_project_id, character["name"], prompt)
    except Exception as e:
        if "NOT_LOGGED_IN" in str(e):
            raise HTTPException(401, "FLOW_NOT_LOGGED_IN")
        raise HTTPException(500, f"Lỗi tạo ảnh: {str(e)}")

    # 5. Save image from browser download (scoped to video)
    image_path = None
    if result.get("image_bytes"):
        save_dir = PROJECTS_DIR / project_id / "videos" / video_id / "characters" / character_id
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / "reference.png"
        save_path.write_bytes(result["image_bytes"])
        image_path = f"/files/projects/{project_id}/videos/{video_id}/characters/{character_id}/reference.png"

    # 6. Update character in backend
    update_data = {}
    if image_path:
        update_data["reference_image_path"] = image_path
    if result.get("flow_character_id"):
        update_data["flow_character_id"] = result["flow_character_id"]

    if update_data:
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/characters/{character_id}",
                json=update_data,
            )

    return {
        "status": "ok",
        "image_path": image_path,
        "flow_character_id": result.get("flow_character_id"),
        "flow_url": result.get("page_url"),
    }


@app.post("/api/generate-all-character-images/{project_id}/{video_id}")
async def generate_all_character_images(project_id: str, video_id: str, mode: str = "missing"):
    """Tạo ảnh cho nhân vật trong video (background task). mode=missing: chưa có ảnh, mode=all: tất cả."""
    import httpx

    cancel_key = f"{project_id}::{video_id}::characters"

    # Reconnect nếu job đang chạy
    existing_jid = _find_running_bg_job("generate_chars", project_id)
    if existing_jid:
        return _sse_from_bg_job(BACKGROUND_JOBS[existing_jid])

    job_id = _start_job("character", "generate_chars", project_id, total=0)
    bg_job = BackgroundJob(job_id)
    BACKGROUND_JOBS[job_id] = bg_job

    async def work():
        cancel_flag = asyncio.Event()
        CANCEL_FLAGS[cancel_key] = cancel_flag
        try:
            # 1. Get all characters for this video
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/characters")
                characters = resp.json() if resp.status_code == 200 else []

            if not characters:
                yield {"type": "all_done", "message": "Không có nhân vật nào."}
                return

            # 2. Get flow_project_id từ video (fallback sang project)
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}")
                video_data = resp.json() if resp.status_code == 200 else {}
            flow_project_id = video_data.get("flow_project_id")
            if not flow_project_id:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{BACKEND}/api/projects/{project_id}")
                    project = resp.json() if resp.status_code == 200 else {}
                flow_project_id = project.get("flow_project_id")
            if not flow_project_id:
                yield {"type": "error", "message": "Video/dự án chưa cấu hình Flow Project ID."}
                return

            # 3. Filter characters
            if mode == "missing":
                target_chars = [c for c in characters if c.get("visual_prompt_base") and not c.get("reference_image_path")]
            else:
                target_chars = [c for c in characters if c.get("visual_prompt_base")]

            total = len(target_chars)
            if total == 0:
                yield {"type": "all_done", "message": "Không có nhân vật nào cần tạo ảnh."}
                return

            _update_job(job_id, 0, total=total)

            CONCURRENT = 3
            yield {"type": "status", "message": f"Bắt đầu tạo ảnh {total} nhân vật ({CONCURRENT} tab song song)...", "total": total}

            results_queue = asyncio.Queue()

            async def _generate_one(char):
                char_id = char["id"]
                char_name = char["name"]

                if cancel_flag.is_set():
                    await results_queue.put({"type": "char_done", "character_id": char_id, "name": char_name, "status": "skipped", "message": "Đã dừng"})
                    return

                try:
                    prompt = f"Front-facing portrait, medium shot, centered, looking directly at camera. {char_name}. {char['visual_prompt_base']}"
                    result = await _flow_create_character(flow_project_id, char_name, prompt)

                    # Save image (scoped to video)
                    image_path = None
                    if result.get("image_bytes"):
                        save_dir = PROJECTS_DIR / project_id / "videos" / video_id / "characters" / char_id
                        save_dir.mkdir(parents=True, exist_ok=True)
                        save_path = save_dir / "reference.png"
                        save_path.write_bytes(result["image_bytes"])
                        image_path = f"/files/projects/{project_id}/videos/{video_id}/characters/{char_id}/reference.png"

                    # Update backend
                    update_data = {}
                    if image_path:
                        update_data["reference_image_path"] = image_path
                    if result.get("flow_character_id"):
                        update_data["flow_character_id"] = result["flow_character_id"]
                    if update_data:
                        async with httpx.AsyncClient() as client:
                            await client.put(
                                f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/characters/{char_id}",
                                json=update_data,
                            )

                    await results_queue.put({"type": "char_done", "character_id": char_id, "name": char_name, "status": "ok", "image_path": image_path})
                except Exception as e:
                    error_msg = str(e)
                    if "NOT_LOGGED_IN" in error_msg:
                        await results_queue.put({"type": "error", "message": "Chưa đăng nhập Google Flow."})
                    else:
                        await results_queue.put({"type": "char_done", "character_id": char_id, "name": char_name, "status": "error", "message": error_msg})

            sem = asyncio.Semaphore(CONCURRENT)

            async def _worker(char):
                async with sem:
                    if not cancel_flag.is_set():
                        await _generate_one(char)
                    else:
                        await results_queue.put({"type": "char_done", "character_id": char["id"], "name": char["name"], "status": "skipped", "message": "Đã dừng"})

            tasks = [asyncio.create_task(_worker(c)) for c in target_chars]

            done = 0
            cancelled = False
            while done < total:
                if cancel_flag.is_set() and not cancelled:
                    cancelled = True
                    for t in tasks:
                        t.cancel()
                    yield {"type": "stopped", "message": f"Đã dừng — {done}/{total} nhân vật hoàn thành."}
                    _finish_job(job_id, "stopped", f"Dừng tại {done}/{total}")
                    break

                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=360)
                except asyncio.TimeoutError:
                    yield {"type": "error", "message": "Timeout chờ kết quả quá lâu."}
                    break

                if result.get("type") == "error":
                    yield result
                    for t in tasks:
                        t.cancel()
                    break

                if result.get("status") == "skipped":
                    done += 1
                    continue

                done += 1
                result["progress"] = f"{done}/{total}"
                _update_job(job_id, done)
                yield result

            await asyncio.gather(*tasks, return_exceptions=True)
            if not cancelled:
                _finish_job(job_id, "done", f"Hoàn thành {done}/{total} nhân vật")
            yield {"type": "all_done", "message": f"Hoàn thành {done}/{total} nhân vật."}
        finally:
            CANCEL_FLAGS.pop(cancel_key, None)

    asyncio.create_task(_run_bg(bg_job, job_id, work()))
    return _sse_from_bg_job(bg_job)


# ─────────────────────────────────────────────
# Scene Asset Generation via Google Flow (Veo 3)
# ─────────────────────────────────────────────

async def _flow_add_characters(page, character_names: List[str]):
    """Thêm nhân vật vào prompt qua UI Flow: + → Nhân vật → chọn tên → Thêm vào câu lệnh."""
    for name in character_names:
        try:
            # 1. Bấm nút "+" (cạnh "Tác nhân" dưới ô input prompt)
            #    Nút + nằm gần nút "Tác nhân" ở thanh dưới cùng
            plus_clicked = await page.evaluate("""() => {
                // Tìm nút/element chứa text "Tác nhân"
                const tacNhan = Array.from(document.querySelectorAll('button, span, div')).find(
                    el => el.textContent.trim() === 'Tác nhân'
                );
                if (tacNhan) {
                    // Tìm nút + gần "Tác nhân" (sibling hoặc trong cùng parent)
                    const parent = tacNhan.closest('div, form, footer, section') || tacNhan.parentElement;
                    if (parent) {
                        const plusBtn = parent.querySelector('button:first-child') ||
                                       parent.previousElementSibling;
                        if (plusBtn && plusBtn.tagName === 'BUTTON') {
                            plusBtn.click(); return true;
                        }
                        // Tìm tất cả button trong parent, click cái có icon add hoặc text +
                        const btns = parent.querySelectorAll('button');
                        for (const b of btns) {
                            const icon = b.querySelector('[data-icon="add"]');
                            if (icon || b.textContent.trim() === '+' || b.textContent.trim() === '') {
                                b.click(); return true;
                            }
                        }
                    }
                }
                // Fallback: tìm button có icon add ở cuối trang
                const allBtns = Array.from(document.querySelectorAll('button'));
                for (const b of allBtns.reverse()) {
                    if (b.querySelector('[data-icon="add"]') || b.getAttribute('aria-label')?.includes('add')) {
                        b.click(); return true;
                    }
                }
                return false;
            }""")
            if plus_clicked:
                await asyncio.sleep(1)
                log.info(f"✅ Bấm nút + để thêm nhân vật '{name}'")
            else:
                log.warning(f"⚠️ Không tìm được nút + để thêm nhân vật {name}")
                continue

            # 2. Bấm tab "Nhân vật" TRONG popup (không phải nav chính)
            #    Popup có các tab: Tất cả, Hình ảnh, Video, Giọng nói, Nhân vật, Hình đại diện, Tệp tải lên
            tab_clicked = await page.evaluate("""() => {
                // Tìm popup/panel vừa mở — thường là dialog, panel, hoặc div mới xuất hiện
                // Popup chứa nhiều tab: "Tất cả", "Hình ảnh", "Video", "Giọng nói", "Nhân vật"
                const allElements = document.querySelectorAll('button, a, div[role="tab"], span, li');

                // Tìm element "Nhân vật" gần element "Tất cả" hoặc "Giọng nói" (chỉ có trong popup)
                let popup = null;
                for (const el of allElements) {
                    if (el.textContent.trim() === 'Tất cả' || el.textContent.trim() === 'Giọng nói') {
                        popup = el.closest('div, nav, aside, section, [role="dialog"], [role="menu"]');
                        break;
                    }
                }

                if (popup) {
                    // Tìm "Nhân vật" trong popup
                    const tabs = popup.querySelectorAll('button, a, div[role="tab"], span, li');
                    for (const el of tabs) {
                        if (el.textContent.trim() === 'Nhân vật' && el.offsetParent !== null) {
                            el.click(); return true;
                        }
                    }
                }

                // Fallback: tìm "Nhân vật" gần "Giọng nói" (cùng parent)
                for (const el of allElements) {
                    if (el.textContent.trim() === 'Giọng nói' && el.offsetParent !== null) {
                        const parent = el.parentElement;
                        if (parent) {
                            const siblings = parent.querySelectorAll('button, a, div[role="tab"], span, li');
                            for (const sib of siblings) {
                                if (sib.textContent.trim() === 'Nhân vật') {
                                    sib.click(); return true;
                                }
                            }
                        }
                    }
                }
                return false;
            }""")
            if tab_clicked:
                await asyncio.sleep(1)
                log.info("✅ Chọn tab Nhân vật")
            else:
                log.warning("⚠️ Không tìm được tab Nhân vật")

            # 3. Chọn nhân vật theo tên (fuzzy match — tìm element chứa từ khóa chính)
            char_clicked = await page.evaluate("""(charName) => {
                // Tách từ khóa chính từ tên (bỏ dấu ngoặc, tuổi, mô tả phụ)
                const keywords = charName.replace(/[()（）]/g, ' ').split(/[\s,–—-]+/).filter(w => w.length > 1);

                // Tìm nhân vật có label "Nhân vật" trong danh sách
                const items = document.querySelectorAll('div, button, li, a, span');
                let bestMatch = null;
                let bestScore = 0;

                for (const el of items) {
                    if (el.offsetParent === null) continue;
                    const text = el.textContent.trim();
                    if (!text || text.length > 100) continue;

                    // Chỉ xét element có text "Nhân vật" (sublabel) hoặc trong danh sách nhân vật
                    const hasCharLabel = text.includes('Nhân vật') || el.closest('[role="listitem"], [role="option"]');
                    if (!hasCharLabel && el.parentElement && !el.parentElement.textContent.includes('Nhân vật')) continue;

                    // Đếm từ khóa match
                    let score = 0;
                    for (const kw of keywords) {
                        if (text.toLowerCase().includes(kw.toLowerCase())) score++;
                    }

                    // Exact match
                    if (text.includes(charName)) score += 10;

                    if (score > bestScore) {
                        bestScore = score;
                        bestMatch = el;
                    }
                }

                if (bestMatch && bestScore >= Math.max(1, Math.floor(keywords.length / 2))) {
                    bestMatch.click();
                    return true;
                }
                return false;
            }""", name)
            if char_clicked:
                await asyncio.sleep(1)
                log.info(f"✅ Chọn nhân vật '{name}'")
            else:
                log.warning(f"⚠️ Không tìm thấy nhân vật '{name}' trên Flow")
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
                continue

            # 4. Bấm "Thêm vào câu lệnh"
            add_clicked = await page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const b of btns) {
                    if (b.textContent.trim().includes('Thêm vào câu lệnh') && b.offsetParent !== null) {
                        b.click(); return true;
                    }
                }
                return false;
            }""")
            if add_clicked:
                await asyncio.sleep(0.5)
                log.info(f"✅ Đã thêm nhân vật '{name}' vào prompt")
            else:
                log.warning(f"⚠️ Không tìm được nút 'Thêm vào câu lệnh' cho {name}")
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
        except Exception as e:
            log.warning(f"⚠️ Lỗi thêm nhân vật '{name}': {e}")
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            await asyncio.sleep(0.3)


async def _flow_generate_asset(flow_project_id: str, prompt: str, visual_type: str = "image", duration: int = 8, is_short: bool = False, flow_characters: Optional[List[str]] = None):
    """Tạo ảnh/video trên Google Flow từ prompt. Trả về bytes + metadata."""
    ctx = await _get_flow_browser()
    page = await ctx.new_page()

    try:
        # 1. Navigate to Flow project page
        url = f"https://flow.google.com/u/1/project/{flow_project_id}"
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # 2. Check if logged in
        if "accounts.google.com" in page.url:
            await page.close()
            raise Exception("NOT_LOGGED_IN")

        # 3. Settings (Hình ảnh/Video, resolution...) — user chọn sẵn trên Flow
        #    Code KHÔNG tự chọn settings. User bấm nút "Tạo ảnh" hoặc "Tạo video" riêng.
        log.info(f"{'🎬 Video' if visual_type == 'video' else '🖼️ Hình ảnh'} — user đã chọn settings sẵn trên Flow")

        # 3.5. Thêm nhân vật vào prompt qua UI
        if flow_characters:
            await _flow_add_characters(page, flow_characters)

        # 4. Lưu danh sách media-id hiện có trước khi tạo
        before_ids = set(await page.evaluate(
            "() => Array.from(document.querySelectorAll('[data-media-id]')).map(el => el.getAttribute('data-media-id'))"
        ))

        # 5. Find prompt input and enter prompt
        #    Flow dùng contenteditable div/p — thử nhiều selector
        prompt_filled = False
        for selector in [
            '[contenteditable="true"]',
            'p[contenteditable]',
            '[role="textbox"]',
            'textarea',
        ]:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    await el.wait_for(state="visible", timeout=5000)
                    await el.click()
                    await el.fill(prompt)
                    prompt_filled = True
                    break
            except Exception:
                continue

        if not prompt_filled:
            # Fallback: tìm element có placeholder "Bạn muốn tạo những gì?"
            try:
                el = page.get_by_placeholder("Bạn muốn tạo")
                if await el.count() > 0:
                    await el.click()
                    await el.fill(prompt)
                    prompt_filled = True
            except Exception:
                pass

        if not prompt_filled:
            if "accounts.google.com" in page.url:
                raise Exception("NOT_LOGGED_IN")
            raise Exception("Không tìm được ô nhập prompt trên Flow.")

        # 6. Submit + retry loop (tối đa 5 lần nếu Flow báo lỗi)
        MAX_RETRIES = 5
        new_media_id = None

        for attempt in range(1, MAX_RETRIES + 1):
            if attempt == 1:
                # Lần đầu: bấm "Bắt đầu tạo"
                submit_btn = page.get_by_role("button", name="Bắt đầu tạo")
                for _ in range(30):
                    if await submit_btn.is_enabled():
                        break
                    await asyncio.sleep(0.5)
                else:
                    raise Exception("Nút 'Bắt đầu tạo' không kích hoạt được.")
                await submit_btn.click()
            else:
                # Retry: tìm nút retry (↻) trên UI Flow
                retry_clicked = False
                for retry_selector in [
                    'button[aria-label*="retry" i]',
                    'button[aria-label*="Thử lại" i]',
                    'button[aria-label*="regenerate" i]',
                    'button[aria-label*="Tạo lại" i]',
                ]:
                    try:
                        btn = page.locator(retry_selector).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click()
                            retry_clicked = True
                            break
                    except Exception:
                        continue

                if not retry_clicked:
                    # Fallback: tìm nút có icon refresh/retry gần "Không thành công"
                    try:
                        # Tìm tất cả button, click cái đầu tiên có icon reload
                        retry_clicked = await page.evaluate("""() => {
                            const btns = document.querySelectorAll('button');
                            for (const btn of btns) {
                                const text = btn.textContent || '';
                                const ariaLabel = btn.getAttribute('aria-label') || '';
                                const icon = btn.querySelector('[data-icon="refresh"], [data-icon="replay"], [data-icon="autorenew"]');
                                if (icon || text.includes('↻') || ariaLabel.includes('retry') || ariaLabel.includes('Tạo lại')) {
                                    btn.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                    except Exception:
                        retry_clicked = False

                if not retry_clicked:
                    # Last resort: bấm "Bắt đầu tạo" lại
                    submit_btn = page.get_by_role("button", name="Bắt đầu tạo")
                    try:
                        if await submit_btn.is_enabled():
                            await submit_btn.click()
                            retry_clicked = True
                    except Exception:
                        pass

                if not retry_clicked:
                    raise Exception(f"Không tìm được nút retry sau lỗi Flow (lần {attempt}).")

            # Đếm số lỗi "Không thành công" hiện tại TRƯỚC khi bấm
            error_count_before = await page.evaluate("""() => {
                return (document.body.innerText.match(/Không thành công/g) || []).length;
            }""")

            log.info(f"🎬 Flow: bấm tạo (lần {attempt}/{MAX_RETRIES}, errors_before={error_count_before})")

            # Chờ Flow bắt đầu xử lý
            await asyncio.sleep(10)

            # Chờ kết quả: media mới HOẶC lỗi MỚI "Không thành công"
            timeout_s = 300
            failed = False
            for tick in range(timeout_s):
                await asyncio.sleep(2)

                # Check media mới trước (ưu tiên thành công)
                # Tìm cả data-media-id VÀ video/img mới xuất hiện
                new_media = await page.evaluate("""(beforeIds) => {
                    // Check data-media-id elements
                    const mediaEls = document.querySelectorAll('[data-media-id]');
                    for (const el of mediaEls) {
                        const mid = el.getAttribute('data-media-id');
                        if (mid && !beforeIds.includes(mid)) {
                            let src = el.src || el.currentSrc || '';
                            if (!src) {
                                const child = el.querySelector('img, video, source');
                                if (child) src = child.src || child.currentSrc || '';
                            }
                            if (!src && el.poster) src = el.poster;
                            return { mediaId: mid, src: src, tagName: el.tagName.toLowerCase() };
                        }
                    }
                    // Check video tags (Flow video có thể không có data-media-id)
                    const videos = document.querySelectorAll('video');
                    for (const v of videos) {
                        const src = v.src || v.currentSrc || '';
                        const poster = v.poster || '';
                        if (src && !beforeIds.includes(src)) {
                            return { mediaId: src, src: src, tagName: 'video' };
                        }
                        if (poster && !beforeIds.includes(poster)) {
                            return { mediaId: poster, src: poster, tagName: 'video-poster' };
                        }
                    }
                    return null;
                }""", list(before_ids))
                if new_media:
                    new_media_id = new_media.get("mediaId")
                    break

                # Check lỗi MỚI — so sánh số lượng "Không thành công" với trước khi bấm
                if tick >= 3:
                    error_count_now = await page.evaluate("""() => {
                        return (document.body.innerText.match(/Không thành công/g) || []).length;
                    }""")
                    if error_count_now > error_count_before:
                        log.warning(f"⚠️ Flow báo lỗi MỚI (lần {attempt}/{MAX_RETRIES}, errors: {error_count_before}→{error_count_now})")
                        failed = True
                        break
            else:
                raise Exception(f"Timeout — Flow không tạo được media (lần {attempt}).")

            if new_media_id:
                if attempt > 1:
                    log.info(f"✅ Flow thành công ở lần thử {attempt}")
                break

            if failed and attempt < MAX_RETRIES:
                await asyncio.sleep(3)
                continue

        if not new_media_id:
            raise Exception(f"Flow thất bại sau {MAX_RETRIES} lần thử.")

        await asyncio.sleep(3)

        # 7. Get URL of the new media
        #    new_media đã có thông tin từ detect loop, nhưng double-check
        media_info = new_media if new_media else await page.evaluate("""(mediaId) => {
            const el = document.querySelector(`[data-media-id="${mediaId}"]`);
            if (!el) {
                // Tìm video tag
                const v = document.querySelector('video');
                if (v && (v.src || v.currentSrc)) return { src: v.src || v.currentSrc, mediaId: mediaId, tagName: 'video' };
                return null;
            }
            let src = el.src || el.currentSrc || '';
            if (!src) {
                const child = el.querySelector('img, video, source');
                if (child) src = child.src || child.currentSrc || '';
            }
            if (!src && el.poster) src = el.poster;
            return { src: src, mediaId: mediaId, tagName: el.tagName.toLowerCase() };
        }""", new_media_id)

        if not media_info or not media_info.get("src"):
            raise Exception("Không lấy được URL media sau khi tạo.")

        # 8. Download media
        import base64
        media_src = media_info["src"]
        log.info(f"📥 Download media: {media_src[:100]}... (tag: {media_info.get('tagName')})")

        media_base64 = await page.evaluate('''async (url) => {
            try {
                // Cách 1: fetch trực tiếp
                const resp = await fetch(url, { credentials: 'include' });
                if (resp.ok) {
                    const blob = await resp.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }
            } catch(e) {}

            try {
                // Cách 2: nếu là video element, dùng canvas capture
                const video = document.querySelector(`video[src="${url}"], video[currentSrc="${url}"]`)
                             || document.querySelector('video');
                if (video && video.src) {
                    // Thử fetch video src
                    const resp = await fetch(video.src, { credentials: 'include' });
                    if (resp.ok) {
                        const blob = await resp.blob();
                        return new Promise((resolve) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        });
                    }
                }
            } catch(e) {}

            try {
                // Cách 3: tìm source tag trong video
                const source = document.querySelector('video source');
                if (source && source.src) {
                    const resp = await fetch(source.src, { credentials: 'include' });
                    if (resp.ok) {
                        const blob = await resp.blob();
                        return new Promise((resolve) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        });
                    }
                }
            } catch(e) {}

            return null;
        }''', media_src)

        if not media_base64:
            # Cách 4: Fallback — dùng Playwright download
            try:
                resp = await page.request.get(media_src)
                if resp.ok:
                    media_bytes = await resp.body()
                    return {
                        "media_bytes": media_bytes,
                        "media_url": media_src,
                        "media_id": media_info.get("mediaId"),
                        "visual_type": visual_type,
                    }
            except Exception:
                pass
            raise Exception(f"Không tải được media: {media_src[:200]}")

        _, b64_data = media_base64.split(',', 1)
        media_bytes = base64.b64decode(b64_data)

        return {
            "media_bytes": media_bytes,
            "media_url": media_src,
            "media_id": media_info.get("mediaId"),
            "visual_type": visual_type,
        }

    finally:
        await page.close()


@app.post("/api/generate-scene-asset/{project_id}/{video_id}/{scene_number}")
async def generate_scene_asset(project_id: str, video_id: str, scene_number: int):
    """Tạo ảnh/video cho 1 cảnh trên Google Flow."""
    import httpx

    # 1. Get scene info (lấy tất cả scenes rồi filter vì backend không có GET single scene)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/scenes")
        if resp.status_code != 200:
            raise HTTPException(404, f"Không tìm thấy danh sách cảnh.")
        all_scenes = resp.json()
    scene = next((s for s in all_scenes if s.get("scene_number") == scene_number), None)
    if not scene:
        raise HTTPException(404, f"Không tìm thấy cảnh {scene_number}.")

    if not scene.get("veo3_prompt"):
        raise HTTPException(400, f"Cảnh {scene_number} chưa có prompt.")

    # 2. Get flow_project_id từ video (fallback sang project)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}")
        video_data = resp.json() if resp.status_code == 200 else {}
    flow_project_id = video_data.get("flow_project_id")
    if not flow_project_id:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND}/api/projects/{project_id}")
            project = resp.json() if resp.status_code == 200 else {}
        flow_project_id = project.get("flow_project_id")
    if not flow_project_id:
        raise HTTPException(400, "Video/dự án chưa cấu hình Flow Project ID.")

    # 3. Generate via Flow
    visual_type = scene.get("visual_type", "image")
    scene_duration = int(scene.get("timestamp_end", 0) - scene.get("timestamp_start", 0))
    flow_duration = next((d for d in [4, 6, 8, 10] if d >= scene_duration), 10) if scene_duration > 0 else 8
    _is_short = "short" in video_id.lower()
    _flow_chars = scene.get("flow_characters", [])
    try:
        result = await _flow_generate_asset(flow_project_id, scene["veo3_prompt"], visual_type, duration=flow_duration, is_short=_is_short, flow_characters=_flow_chars)
    except Exception as e:
        if "NOT_LOGGED_IN" in str(e):
            raise HTTPException(401, "Chưa đăng nhập Google Flow. Vui lòng đăng nhập trước.")
        raise HTTPException(500, f"Lỗi tạo asset: {str(e)}")

    # 4. Save asset file
    ext = "mp4" if visual_type == "video" else "jpg"
    assets_dir = PROJECTS_DIR / project_id / "videos" / video_id / "assets"
    sub_dir = assets_dir / ("videos" if visual_type == "video" else "images")
    sub_dir.mkdir(parents=True, exist_ok=True)

    # Find next version
    pattern = f"scene_{scene_number:03d}_v*"
    existing = sorted(sub_dir.glob(f"{pattern}.{ext}"))
    next_v = 1
    if existing:
        last = existing[-1].stem
        next_v = int(last.split("_v")[-1]) + 1

    save_path = sub_dir / f"scene_{scene_number:03d}_v{next_v}.{ext}"
    save_path.write_bytes(result["media_bytes"])

    # 5. Update scene in backend
    asset_rel_path = str(save_path)
    async with httpx.AsyncClient() as client:
        await client.put(
            f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/scenes/{scene_number}",
            json={"asset_path": asset_rel_path, "asset_version": next_v, "status": "review"},
        )

    return {
        "status": "ok",
        "scene_number": scene_number,
        "asset_path": f"/files/projects/{project_id}/videos/{video_id}/assets/{'videos' if visual_type == 'video' else 'images'}/scene_{scene_number:03d}_v{next_v}.{ext}",
        "version": next_v,
    }


@app.post("/api/generate-scene-assets/{project_id}/{video_id}")
async def generate_scene_assets_bulk(project_id: str, video_id: str, mode: str = "missing", scenes_filter: str = "", visual_type_filter: str = ""):
    """Tạo ảnh/video cho nhiều cảnh. mode=missing|all, scenes_filter=1,2,5, visual_type_filter=image|video."""
    import httpx

    cancel_key = f"{project_id}::{video_id}::assets"

    # Reconnect nếu job đang chạy
    existing_jid = _find_running_bg_job("generate_assets", project_id, video_id)
    if existing_jid:
        return _sse_from_bg_job(BACKGROUND_JOBS[existing_jid])

    job_id = _start_job("asset", "generate_assets", project_id, video_id, total=0)
    bg_job = BackgroundJob(job_id)
    BACKGROUND_JOBS[job_id] = bg_job

    async def work():
        cancel_flag = asyncio.Event()
        CANCEL_FLAGS[cancel_key] = cancel_flag
        try:
            # 1. Get all scenes
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/scenes")
                if resp.status_code != 200:
                    yield {"type": "error", "message": "Không lấy được danh sách cảnh."}
                    return
                scenes = resp.json()

            # 2. Get flow_project_id từ video (fallback sang project)
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BACKEND}/api/projects/{project_id}/videos/{video_id}")
                video_data = resp.json() if resp.status_code == 200 else {}
            flow_project_id = video_data.get("flow_project_id")
            if not flow_project_id:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{BACKEND}/api/projects/{project_id}")
                    project = resp.json() if resp.status_code == 200 else {}
                flow_project_id = project.get("flow_project_id")
            if not flow_project_id:
                yield {"type": "error", "message": "Video/dự án chưa cấu hình Flow Project ID."}
                return

            # 3. Filter scenes
            # Nếu có scenes_filter, chỉ lấy các scene numbers được chỉ định
            if scenes_filter:
                try:
                    allowed_nums = {int(x.strip()) for x in scenes_filter.split(",") if x.strip()}
                except ValueError:
                    allowed_nums = set()
                scenes = [s for s in scenes if s.get("scene_number") in allowed_nums]

            # Filter theo visual_type (image hoặc video)
            if visual_type_filter:
                scenes = [s for s in scenes if s.get("visual_type") == visual_type_filter]

            if mode == "missing":
                target_scenes = [s for s in scenes if s.get("veo3_prompt") and (not s.get("asset_path") or s.get("status") in ("pending", "redo"))]
            else:
                target_scenes = [s for s in scenes if s.get("veo3_prompt")]

            total = len(target_scenes)
            if total == 0:
                yield {"type": "all_done", "message": "Không có cảnh nào cần tạo."}
                return

            _update_job(job_id, 0, total=total)

            CONCURRENT = 3
            yield {"type": "status", "message": f"Bắt đầu tạo {total} cảnh ({CONCURRENT} tab song song)...", "total": total}

            results_queue = asyncio.Queue()

            async def _generate_one(scene):
                sn = scene["scene_number"]
                if cancel_flag.is_set():
                    await results_queue.put({"type": "scene_done", "scene_number": sn, "status": "skipped", "message": "Đã dừng"})
                    return

                visual_type = scene.get("visual_type", "image")
                # Tính duration từ timestamps (cho video)
                scene_duration = int(scene.get("timestamp_end", 0) - scene.get("timestamp_start", 0))
                flow_duration = next((d for d in [4, 6, 8, 10] if d >= scene_duration), 10) if scene_duration > 0 else 8
                _is_short = "short" in video_id.lower()
                _flow_chars = scene.get("flow_characters", [])
                try:
                    result = await _flow_generate_asset(flow_project_id, scene["veo3_prompt"], visual_type, duration=flow_duration, is_short=_is_short, flow_characters=_flow_chars)

                    ext = "mp4" if visual_type == "video" else "jpg"
                    assets_dir = PROJECTS_DIR / project_id / "videos" / video_id / "assets"
                    sub_dir = assets_dir / ("videos" if visual_type == "video" else "images")
                    sub_dir.mkdir(parents=True, exist_ok=True)

                    existing = sorted(sub_dir.glob(f"scene_{sn:03d}_v*.{ext}"))
                    next_v = 1
                    if existing:
                        next_v = int(existing[-1].stem.split("_v")[-1]) + 1

                    save_path = sub_dir / f"scene_{sn:03d}_v{next_v}.{ext}"
                    save_path.write_bytes(result["media_bytes"])

                    async with httpx.AsyncClient() as client:
                        await client.put(
                            f"{BACKEND}/api/projects/{project_id}/videos/{video_id}/scenes/{sn}",
                            json={"asset_path": str(save_path), "asset_version": next_v, "status": "review"},
                        )

                    asset_url = f"/api/projects/{project_id}/videos/{video_id}/scenes/{sn}/asset"
                    await results_queue.put({"type": "scene_done", "scene_number": sn, "status": "ok", "asset_path": asset_url, "version": next_v})
                except Exception as e:
                    error_msg = str(e)
                    if "NOT_LOGGED_IN" in error_msg:
                        await results_queue.put({"type": "error", "message": "Chưa đăng nhập Google Flow."})
                    else:
                        _append_gen_error(project_id, video_id, {
                            "scene_number": sn,
                            "visual_type": visual_type,
                            "error": error_msg,
                            "timestamp": datetime.now().isoformat(),
                        })
                        await results_queue.put({"type": "scene_done", "scene_number": sn, "status": "error", "message": error_msg})

            sem = asyncio.Semaphore(CONCURRENT)

            async def _worker(scene):
                async with sem:
                    if not cancel_flag.is_set():
                        await _generate_one(scene)
                    else:
                        await results_queue.put({"type": "scene_done", "scene_number": scene["scene_number"], "status": "skipped", "message": "Đã dừng"})

            tasks = [asyncio.create_task(_worker(s)) for s in target_scenes]

            done = 0
            cancelled = False
            while done < total:
                if cancel_flag.is_set() and not cancelled:
                    cancelled = True
                    for t in tasks:
                        t.cancel()
                    yield {"type": "stopped", "message": f"Đã dừng — {done}/{total} cảnh hoàn thành."}
                    _finish_job(job_id, "stopped", f"Dừng tại {done}/{total}")
                    break

                try:
                    result = await asyncio.wait_for(results_queue.get(), timeout=360)
                except asyncio.TimeoutError:
                    yield {"type": "error", "message": "Timeout chờ kết quả quá lâu."}
                    break

                if result.get("type") == "error":
                    yield result
                    for t in tasks:
                        t.cancel()
                    break

                if result.get("status") == "skipped":
                    done += 1
                    continue

                done += 1
                result["progress"] = f"{done}/{total}"
                _update_job(job_id, done)
                yield result

            await asyncio.gather(*tasks, return_exceptions=True)
            if not cancelled:
                _finish_job(job_id, "done", f"Hoàn thành {done}/{total} cảnh")
            yield {"type": "all_done", "message": f"Hoàn thành {done}/{total} cảnh."}
        finally:
            CANCEL_FLAGS.pop(cancel_key, None)

    asyncio.create_task(_run_bg(bg_job, job_id, work()))
    return _sse_from_bg_job(bg_job)



# ── Error log helpers ──────────────────────────────────────────────

def _gen_log_path(project_id: str, video_id: str) -> Path:
    return PROJECTS_DIR / project_id / "videos" / video_id / "generation_errors.json"

def _append_gen_error(project_id: str, video_id: str, entry: dict):
    """Append an error entry to the generation error log."""
    log_path = _gen_log_path(project_id, video_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    errors = []
    if log_path.exists():
        try:
            errors = json.loads(log_path.read_text("utf-8"))
        except Exception:
            errors = []
    errors.append(entry)
    log_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2), "utf-8")

@app.get("/api/generation-errors/{project_id}/{video_id}")
async def get_generation_errors(project_id: str, video_id: str):
    log_path = _gen_log_path(project_id, video_id)
    if not log_path.exists():
        return {"errors": []}
    try:
        return {"errors": json.loads(log_path.read_text("utf-8"))}
    except Exception:
        return {"errors": []}

@app.delete("/api/generation-errors/{project_id}/{video_id}")
async def clear_generation_errors(project_id: str, video_id: str):
    log_path = _gen_log_path(project_id, video_id)
    if log_path.exists():
        log_path.unlink()
    return {"status": "ok"}


@app.post("/api/cancel-generation/{project_id}/{video_id}")
async def cancel_generation(project_id: str, video_id: str):
    """Dừng batch job đang chạy cho video này (prompt hoặc asset)."""
    cancelled = False
    for key in [f"{project_id}::{video_id}", f"{project_id}::{video_id}::assets"]:
        flag = CANCEL_FLAGS.get(key)
        if flag:
            flag.set()
            cancelled = True
    if cancelled:
        return {"status": "ok", "message": "Đã gửi tín hiệu dừng."}
    return {"status": "ok", "message": "Không có job nào đang chạy."}


@app.post("/api/cancel-character-generation/{project_id}/{video_id}")
async def cancel_character_generation(project_id: str, video_id: str):
    """Dừng batch job tạo ảnh nhân vật."""
    key = f"{project_id}::{video_id}::characters"
    flag = CANCEL_FLAGS.get(key)
    if flag:
        flag.set()
        return {"status": "ok", "message": "Đã gửi tín hiệu dừng."}
    return {"status": "ok", "message": "Không có job nào đang chạy."}


@app.post("/api/build-capcut/{project_id}/{video_id}")
async def build_capcut(project_id: str, video_id: str, is_short: bool = False):
    """Tạo project CapCut từ scenes đã có asset."""
    from capcut_builder import build_capcut_project

    video_dir = PROJECTS_DIR / project_id / "videos" / video_id
    if not video_dir.exists():
        raise HTTPException(404, "Video not found")

    # Đọc scenes từ DB qua backend API
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://localhost:8000/api/projects/{project_id}/videos/{video_id}/scenes?is_short={str(is_short).lower()}") as resp:
            if resp.status != 200:
                raise HTTPException(500, "Không lấy được danh sách cảnh từ backend")
            scenes_data = await resp.json()

        async with session.get(f"http://localhost:8000/api/projects/{project_id}/videos/{video_id}") as resp:
            video_data = await resp.json() if resp.status == 200 else {}

    if not scenes_data:
        return {"status": "error", "message": "Chưa có cảnh nào."}

    # Build scenes list cho capcut_builder
    scenes_for_capcut = []
    for s in scenes_data:
        asset_path = s.get("asset_path")
        if not asset_path:
            continue
        # asset_path trong DB là relative, resolve full path
        asset_base = video_dir / "shorts" / "assets" if is_short else video_dir / "assets"
        full_asset_path = str(asset_base / Path(asset_path).name)
        if not Path(full_asset_path).exists():
            # Thử path trực tiếp
            if Path(asset_path).exists():
                full_asset_path = asset_path
            else:
                continue

        scenes_for_capcut.append({
            "scene_number": s["scene_number"],
            "timestamp_start": s.get("timestamp_start", 0),
            "timestamp_end": s.get("timestamp_end", 0),
            "asset_path": full_asset_path,
            "visual_type": s.get("visual_type", "image"),
        })

    if not scenes_for_capcut:
        return {"status": "error", "message": "Không có cảnh nào có ảnh/video. Tạo ảnh trước."}

    # Audio path
    audio_path = None
    audio_dir = (video_dir / "shorts" / "audio") if is_short else (video_dir / "audio")
    if audio_dir.exists():
        for ext in ["*.mp3", "*.wav", "*.m4a", "*.aac"]:
            files = list(audio_dir.glob(ext))
            if files:
                audio_path = str(files[0])
                break

    # Tên project
    video_title = video_data.get("title", video_id)
    project_name = f"{project_id} - {video_title}"

    # Canvas dimensions based on format
    if is_short:
        canvas_w, canvas_h = 1080, 1920
    else:
        canvas_w, canvas_h = 1920, 1080

    result = build_capcut_project(
        project_name=project_name,
        scenes=scenes_for_capcut,
        audio_path=audio_path,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
    )

    return result


# ===== Monitor Endpoints =====

@app.get("/api/monitor/status")
async def monitor_status():
    """Trạng thái tổng quan: sessions, active jobs, stats."""
    return {
        "server": "running",
        "sdk_pool": session_manager.stats, "lab_pool": lab_session_manager.stats,
        "active_jobs": list(ACTIVE_JOBS.values()),
        "cancel_flags": list(CANCEL_FLAGS.keys()),
        "total_activities": len(ACTIVITY_LOG),
    }


@app.get("/api/monitor/activities")
async def monitor_activities(category: str = "", limit: int = 100):
    """Lấy activity log (recent). Filter theo category nếu cần."""
    entries = list(ACTIVITY_LOG)
    if category:
        entries = [e for e in entries if e["category"] == category]
    return entries[-limit:]


@app.get("/api/monitor/stream")
async def monitor_stream():
    """SSE stream — real-time activity feed."""
    sub_id = str(uuid.uuid4())[:8]
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    MONITOR_SUBSCRIBERS[sub_id] = queue

    async def event_generator():
        try:
            # Gửi event kết nối thành công
            yield f"data: {json.dumps({'type': 'connected', 'subscriber_id': sub_id})}\n\n"
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat để giữ kết nối
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            MONITOR_SUBSCRIBERS.pop(sub_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ===== Lab System (Phòng nghiên cứu) =====

VALID_LAB_TYPES = {"storytelling", "styles"}


def _lab_sessions_dir(lab_type: str) -> Path:
    return LABS_DIR / lab_type / "sessions"


def _lab_session_path(lab_type: str, session_id: str) -> Path:
    return _lab_sessions_dir(lab_type) / f"{session_id}.json"


def _load_lab_session(lab_type: str, session_id: str) -> dict:
    path = _lab_session_path(lab_type, session_id)
    if path.exists():
        try:
            return json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_lab_session(lab_type: str, session_id: str, session_data: dict):
    path = _lab_session_path(lab_type, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    session_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(session_data, ensure_ascii=False, indent=2), "utf-8")


def _list_lab_sessions(lab_type: str) -> List[dict]:
    """Liệt kê tất cả sessions, sắp xếp theo updated_at mới nhất."""
    sessions_dir = _lab_sessions_dir(lab_type)
    if not sessions_dir.exists():
        return []
    sessions = []
    for f in sessions_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text("utf-8"))
            sessions.append({
                "id": data.get("id", f.stem),
                "title": data.get("title", "Chat mới"),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "message_count": len(data.get("messages", [])),
            })
        except (json.JSONDecodeError, OSError):
            continue
    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions


def _build_lab_storytelling_prompt() -> str:
    """System prompt cho Lab Kể chuyện."""
    # Load existing storytelling profiles for reference
    profiles_dir = TEMPLATES_DIR / "storytelling_profiles"
    existing = []
    if profiles_dir.exists():
        for f in sorted(profiles_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text("utf-8"))
                existing.append(f"- {data.get('name', f.stem)}: {data.get('description', '')[:100]}")
            except (json.JSONDecodeError, OSError):
                pass

    existing_text = "\n".join(existing) if existing else "(Chưa có profile nào)"

    return f"""Bạn là chuyên gia phân tích cách kể chuyện (storytelling) cho video YouTube.

QUY TẮC VỀ TOOLS — ĐỌC KỸ:
Bạn CÓ Playwright MCP tools đã được cài sẵn và cấp quyền. Danh sách tools bạn CÓ THỂ dùng:
- mcp__plugin_playwright_playwright__browser_navigate — mở URL
- mcp__plugin_playwright_playwright__browser_snapshot — chụp DOM
- mcp__plugin_playwright_playwright__browser_click — click element
- mcp__plugin_playwright_playwright__browser_fill_form — điền form
- mcp__plugin_playwright_playwright__browser_take_screenshot — chụp ảnh màn hình
- mcp__plugin_playwright_playwright__browser_type — gõ text
- mcp__plugin_playwright_playwright__browser_press_key — nhấn phím
- mcp__plugin_playwright_playwright__browser_find — tìm element
- mcp__plugin_playwright_playwright__browser_tabs — quản lý tabs
Khi user gửi link YouTube hoặc yêu cầu mở browser: HÃY DÙNG các tool trên ngay, KHÔNG từ chối, KHÔNG nói "tao không có tool".
Quyền đã bypass — không cần hỏi permission.

Tool BỊ CẤM (KHÔNG dùng): Write, Edit, Bash, Read, Glob, Grep, NotebookEdit, WebFetch, WebSearch.
Hệ thống tự lưu file từ output text của bạn. Trả lời bằng tiếng Việt.

VAI TRÒ:
- Phân tích PHONG CÁCH KỂ CHUYỆN CHUNG từ video/kênh YouTube — rút ra công thức, pattern, kỹ thuật có thể ÁP DỤNG LẠI cho nhiều video khác cùng dạng
- Nhận diện cấu trúc narrative: hook, build-up, climax, resolution, outro
- Phân tích kỹ thuật engagement: câu hỏi tu từ, cliffhanger, foreshadowing, callback
- Phân tích nhịp kể: pacing, tone shifts, emotional arc
- So sánh và tổng hợp nhiều nguồn thành 1 cách kể chuyện nhất quán

QUAN TRỌNG — MỤC ĐÍCH CỦA LAB:
- Phân tích để rút ra PHONG CÁCH CHUNG, CÔNG THỨC SẢN XUẤT có thể dùng lại cho nhiều video cùng thể loại.
- KHÔNG phân tích nội dung/kịch bản cụ thể của video đó (nhân vật nào, sự kiện nào...).
- PHẢI tập trung vào: cấu trúc kể, kỹ thuật giữ khán giả, nhịp điệu, cách mở/đóng, pattern lặp lại — những thứ ÁP DỤNG ĐƯỢC cho video khác.
- Output là template/profile trung lập, dùng được cho bất kỳ dự án nào cùng dạng.
- KHÔNG tự thêm phần "áp dụng cho kênh của user" hay gợi ý cho kênh cụ thể nào.

RÀNG BUỘC CHUNG CỦA HỆ THỐNG — BẮT BUỘC TUÂN THỦ:
- KHÔNG có phụ đề (subtitle) — hệ thống không dùng phụ đề
- Video clip KHÔNG có tiếng nói/lời thoại — chỉ ambient/SFX nhẹ
- Tỷ lệ video clip chỉ chiếm khoảng 1/10 tổng số cảnh, tập trung ở đoạn mở đầu
Dù video gốc có phụ đề hay dùng nhiều video clip, template vẫn tuân theo ràng buộc trên.

CÁCH LÀM VIỆC:
1. User gửi transcript, mô tả, link video, hoặc ghi chú
2. Phân tích và TRẢ KẾT QUẢ CUỐI CÙNG LUÔN. Nếu dùng Playwright, làm xong rồi trả 1 lần.
3. Khi user nói "Lưu" hoặc "Tạo profile" → xuất STORYTELLING PROFILE

QUY TẮC OUTPUT — BẮT BUỘC TUYỆT ĐỐI:
- TUYỆT ĐỐI KHÔNG viết bất kỳ text nào TRƯỚC KHI có kết quả phân tích hoàn chỉnh
- KHÔNG viết: "đang mở browser", "chờ chụp frame", "đang đo cut", "tao sẽ...", "xong sẽ gửi..."
- KHÔNG giải thích bạn đang làm gì. KHÔNG thông báo tiến độ. KHÔNG nói "đợi tao".
- Dùng Playwright HOÀN TOÀN IM LẶNG — không output text nào cho đến khi có kết quả cuối
- Chỉ viết text DUY NHẤT 1 LẦN khi đã phân tích XONG TẤT CẢ

FORMAT KHI LƯU:
Khi user nói "Lưu", xuất profile theo format sau (BẮT BUỘC đúng format):

[PROFILE:01]
{{{{
  "id": "slug-tieng-viet-khong-dau",
  "name": "Tên profile tiếng Việt",
  "category": "storytelling_profile",
  "description": "Mô tả ngắn gọn cách kể chuyện",
  "preview_summary": "• Điểm 1\\n• Điểm 2\\n• Điểm 3",
  "applies_to": ["project_storytelling_guide"],
  "content": "# Tên cách kể chuyện\\n\\n## Cấu trúc\\n...\\n\\n## Hook\\n...\\n\\n## Pacing\\n...\\n\\n## Kỹ thuật engagement\\n..."
}}}}
[/PROFILE:01]

Mã tăng dần: PROFILE:01, PROFILE:02...
Field "content" là markdown — tất cả nội dung chi tiết nằm trong đó.
Field "id" dùng slug không dấu, lowercase, gạch nối (VD: "ke-chuyen-hap-dan").

PROFILES ĐÃ CÓ:
{existing_text}"""


def _build_lab_styles_prompt() -> str:
    """System prompt cho Lab Phong cách hình ảnh & edit."""
    # Load existing templates for reference
    existing = []
    for cat in ["image_styles", "edit_styles"]:
        cat_dir = TEMPLATES_DIR / cat
        if cat_dir.exists():
            for f in sorted(cat_dir.glob("*.json")):
                try:
                    data = json.loads(f.read_text("utf-8"))
                    existing.append(f"- [{cat}] {data.get('name', f.stem)}: {data.get('description', '')[:100]}")
                except (json.JSONDecodeError, OSError):
                    pass

    existing_text = "\n".join(existing) if existing else "(Chưa có template nào)"

    return f"""Bạn là chuyên gia phân tích phong cách hình ảnh và edit video cho kênh YouTube.

QUY TẮC VỀ TOOLS — ĐỌC KỸ:
Bạn CÓ Playwright MCP tools đã được cài sẵn và cấp quyền. Danh sách tools bạn CÓ THỂ dùng:
- mcp__plugin_playwright_playwright__browser_navigate — mở URL
- mcp__plugin_playwright_playwright__browser_snapshot — chụp DOM
- mcp__plugin_playwright_playwright__browser_click — click element
- mcp__plugin_playwright_playwright__browser_fill_form — điền form
- mcp__plugin_playwright_playwright__browser_take_screenshot — chụp ảnh màn hình
- mcp__plugin_playwright_playwright__browser_type — gõ text
- mcp__plugin_playwright_playwright__browser_press_key — nhấn phím
- mcp__plugin_playwright_playwright__browser_find — tìm element
- mcp__plugin_playwright_playwright__browser_tabs — quản lý tabs
Khi user gửi link YouTube hoặc yêu cầu mở browser: HÃY DÙNG các tool trên ngay, KHÔNG từ chối, KHÔNG nói "tao không có tool".
Quyền đã bypass — không cần hỏi permission.

Tool BỊ CẤM (KHÔNG dùng): Write, Edit, Bash, Read, Glob, Grep, NotebookEdit, WebFetch, WebSearch.
Hệ thống tự lưu file từ output text của bạn. Trả lời bằng tiếng Việt.

VAI TRÒ:
- Phân tích PHONG CÁCH HÌNH ẢNH & EDIT CHUNG từ video/kênh YouTube — rút ra quy tắc, công thức sản xuất có thể ÁP DỤNG LẠI cho nhiều video khác cùng dạng
- Phân tích art style, color palette, composition, character design ở mức PHONG CÁCH (không phải nội dung cụ thể)
- Phân tích phong cách edit: transitions, pacing, text overlay, Ken Burns, sound design
- Tạo template image_style hoặc edit_style theo format chuẩn của hệ thống

QUAN TRỌNG — MỤC ĐÍCH CỦA LAB:
- Phân tích để rút ra PHONG CÁCH CHUNG, QUY TẮC SẢN XUẤT có thể dùng lại cho nhiều video cùng thể loại.
- KHÔNG phân tích nội dung cụ thể (nhân vật nào, cảnh nào trong video đó).
- PHẢI tập trung vào: phong cách vẽ, cách dùng màu, cách chuyển cảnh, nhịp edit, cách dùng text overlay, Ken Burns — những thứ ÁP DỤNG ĐƯỢC cho video khác.
- Output là template trung lập, dùng được cho bất kỳ dự án nào cùng dạng.
- KHÔNG tự thêm phần "áp dụng cho kênh của user" hay gợi ý cho kênh cụ thể nào.

RÀNG BUỘC CHUNG CỦA HỆ THỐNG — BẮT BUỘC TUÂN THỦ KHI PHÂN TÍCH:
Khi phân tích và xuất template, PHẢI loại bỏ / không đề cập các thành phần sau dù video gốc có:
- KHÔNG có phụ đề (subtitle) — hệ thống không dùng phụ đề
- Video clip KHÔNG có tiếng nói/lời thoại — chỉ ambient/SFX nhẹ
- Tỷ lệ video clip chỉ chiếm khoảng 1/10 tổng số cảnh, tập trung ở đoạn mở đầu (phần còn lại là ảnh tĩnh + Ken Burns)
Nếu video gốc có phụ đề, vẫn KHÔNG đưa vào template. Nếu video gốc dùng 90% video clip, template vẫn ghi quy tắc 1/10.

CÁCH LÀM VIỆC:
1. User gửi mô tả, link video, hoặc transcript
2. Phân tích và TRẢ KẾT QUẢ CUỐI CÙNG LUÔN theo DANH SÁCH BẮT BUỘC bên dưới. Nếu dùng Playwright, làm xong rồi trả 1 lần.
3. Khi user nói "Lưu hình ảnh" → xuất IMAGE STYLE template
4. Khi user nói "Lưu edit" → xuất EDIT STYLE template

QUY TẮC OUTPUT:
- KHÔNG output tin nhắn trung gian ("đang mở browser", "chờ chụp frame", "đang phân tích...")
- Làm xong TẤT CẢ rồi trả kết quả phân tích đầy đủ 1 lần duy nhất
- Nếu dùng Playwright: dùng im lặng, chỉ trả kết quả cuối

DANH SÁCH PHÂN TÍCH BẮT BUỘC — luôn phải có khi phân tích, tùy chỉnh theo kịch bản cụ thể:

A. CHUYỂN CẢNH (Transitions):
- Liệt kê các loại transition được dùng (crossfade, fade_from/to_black, cut...)
- Khi nào dùng loại nào (mặc định, giữa segment, cao trào...)
- Thời lượng mỗi loại
- Transition NÊN TRÁNH (nếu có)

B. HIỆU ỨNG KEN BURNS (ảnh tĩnh):
- Các kiểu: zoom in/out, pan ngang, pan + zoom kết hợp
- % zoom, hướng, thời gian cụ thể
- Quy tắc: ảnh tĩnh có bắt buộc Ken Burns không

C. NHỊP ĐIỆU (Pacing):
- Thời lượng cảnh theo từng đoạn kịch bản (hook, bối cảnh, diễn biến, cao trào, kết)
- Cách xử lý khi clip ngắn hơn lời đọc (slow-down, giữ frame cuối...)

D. TEXT OVERLAY:
- Các loại text (tên nhân vật, năm, địa điểm, trích dẫn, label kép...)
- Vị trí, font, timing, giới hạn ký tự
- Hiệu ứng xuất hiện (fade in/out)

E. ÂM THANH:
- Mức âm lượng: giọng đọc, nhạc nền, SFX
- Thể loại nhạc theo từng đoạn
- Khoảng lặng, sound effects
- Audio direction cho video clip (nếu có)

F. TỶ LỆ VIDEO/IMAGE:
- Tỷ lệ cảnh video so với tổng
- Video tập trung ở đoạn nào
- Bố cục chuyển động trong video clip (camera style, composition)

G. MÀN HÌNH KẾT:
- Thời lượng, nội dung (logo, video gợi ý, subscribe...)
- Nhạc fade out

Lưu ý: Không nhất thiết mọi mục đều có đủ thông tin. Nếu video/kênh được phân tích không có thông tin cho mục nào, ghi "Không xác định từ nguồn" và đề xuất giá trị mặc định phù hợp.

FORMAT KHI LƯU HÌNH ẢNH:
[IMG_STYLE:01]
{{{{
  "id": "slug-ten-style",
  "name": "Tên phong cách hình ảnh",
  "category": "image_style",
  "description": "Mô tả ngắn",
  "preview_summary": "• Điểm 1\\n• Điểm 2\\n• Điểm 3",
  "applies_to": ["project_style_guide", "video_visual_guide"],
  "content": "# Phong cách hình ảnh\\n\\n## Tổng quan\\n...\\n\\n## Characters\\n...\\n\\n## Prompt structure\\n..."
}}}}
[/IMG_STYLE:01]

FORMAT KHI LƯU EDIT:
[EDIT_STYLE:01]
{{{{
  "id": "slug-ten-style",
  "name": "Tên phong cách edit",
  "category": "edit_style",
  "description": "Mô tả ngắn",
  "preview_summary": "• Điểm 1\\n• Điểm 2\\n• Điểm 3",
  "applies_to": ["video_edit_guide"],
  "content": "# Phong cách edit\\n\\n## Director Plan\\n...\\n\\n## Per-scene Edit\\n...\\n\\n## Pacing\\n..."
}}}}
[/EDIT_STYLE:01]

Mã tăng dần: IMG_STYLE:01, IMG_STYLE:02... và EDIT_STYLE:01, EDIT_STYLE:02...
Field "content" là markdown đầy đủ.
Field "id" dùng slug không dấu, lowercase, gạch nối.

TEMPLATES ĐÃ CÓ:
{existing_text}"""


def _build_lab_chat_prompt(lab_type: str, messages: List[dict], new_message: str) -> str:
    """Xây prompt cho lab chat."""
    if lab_type == "storytelling":
        system = _build_lab_storytelling_prompt()
    else:
        system = _build_lab_styles_prompt()

    if len(messages) <= 1:
        return f"{system}\n\nUser: {new_message}"

    recent = messages[-10:]
    history = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:3000]}"
        for m in recent[:-1]
    )
    return f"{system}\n\nLịch sử chat:\n{history}\n\nUser: {new_message}"


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


@app.get("/api/lab/{lab_type}/sessions")
async def list_sessions(lab_type: str):
    """Liệt kê tất cả sessions của lab."""
    if lab_type not in VALID_LAB_TYPES:
        raise HTTPException(400, f"Invalid lab_type. Must be one of: {VALID_LAB_TYPES}")
    return {"sessions": _list_lab_sessions(lab_type)}


@app.post("/api/lab/{lab_type}/sessions")
async def create_session(lab_type: str, body: Optional[CreateSessionRequest] = None):
    """Tạo session chat mới."""
    if lab_type not in VALID_LAB_TYPES:
        raise HTTPException(400, f"Invalid lab_type. Must be one of: {VALID_LAB_TYPES}")
    session_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    title = (body.title if body and body.title else "Chat mới")
    session_data = {
        "id": session_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    _save_lab_session(lab_type, session_id, session_data)
    return session_data


@app.delete("/api/lab/{lab_type}/sessions/{session_id}")
async def delete_session(lab_type: str, session_id: str):
    """Xóa 1 session."""
    if lab_type not in VALID_LAB_TYPES:
        raise HTTPException(400, f"Invalid lab_type. Must be one of: {VALID_LAB_TYPES}")
    path = _lab_session_path(lab_type, session_id)
    if path.exists():
        path.unlink()
    return {"status": "deleted"}


@app.get("/api/lab/{lab_type}/sessions/{session_id}/history")
async def get_session_history(lab_type: str, session_id: str):
    """Lấy lịch sử chat của 1 session."""
    if lab_type not in VALID_LAB_TYPES:
        raise HTTPException(400, f"Invalid lab_type. Must be one of: {VALID_LAB_TYPES}")
    session = _load_lab_session(lab_type, session_id)
    if not session:
        raise HTTPException(404, "Session không tồn tại")
    return {"messages": session.get("messages", []), "title": session.get("title", "")}


@app.post("/api/lab/{lab_type}/sessions/{session_id}/stream")
async def stream_session_message(lab_type: str, session_id: str, body: ChatRequest):
    """Gửi tin nhắn tới 1 session, stream phản hồi qua SSE."""
    if lab_type not in VALID_LAB_TYPES:
        raise HTTPException(400, f"Invalid lab_type. Must be one of: {VALID_LAB_TYPES}")

    session = _load_lab_session(lab_type, session_id)
    if not session:
        raise HTTPException(404, "Session không tồn tại")

    messages = session.get("messages", [])
    now = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": body.message, "timestamp": now}
    messages.append(user_msg)

    # Auto-title: lấy 50 ký tự đầu từ tin nhắn user đầu tiên
    if session.get("title") == "Chat mới" and body.message.strip():
        session["title"] = body.message.strip()[:50] + ("..." if len(body.message.strip()) > 50 else "")

    session["messages"] = messages
    _save_lab_session(lab_type, session_id, session)

    prompt = _build_lab_chat_prompt(lab_type, messages, body.message)
    _emit_activity("lab", "stream_start", f"[{lab_type}] {body.message[:80]}", status="working")

    async def event_stream():
        full_text = ""
        try:
            # Lab: buffer tất cả, KHÔNG stream delta — chỉ trả kết quả cuối
            # Reset full_text mỗi new_turn để chỉ giữ text từ lượt cuối cùng
            async for msg_type, data in lab_session_manager.query_stream(prompt):
                if msg_type == "new_turn":
                    full_text = ""  # Reset — chỉ giữ text từ lượt cuối
                elif msg_type == "delta":
                    full_text += data
                    yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"
                elif msg_type == "thinking":
                    preview = data[:300].replace("\n", " ").strip()
                    _emit_activity("lab", "thinking", f"[{lab_type}] {preview}", status="info")
                elif msg_type == "error":
                    full_text = full_text or f"[Lỗi] {data}"
                    yield f"data: {json.dumps({'type': 'error', 'text': data[:200]}, ensure_ascii=False)}\n\n"
        except Exception as e:
            full_text = full_text or f"[Lỗi] {str(e)[:200]}"
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)[:200]}, ensure_ascii=False)}\n\n"

        assistant_msg = {
            "role": "assistant",
            "content": full_text or "[Không có phản hồi]",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        sess = _load_lab_session(lab_type, session_id)
        sess.setdefault("messages", []).append(assistant_msg)
        _save_lab_session(lab_type, session_id, sess)

        _emit_activity("lab", "stream_done", f"[{lab_type}] {len(full_text)} ký tự", status="success")
        # Gửi toàn bộ kết quả 1 lần cuối
        yield f"data: {json.dumps({'type': 'done', 'text': full_text}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _extract_lab_tagged_content(text: str, tag: str, code: Optional[str] = None) -> Optional[str]:
    """Trích nội dung từ lab message theo tag [PROFILE:xx], [IMG_STYLE:xx], [EDIT_STYLE:xx]."""
    if code:
        pattern = rf'\[{tag}:{_re.escape(code)}\]\s*([\s\S]*?)\s*\[/{tag}:{_re.escape(code)}\]'
        match = _re.search(pattern, text)
        return match.group(1).strip() if match else None
    else:
        pattern = rf'\[{tag}:\d+\]\s*([\s\S]*?)\s*\[/{tag}:\d+\]'
        matches = _re.findall(pattern, text)
        return matches[-1].strip() if matches else None


TAG_TO_CATEGORY = {
    "PROFILE": "storytelling_profiles",
    "IMG_STYLE": "image_styles",
    "EDIT_STYLE": "edit_styles",
}


class LabSaveRequest(BaseModel):
    tag: str  # PROFILE, IMG_STYLE, EDIT_STYLE
    code: Optional[str] = None  # "01", "02", etc. None = latest


@app.post("/api/lab/{lab_type}/sessions/{session_id}/save")
async def save_lab_output(lab_type: str, session_id: str, body: LabSaveRequest):
    """Lưu output từ lab chat thành profile/template JSON file."""
    if lab_type not in VALID_LAB_TYPES:
        raise HTTPException(400, f"Invalid lab_type. Must be one of: {VALID_LAB_TYPES}")
    if body.tag not in TAG_TO_CATEGORY:
        raise HTTPException(400, f"Invalid tag. Must be one of: {list(TAG_TO_CATEGORY.keys())}")

    session = _load_lab_session(lab_type, session_id)
    if not session:
        raise HTTPException(404, "Session không tồn tại")

    messages = session.get("messages", [])
    if not messages:
        raise HTTPException(400, "Chưa có nội dung chat để lưu")

    # Find tagged content in chat history
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        extracted = _extract_lab_tagged_content(content, body.tag, body.code)
        if extracted:
            # Parse JSON from extracted content
            try:
                template_data = json.loads(extracted)
            except json.JSONDecodeError:
                raise HTTPException(400, f"Nội dung [{body.tag}] không phải JSON hợp lệ")

            # Validate required fields
            for field in ["id", "name", "category", "content"]:
                if field not in template_data:
                    raise HTTPException(400, f"Thiếu field bắt buộc: {field}")

            # Write to templates directory
            category_dir = TEMPLATES_DIR / TAG_TO_CATEGORY[body.tag]
            category_dir.mkdir(parents=True, exist_ok=True)
            output_path = category_dir / f"{template_data['id']}.json"
            output_path.write_text(
                json.dumps(template_data, ensure_ascii=False, indent=2), "utf-8"
            )

            _emit_activity(
                "lab", "save",
                f"[{lab_type}] Đã lưu {body.tag}: {template_data['name']}",
                status="success",
            )

            return {
                "status": "saved",
                "tag": body.tag,
                "template_id": template_data["id"],
                "name": template_data["name"],
                "category": TAG_TO_CATEGORY[body.tag],
                "path": str(output_path),
            }

    raise HTTPException(400, f"Không tìm thấy nội dung [{body.tag}] trong chat history")


@app.get("/api/lab/{lab_type}/outputs")
async def list_lab_outputs(lab_type: str):
    """Liệt kê profiles/templates đã tạo từ lab."""
    if lab_type not in VALID_LAB_TYPES:
        raise HTTPException(400, f"Invalid lab_type. Must be one of: {VALID_LAB_TYPES}")

    results = []

    if lab_type == "storytelling":
        categories = ["storytelling_profiles"]
    else:
        categories = ["image_styles", "edit_styles"]

    for cat in categories:
        cat_dir = TEMPLATES_DIR / cat
        if not cat_dir.exists():
            continue
        for f in sorted(cat_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text("utf-8"))
                results.append({
                    "id": data.get("id", f.stem),
                    "name": data.get("name", f.stem),
                    "category": cat,
                    "description": data.get("description", ""),
                    "preview_summary": data.get("preview_summary", ""),
                })
            except (json.JSONDecodeError, OSError):
                continue

    return {"outputs": results}


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "sdk_pool": session_manager.stats, "lab_pool": lab_session_manager.stats}


@app.on_event("startup")
async def _startup():
    """Pre-warm SDK clients + browser + start cleanup task."""
    asyncio.create_task(session_manager.warm_up(count=3))
    asyncio.create_task(lab_session_manager.warm_up(count=2))
    asyncio.create_task(_cleanup_finished_bg_jobs())
    # Pre-warm browser để không phải chờ khi tạo asset
    async def _warm_browser():
        try:
            await _get_flow_browser()
            log.info("🌐 Browser pre-warmed")
        except Exception as e:
            log.warning(f"⚠️ Browser pre-warm failed (sẽ thử lại khi cần): {e}")
    asyncio.create_task(_warm_browser())


@app.on_event("shutdown")
async def _shutdown():
    """Gracefully disconnect all SDK clients."""
    await session_manager.shutdown()
    await lab_session_manager.shutdown()


if __name__ == "__main__":
    import uvicorn
    print("🚀 Chat Bridge đang chạy tại http://localhost:8001")
    print(f"   SDK Pool: {SESSION_POOL_SIZE} clients (warm)")
    print(f"   Projects: {PROJECTS_DIR.resolve()}")
    uvicorn.run(app, host="0.0.0.0", port=8001)
