"""
Chat Bridge — Cầu nối giữa Web UI và Claude Code CLI.
Chạy trên HOST (không phải Docker), gọi claude CLI cho AI responses.
Mỗi video có 1 session Claude Code riêng biệt.

Chạy: python3 chat_bridge.py
Hoặc: ./start_chat.sh
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Minh Bi Youtube — Chat Bridge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", "./projects"))
CLAUDE_BIN = shutil.which("claude") or "claude"

# Lưu session ID cho mỗi video
SESSION_STORE: Dict[str, str] = {}


def _session_key(project_id: str, video_id: str) -> str:
    return f"{project_id}::{video_id}"


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


def _load_full_context(project_id: str, video_id: str) -> str:
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

    return "\n\n".join(parts) if parts else ""


def _build_system_prompt(project_id: str, video_id: str) -> str:
    """Xây dựng system prompt với đầy đủ context dự án."""
    ctx = _load_full_context(project_id, video_id)
    return f"""Bạn đang giúp sản xuất video cho kênh YouTube lịch sử. Project: {project_id}, Video: {video_id}.

QUAN TRỌNG — QUY TẮC BẮT BUỘC:
- Bạn KHÔNG được ghi file, tạo file, hay dùng bất kỳ tool nào (Write, Edit, Bash, Read...).
- Bạn CHỈ trả lời bằng text thuần. Hệ thống sẽ tự xử lý việc lưu file.
- KHÔNG hỏi user "cho phép ghi file" hay "cần quyền truy cập" — user không có cách nào approve.
- Khi user nói "Chốt", hãy trả về nội dung kịch bản trực tiếp trong message, hệ thống sẽ tự lưu.

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


def _call_claude(prompt: str, session_id: Optional[str] = None, timeout: int = 180) -> Tuple[str, Optional[str]]:
    """
    Gọi Claude Code CLI.
    Returns: (response_text, session_id)
    """
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--output-format", "text",
        "--disallowedTools", "Write", "Edit", "Bash", "Read", "Glob", "Grep",
        "NotebookEdit", "WebFetch", "WebSearch",
    ]
    if session_id:
        cmd.extend(["--resume", session_id])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECTS_DIR.parent),
        )
        response = proc.stdout.strip()
        if not response and proc.stderr:
            response = f"[Lỗi] {proc.stderr.strip()[:500]}"

        # Trích session ID từ stderr nếu có (claude CLI thường in session info)
        new_session_id = session_id
        # Nếu chưa có session, dùng key tạm
        return response or "[Không có phản hồi]", new_session_id

    except subprocess.TimeoutExpired:
        return "[Timeout] Claude đang xử lý quá lâu. Thử lại hoặc chia nhỏ yêu cầu.", session_id
    except FileNotFoundError:
        return "[Lỗi] Không tìm thấy claude CLI. Hãy cài đặt Claude Code.", session_id
    except Exception as e:
        return f"[Lỗi] {str(e)[:200]}", session_id


async def _call_claude_async(prompt: str, timeout: int = 180) -> str:
    """Async version of _call_claude — dùng cho concurrent workers."""
    cmd = [
        CLAUDE_BIN, "-p", prompt,
        "--output-format", "text",
        "--disallowedTools", "Write", "Edit", "Bash", "Read", "Glob", "Grep",
        "NotebookEdit", "WebFetch", "WebSearch",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(PROJECTS_DIR.parent),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return "[Timeout] Claude đang xử lý quá lâu."
        response = stdout.decode().strip()
        if not response and stderr:
            response = f"[Lỗi] {stderr.decode().strip()[:500]}"
        return response or "[Không có phản hồi]"
    except FileNotFoundError:
        return "[Lỗi] Không tìm thấy claude CLI."
    except Exception as e:
        return f"[Lỗi] {str(e)[:200]}"


def _build_chat_prompt(project_id: str, video_id: str, messages: List[dict], new_message: str) -> str:
    """Xây prompt cho chat (dùng chung cho cả stream và non-stream)."""
    system = _build_system_prompt(project_id, video_id)
    if len(messages) <= 1:
        return f"{system}\n\nUser: {new_message}"
    recent = messages[-20:]
    history = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
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
    key = _session_key(project_id, video_id)
    session_id = SESSION_STORE.get(key)
    messages = _load_history(project_id, video_id)

    now = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": body.message, "timestamp": now}
    messages.append(user_msg)

    prompt = _build_chat_prompt(project_id, video_id, messages, body.message)
    response, new_session = _call_claude(prompt, session_id)
    if new_session:
        SESSION_STORE[key] = new_session

    assistant_msg = {
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    messages.append(assistant_msg)
    _save_history(project_id, video_id, messages)

    return assistant_msg


@app.post("/api/chat/{project_id}/{video_id}/stream")
async def stream_message(project_id: str, video_id: str, body: ChatRequest):
    """Gửi tin nhắn, stream phản hồi từ Claude qua SSE."""
    key = _session_key(project_id, video_id)
    session_id = SESSION_STORE.get(key)
    messages = _load_history(project_id, video_id)

    now = datetime.now(timezone.utc).isoformat()
    user_msg = {"role": "user", "content": body.message, "timestamp": now}
    messages.append(user_msg)
    _save_history(project_id, video_id, messages)

    prompt = _build_chat_prompt(project_id, video_id, messages, body.message)

    def event_stream():
        # type: () -> Iterator[str]
        cmd = [
            CLAUDE_BIN, "-p", prompt,
            "--output-format", "stream-json", "--verbose", "--include-partial-messages",
            "--disallowedTools", "Write", "Edit", "Bash", "Read", "Glob", "Grep",
            "NotebookEdit", "WebFetch", "WebSearch",
        ]
        if session_id:
            cmd.extend(["--resume", session_id])

        full_text = ""
        new_sid = session_id
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(PROJECTS_DIR.parent),
            )
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                evt_type = data.get("type", "")

                # Text delta — stream ra ngay
                if evt_type == "stream_event":
                    inner = data.get("event", {})
                    if inner.get("type") == "content_block_delta":
                        delta = inner.get("delta", {})
                        if delta.get("type") == "text_delta":
                            chunk = delta.get("text", "")
                            if chunk:
                                full_text += chunk
                                yield f"data: {json.dumps({'type': 'delta', 'text': chunk}, ensure_ascii=False)}\n\n"

                # Kết quả cuối
                elif evt_type == "result":
                    new_sid = data.get("session_id", session_id)
                    if not full_text:
                        full_text = data.get("result", "")

            proc.wait(timeout=10)

        except Exception as e:
            full_text = full_text or f"[Lỗi] {str(e)[:200]}"
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)[:200]}, ensure_ascii=False)}\n\n"

        # Lưu session
        if new_sid:
            SESSION_STORE[key] = new_sid

        # Lưu message hoàn chỉnh
        assistant_msg = {
            "role": "assistant",
            "content": full_text or "[Không có phản hồi]",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        msgs = _load_history(project_id, video_id)
        msgs.append(assistant_msg)
        _save_history(project_id, video_id, msgs)

        yield f"data: {json.dumps({'type': 'done', 'text': full_text}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/api/chat/{project_id}/{video_id}")
async def clear_history(project_id: str, video_id: str):
    """Xóa lịch sử chat."""
    key = _session_key(project_id, video_id)
    SESSION_STORE.pop(key, None)
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
            visual_type, content_tag = _classify_scene(script_text)
            scenes.append({
                "scene_number": scene_num,
                "timestamp_start": round(group_start, 2),
                "timestamp_end": round(group_end, 2),
                "script_text": script_text,
                "visual_type": visual_type,
                "content_tag": content_tag,
                "mood": "",
            })
            scene_num += 1
            group_texts = []
            if not is_last:
                group_start = entries[i + 1]["start"]

    return scenes


@app.post("/api/generate-shotlist/{project_id}/{video_id}")
async def generate_shotlist(project_id: str, video_id: str):
    """Parse SRT thuần Python → chia thành danh sách cảnh (KHÔNG gọi Claude)."""
    video_dir = PROJECTS_DIR / project_id / "videos" / video_id

    # Đọc SRT
    srt_path = video_dir / "audio" / "subtitles.srt"
    if not srt_path.exists():
        raise HTTPException(400, "Chưa có file SRT. Hãy upload trước.")
    srt_content = srt_path.read_text("utf-8")

    # Parse SRT
    entries = _parse_srt(srt_content)
    if not entries:
        return {"status": "error", "message": "Không parse được nội dung SRT. Kiểm tra lại file."}

    # Đọc edit guide → parse pacing rules
    pacing_rules = []
    edit_guide_path = video_dir / "edit_guide.md"
    if edit_guide_path.exists():
        edit_guide_content = edit_guide_path.read_text("utf-8")
        pacing_rules = _parse_pacing_rules(edit_guide_content)

    # Group thành scenes theo pacing rules
    scenes = _group_srt_to_scenes(entries, pacing_rules=pacing_rules or None)

    # Lưu shot_list.json
    shot_list = {
        "project_id": project_id,
        "video_id": video_id,
        "total_scenes": len(scenes),
        "scenes": scenes,
    }
    (video_dir / "shot_list.json").write_text(
        json.dumps(shot_list, ensure_ascii=False, indent=2), "utf-8"
    )

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

    prompt = f"""Tạo prompt tiếng Anh cho Veo 3 (AI video/image generation) dựa trên nội dung cảnh sau.

=== NỘI DUNG CẢNH ===
Cảnh số: {scene_data['scene_number']}
Thời gian: {scene_data['timestamp_start']}s — {scene_data['timestamp_end']}s
Nội dung thuyết minh: {scene_data['script_text']}

{f"=== PHONG CÁCH HÌNH ẢNH ==={chr(10)}{style_guide}" if style_guide else ""}

Yêu cầu:
- Prompt bằng TIẾNG ANH
- Phong cách 2D animated cartoon: flat shading, clean bold outlines, simple expressive characters
- Mô tả chi tiết: nhân vật, bối cảnh, hành động, góc máy, ánh sáng, mood
- Phù hợp văn hóa Việt Nam / lịch sử
- Cũng cho biết visual_type phù hợp: "image" (cảnh tĩnh) hoặc "video" (có chuyển động)
- Và mood: dramatic, calm, tense, happy, sad, epic, mysterious

Trả về ĐÚNG format JSON (không có text khác):
{{
  "veo3_prompt": "prompt tiếng Anh ở đây...",
  "visual_type": "image hoặc video",
  "mood": "mood ở đây"
}}"""

    response, _ = _call_claude(prompt, timeout=120)

    # Kiểm tra lỗi từ Claude CLI
    if response.startswith("[Lỗi]") or response.startswith("[Timeout]") or response.startswith("[Không có"):
        return {"status": "error", "message": response}

    # Parse JSON
    try:
        import re as _re
        json_match = _re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("Không tìm thấy JSON trong response")
    except (json.JSONDecodeError, ValueError) as e:
        return {"status": "error", "message": f"Không parse được: {str(e)}", "raw": response[:500]}

    return {
        "status": "ok",
        "scene_number": scene_number,
        "veo3_prompt": result.get("veo3_prompt", ""),
        "visual_type": result.get("visual_type", "image"),
        "mood": result.get("mood", ""),
    }


@app.post("/api/generate-all-prompts/{project_id}/{video_id}")
async def generate_all_prompts(project_id: str, video_id: str, mode: str = "missing"):
    """Đầu não + 10 workers song song → SSE stream cập nhật từng scene.
    mode: 'all' = tạo lại tất cả, 'missing' = chỉ cảnh chưa có prompt.
    """
    video_dir = PROJECTS_DIR / project_id / "videos" / video_id

    # Đọc shot_list.json
    shot_list_path = video_dir / "shot_list.json"
    if not shot_list_path.exists():
        raise HTTPException(400, "Chưa có danh sách cảnh. Hãy tạo từ SRT trước.")
    shot_list = json.loads(shot_list_path.read_text("utf-8"))
    all_scenes = shot_list.get("scenes", [])
    if not all_scenes:
        raise HTTPException(400, "Danh sách cảnh rỗng.")

    # Lọc scenes theo mode
    if mode == "missing":
        # Lấy scenes đã có prompt từ DB để loại bỏ
        existing_prompts = set()
        try:
            import urllib.request
            scenes_resp = urllib.request.urlopen(
                f"http://localhost:8000/api/projects/{project_id}/videos/{video_id}/scenes", timeout=5
            )
            db_scenes = json.loads(scenes_resp.read().decode())
            for s in db_scenes:
                if s.get("veo3_prompt"):
                    existing_prompts.add(s.get("scene_number"))
        except Exception:
            pass
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
    char_prompts = {}  # {name: visual_prompt_base} cho workers inject vào prompt
    try:
        import urllib.request
        char_resp = urllib.request.urlopen(f"http://localhost:8000/api/projects/{project_id}/characters", timeout=5)
        chars = json.loads(char_resp.read().decode())
        if chars:
            char_lines = []
            for c in chars:
                name = c.get("name", "?")
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
    except Exception:
        pass

    # Tóm tắt tất cả scenes cho đầu não
    scenes_summary = "\n".join(
        f"  Cảnh {s['scene_number']} ({s['timestamp_start']}s–{s['timestamp_end']}s): {s['script_text'][:120]}"
        for s in all_scenes
    )

    async def event_stream():
        # ===== PHASE 1: Đầu não — tạo master plan =====
        yield f"data: {json.dumps({'type': 'status', 'message': 'Đầu não đang phân tích tổng thể...'}, ensure_ascii=False)}\n\n"

        head_prompt = f"""Bạn là đạo diễn hình ảnh cho video lịch sử hoạt hình 2D. Phân tích TOÀN BỘ {len(all_scenes)} cảnh và tạo kế hoạch visual cho từng cảnh.

=== DANH SÁCH CẢNH ===
{scenes_summary}

{f"=== PHONG CÁCH HÌNH ẢNH ==={chr(10)}{style_guide}" if style_guide else ""}
{f"=== HƯỚNG DẪN EDIT ==={chr(10)}{edit_guide}" if edit_guide else ""}
{f"=== NHÂN VẬT ==={chr(10)}{char_info}" if char_info else ""}

Tạo kế hoạch visual cho TỪ TỪNG cảnh. Mỗi cảnh cần:
- visual_brief: Mô tả ngắn bằng tiếng Anh (2-3 câu) — nhân vật, bối cảnh, hành động chính, góc máy
- visual_type: "image" (cảnh tĩnh/minh họa) hoặc "video" (có chuyển động/hành động)
- mood: dramatic, calm, tense, happy, sad, epic, mysterious
- color_tone: warm, cool, muted, vibrant, dark
- transition_note: ghi chú chuyển cảnh với cảnh trước (nếu cần)

Đảm bảo:
- NHẤT QUÁN nhân vật xuyên suốt (cùng trang phục, ngoại hình)
- Mood progression hợp lý (ví dụ: calm → tense → epic → calm)
- Đa dạng góc máy (wide, medium, close-up, aerial xen kẽ)

Trả về ĐÚNG format JSON (không text khác):
[
  {{
    "scene_number": 1,
    "visual_brief": "...",
    "visual_type": "image",
    "mood": "...",
    "color_tone": "...",
    "transition_note": ""
  }},
  ...
]"""

        head_response = await _call_claude_async(head_prompt, timeout=300)

        # Parse master plan
        if head_response.startswith("[Lỗi]") or head_response.startswith("[Timeout]") or head_response.startswith("[Không có"):
            yield f"data: {json.dumps({'type': 'error', 'message': f'Đầu não lỗi: {head_response}'}, ensure_ascii=False)}\n\n"
            return

        master_plan = []
        try:
            json_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', head_response)
            if json_match:
                master_plan = json.loads(json_match.group())
            else:
                raise ValueError("Không tìm thấy JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Đầu não trả về không đúng format: {e}'}, ensure_ascii=False)}\n\n"
            return

        # Lưu master plan
        plan_path = video_dir / "visual_plan.json"
        plan_path.write_text(json.dumps(master_plan, ensure_ascii=False, indent=2), "utf-8")

        # Index plan by scene_number
        plan_by_scene = {p["scene_number"]: p for p in master_plan}

        yield f"data: {json.dumps({'type': 'plan_done', 'message': f'Kế hoạch xong — {len(master_plan)} cảnh. Bắt đầu tạo prompt...', 'plan': master_plan}, ensure_ascii=False)}\n\n"

        # ===== PHASE 2: Workers song song — tạo Veo3 prompt =====
        semaphore = asyncio.Semaphore(10)

        async def worker(scene_data):
            async with semaphore:
                sn = scene_data["scene_number"]
                plan = plan_by_scene.get(sn, {})

                # Tìm nhân vật liên quan đến cảnh này
                scene_chars = ""
                if char_prompts:
                    script = scene_data.get("script_text", "")
                    matched = [f"- {name}: {prompt}" for name, prompt in char_prompts.items() if name in script]
                    if matched:
                        scene_chars = "=== NHÂN VẬT TRONG CẢNH (dùng chính xác mô tả này) ===\n" + "\n".join(matched)

                worker_prompt = f"""Tạo prompt tiếng Anh chi tiết cho Veo 3 dựa trên kế hoạch visual đã được duyệt.

=== THÔNG TIN CẢNH ===
Cảnh số: {sn}
Thời gian: {scene_data['timestamp_start']}s — {scene_data['timestamp_end']}s
Nội dung thuyết minh: {scene_data['script_text']}

=== KẾ HOẠCH VISUAL (từ đạo diễn) ===
Visual brief: {plan.get('visual_brief', 'N/A')}
Visual type: {plan.get('visual_type', 'image')}
Mood: {plan.get('mood', 'N/A')}
Color tone: {plan.get('color_tone', 'N/A')}
Transition note: {plan.get('transition_note', '')}

{scene_chars}

{f"=== PHONG CÁCH CHUNG ==={chr(10)}{style_guide[:1500]}" if style_guide else ""}

Yêu cầu:
- Prompt bằng TIẾNG ANH, 2-4 câu
- Phong cách 2D animated cartoon: flat shading, clean bold outlines, simple expressive characters
- Bám sát visual brief của đạo diễn
- Nếu có nhân vật, PHẢI dùng đúng mô tả visual đã cho (consistency)
- Mô tả cụ thể: nhân vật (trang phục, biểu cảm), bối cảnh, ánh sáng, composition, camera angle

Trả về ĐÚNG format JSON:
{{
  "veo3_prompt": "prompt tiếng Anh chi tiết...",
  "visual_type": "{plan.get('visual_type', 'image')}",
  "mood": "{plan.get('mood', '')}"
}}"""

                resp = await _call_claude_async(worker_prompt, timeout=120)

                if resp.startswith("[Lỗi]") or resp.startswith("[Timeout]") or resp.startswith("[Không có"):
                    return {"scene_number": sn, "status": "error", "message": resp}

                try:
                    jm = re.search(r'\{[\s\S]*\}', resp)
                    if jm:
                        result = json.loads(jm.group())
                    else:
                        raise ValueError("No JSON found")
                except (json.JSONDecodeError, ValueError) as e:
                    return {"scene_number": sn, "status": "error", "message": str(e)}

                return {
                    "scene_number": sn,
                    "status": "ok",
                    "veo3_prompt": result.get("veo3_prompt", ""),
                    "visual_type": result.get("visual_type", plan.get("visual_type", "image")),
                    "mood": result.get("mood", plan.get("mood", "")),
                }

        # Chạy tất cả workers, yield kết quả khi từng cái xong
        tasks = []
        for scene_data in all_scenes:
            tasks.append(asyncio.create_task(worker(scene_data)))

        completed = 0
        total = len(tasks)
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            result["progress"] = f"{completed}/{total}"
            yield f"data: {json.dumps({'type': 'scene_done', **result}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'all_done', 'message': f'Hoàn tất {total} cảnh.'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/extract-characters/{project_id}/{video_id}")
async def extract_characters(project_id: str, video_id: str):
    """Phân tích kịch bản và trích xuất nhân vật lịch sử bằng Claude."""
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

    # 3. Đọc style guide
    style_guide = ""
    sg_path = PROJECTS_DIR / project_id / "style_guide.md"
    if sg_path.exists():
        style_guide = sg_path.read_text("utf-8").strip()[:2000]

    # 4. Gọi Claude phân tích
    prompt = f"""Phân tích kịch bản video lịch sử sau và trích xuất TẤT CẢ nhân vật lịch sử xuất hiện.

=== KỊCH BẢN ===
{script_content[:5000]}

{f"=== THÔNG TIN DỰ ÁN ==={chr(10)}{project_info}" if project_info else ""}
{f"=== PHONG CÁCH HÌNH ẢNH ==={chr(10)}{style_guide}" if style_guide else ""}

Với mỗi nhân vật, hãy cung cấp thông tin CHI TIẾT dựa trên sử liệu (Đại Việt Sử Ký Toàn Thư, Việt Nam Sử Lược, tranh vẽ lịch sử, tượng đài, mô tả trong sử sách).

Trả về ĐÚNG format JSON array (KHÔNG có text nào khác ngoài JSON):
[
  {{
    "name": "Tên tiếng Việt (có dấu)",
    "historical_name": "Tên đầy đủ trong sử sách",
    "era": "Thời kỳ lịch sử",
    "age_range": "VD: 30-40",
    "reference_description": "Mô tả bằng tiếng Việt dựa trên sử liệu: ngoại hình từ tranh vẽ, tượng, mô tả trong sử sách. Nêu rõ nguồn tham khảo.",
    "visual_prompt_base": "English prompt for 2D animated cartoon style character. MUST include: 2D animated cartoon style, flat shading, clean bold outlines, simple expressive features. Describe in detail: face shape, facial hair, hair style and color, skin tone, exact clothing with period-accurate details (patterns, materials, colors), body build, height impression, posture. This prompt will be reused across ALL scenes for consistency.",
    "color_palette": {{
      "skin": "hex hoặc mô tả",
      "hair": "hex hoặc mô tả",
      "primary_outfit": "hex hoặc mô tả",
      "secondary_outfit": "hex hoặc mô tả"
    }},
    "consistency_anchors": ["3-5 đặc điểm nhận dạng PHẢI giữ nhất quán, VD: thick black beard, gold crown with dragon motif, red royal robe with gold trim"]
  }}
]

QUAN TRỌNG:
- visual_prompt_base phải bằng TIẾNG ANH, chi tiết và cụ thể để đảm bảo nhất quán xuyên suốt video
- Giữ tên tiếng Việt CÓ DẤU trong visual_prompt_base (VD: "Trần Hưng Đạo", không phải "Tran Hung Dao")
- Phong cách BẮT BUỘC: 2D animated cartoon, flat shading, clean bold outlines
- Trang phục PHẢI chính xác theo thời kỳ lịch sử
- consistency_anchors là những đặc điểm KHÔNG ĐƯỢC thay đổi giữa các cảnh
- Nếu không có nhân vật lịch sử nào, trả về mảng rỗng: []"""

    response = await _call_claude_async(prompt, timeout=180)

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

    return {"status": "ok", "characters": characters}


# ─────────────────────────────────────────────
# Google Flow (Veo 3) — Playwright automation
# ─────────────────────────────────────────────
FLOW_BROWSER_DIR = Path.home() / ".video-factory-browser"
_playwright_instance = None
_browser_context = None


async def _get_flow_browser():
    """Lấy hoặc tạo persistent browser context cho Google Flow."""
    global _playwright_instance, _browser_context
    if _browser_context is not None:
        try:
            # Test if context is still alive
            _browser_context.pages
            return _browser_context
        except Exception:
            _browser_context = None

    from playwright.async_api import async_playwright
    if _playwright_instance is None:
        _playwright_instance = await async_playwright().start()

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
        url = f"https://flow.google.com/project/{flow_project_id}/character"
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


@app.post("/api/generate-character-image/{project_id}/{character_id}")
async def generate_character_image(project_id: str, character_id: str):
    """Tạo ảnh nhân vật trên Google Flow (Veo 3) bằng Playwright."""
    import httpx

    BACKEND = "http://localhost:8000"

    # 1. Get character info from backend
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND}/api/projects/{project_id}/characters/{character_id}")
        if resp.status_code != 200:
            raise HTTPException(404, "Không tìm thấy nhân vật.")
        character = resp.json()

    if not character.get("visual_prompt_base"):
        raise HTTPException(400, "Nhân vật chưa có visual_prompt_base.")

    # 2. Get project flow_project_id
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND}/api/projects/{project_id}")
        if resp.status_code != 200:
            raise HTTPException(404, "Không tìm thấy dự án.")
        project = resp.json()

    flow_project_id = project.get("flow_project_id")
    if not flow_project_id:
        raise HTTPException(400, "Dự án chưa cấu hình Flow Project ID. Vào Settings để thêm.")

    # 3. Build prompt with character name for Flow
    prompt = f"{character['name']}. {character['visual_prompt_base']}"

    # 4. Automate Flow
    try:
        result = await _flow_create_character(flow_project_id, character["name"], prompt)
    except Exception as e:
        if "NOT_LOGGED_IN" in str(e):
            raise HTTPException(401, "FLOW_NOT_LOGGED_IN")
        raise HTTPException(500, f"Lỗi tạo ảnh: {str(e)}")

    # 5. Save image from browser download
    image_path = None
    if result.get("image_bytes"):
        save_dir = PROJECTS_DIR / project_id / "characters" / character_id
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / "reference.png"
        save_path.write_bytes(result["image_bytes"])
        image_path = f"/files/projects/{project_id}/characters/{character_id}/reference.png"

    # 6. Update character in backend
    update_data = {}
    if image_path:
        update_data["reference_image_path"] = image_path
    if result.get("flow_character_id"):
        update_data["flow_character_id"] = result["flow_character_id"]

    if update_data:
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{BACKEND}/api/projects/{project_id}/characters/{character_id}",
                json=update_data,
            )

    return {
        "status": "ok",
        "image_path": image_path,
        "flow_character_id": result.get("flow_character_id"),
        "flow_url": result.get("page_url"),
    }


@app.post("/api/generate-all-character-images/{project_id}")
async def generate_all_character_images(project_id: str):
    """Tạo ảnh cho TẤT CẢ nhân vật trong project (tuần tự)."""
    import httpx

    BACKEND = "http://localhost:8000"

    # Get all characters
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND}/api/projects/{project_id}/characters")
        characters = resp.json() if resp.status_code == 200 else []

    if not characters:
        return {"status": "ok", "message": "Không có nhân vật nào.", "results": []}

    # Get project
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND}/api/projects/{project_id}")
        if resp.status_code != 200:
            raise HTTPException(404, "Không tìm thấy dự án.")
        project = resp.json()

    flow_project_id = project.get("flow_project_id")
    if not flow_project_id:
        raise HTTPException(400, "Dự án chưa cấu hình Flow Project ID.")

    results = []
    for char in characters:
        if not char.get("visual_prompt_base"):
            results.append({"id": char["id"], "name": char["name"], "status": "skipped", "reason": "Chưa có visual_prompt_base"})
            continue

        try:
            prompt = f"{char['name']}. {char['visual_prompt_base']}"
            result = await _flow_create_character(flow_project_id, char["name"], prompt)

            # Save image
            image_path = None
            if result.get("image_bytes"):
                save_dir = PROJECTS_DIR / project_id / "characters" / char["id"]
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = save_dir / "reference.png"
                save_path.write_bytes(result["image_bytes"])
                image_path = f"/files/projects/{project_id}/characters/{char['id']}/reference.png"

            # Update backend
            update_data = {}
            if image_path:
                update_data["reference_image_path"] = image_path
            if result.get("flow_character_id"):
                update_data["flow_character_id"] = result["flow_character_id"]
            if update_data:
                async with httpx.AsyncClient() as client:
                    await client.put(
                        f"{BACKEND}/api/projects/{project_id}/characters/{char['id']}",
                        json=update_data,
                    )

            results.append({"id": char["id"], "name": char["name"], "status": "ok", "image_path": image_path})
        except Exception as e:
            results.append({"id": char["id"], "name": char["name"], "status": "error", "error": str(e)})

    return {"status": "ok", "results": results}


@app.get("/health")
async def health():
    """Health check."""
    claude_ok = shutil.which("claude") is not None
    return {"status": "ok", "claude_available": claude_ok}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Chat Bridge đang chạy tại http://localhost:8001")
    print(f"   Claude CLI: {CLAUDE_BIN}")
    print(f"   Projects: {PROJECTS_DIR.resolve()}")
    uvicorn.run(app, host="0.0.0.0", port=8001)
