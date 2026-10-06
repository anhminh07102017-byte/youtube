#!/bin/bash
# Khởi động toàn bộ hệ thống Video Factory
# Web UI (Docker) + Chat Bridge (host)

cd "$(dirname "$0")"

# Màu
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${GREEN}=== Video Factory — Khởi động ===${NC}"
echo ""

# 1. Docker Compose
echo -e "${YELLOW}[1/2]${NC} Khởi động Web UI (Docker)..."
docker compose up -d 2>&1 | tail -5
echo ""

# 2. Chat Bridge
echo -e "${YELLOW}[2/2]${NC} Khởi động Chat Bridge..."

# Check dependencies
python3 -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Cài dependencies cho Chat Bridge...${NC}"
    pip3 install fastapi uvicorn pydantic
fi

# Kill Chat Bridge cũ nếu còn chạy
if lsof -ti:8001 > /dev/null 2>&1; then
    echo "Dừng Chat Bridge cũ..."
    kill $(lsof -ti:8001) 2>/dev/null
    sleep 1
fi

# Chạy Chat Bridge nền
nohup python3 chat_bridge.py > /tmp/chat_bridge.log 2>&1 &
CHAT_PID=$!
sleep 1

# Kiểm tra
if kill -0 $CHAT_PID 2>/dev/null; then
    echo -e "${GREEN}Chat Bridge đang chạy (PID: $CHAT_PID)${NC}"
else
    echo -e "${RED}Chat Bridge khởi động thất bại. Xem log: /tmp/chat_bridge.log${NC}"
fi

echo ""
echo -e "${GREEN}=== Sẵn sàng ===${NC}"
echo -e "  Web UI:       http://localhost:3000"
echo -e "  Backend API:  http://localhost:8000"
echo -e "  Chat Bridge:  http://localhost:8001"
echo ""
echo -e "Dừng: ${YELLOW}./stop.sh${NC}"
