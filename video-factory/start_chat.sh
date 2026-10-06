#!/bin/bash
# Chat Bridge — chạy trên HOST (không phải Docker)
# Cầu nối giữa Web UI và Claude Code CLI

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Lỗi: Cần cài Python 3"
    exit 1
fi

# Check dependencies
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Cài dependencies..."
    pip3 install fastapi uvicorn
fi

# Check Claude CLI
if ! command -v claude &> /dev/null; then
    echo "Cảnh báo: Không tìm thấy Claude CLI. Chat sẽ không hoạt động."
fi

echo "Khởi động Chat Bridge tại http://localhost:8001"
python3 chat_bridge.py
