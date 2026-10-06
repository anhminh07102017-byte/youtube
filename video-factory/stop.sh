#!/bin/bash
# Dừng toàn bộ hệ thống Video Factory

cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}=== Video Factory — Dừng ===${NC}"
echo ""

# Dừng Chat Bridge
if lsof -ti:8001 > /dev/null 2>&1; then
    kill $(lsof -ti:8001) 2>/dev/null
    echo "Chat Bridge đã dừng"
else
    echo "Chat Bridge không chạy"
fi

# Dừng Docker
docker compose down 2>&1 | tail -3

echo ""
echo -e "${GREEN}Đã dừng toàn bộ.${NC}"
