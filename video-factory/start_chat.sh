#!/bin/bash
# Chat Bridge — chạy trên HOST (không phải Docker)
# Sử dụng Claude Agent SDK (warm pool) — latency ~1.5s/tin

cd "$(dirname "$0")"

# Activate venv (Python 3.12 + claude-agent-sdk)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Lỗi: Chưa có .venv. Chạy:"
    echo "  uv venv --python 3.12 .venv"
    echo "  source .venv/bin/activate"
    echo "  uv pip install claude-agent-sdk fastapi uvicorn httpx aiohttp pydantic"
    exit 1
fi

# Check Claude CLI
if ! command -v claude &> /dev/null; then
    echo "Cảnh báo: Không tìm thấy Claude CLI. SDK sẽ không hoạt động."
fi

echo "Khởi động Chat Bridge (SDK warm pool) tại http://localhost:8001"
echo "Pool size: ${SESSION_POOL_SIZE:-5} clients"
python chat_bridge.py
