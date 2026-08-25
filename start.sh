#!/bin/bash
# MooCow-Agent - 一键启动脚本
#
# 用法：./start.sh
#   [1] 一键启动（Docker 后端 + RAG + 前端 dev server）
#   [2] 仅启动 Docker 服务（后端 + RAG，前端自行启动）
#   [3] 停止所有服务
#   [4] 查看服务状态

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MooCow-Agent - 启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# ------------------------------------------------------------
# 1. 初始化缺失的 .env（从各目录 .env.example 模板复制）
#    密钥在 .gitignore 中不上传，首次 clone 后必须先生成
# ------------------------------------------------------------
init_env() {
    local dir="$1"
    if [ ! -f "$dir/.env" ]; then
        if [ -f "$dir/.env.example" ]; then
            cp "$dir/.env.example" "$dir/.env"
            echo -e "  ${GREEN}✓${NC} 已从模板生成 $dir/.env"
        fi
    fi
}
echo -e "\n${BLUE}[1/3] 检查环境配置...${NC}"
init_env "backend"
init_env "rag-service"
init_env "frontend"

# 占位符密钥只警告不阻断（容器能启动，LLM/搜索功能需填真实密钥）
warn_placeholder() {
    local file="$1"
    if [ -f "$file" ] && grep -qE "your-siliconflow-api-key|your-dashscope-api-key|your-baidu-map-ak|change-me" "$file"; then
        echo -e "  ${YELLOW}⚠️  $file 仍是占位符密钥：服务可启动，但 LLM 对话 / 联网搜索需要填写真实密钥${NC}"
    fi
}
warn_placeholder "backend/.env"
warn_placeholder "rag-service/.env"

# ------------------------------------------------------------
# 2. 检查 Docker
# ------------------------------------------------------------
echo -e "\n${BLUE}[2/3] 检查 Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker 未运行，请先启动 Docker Desktop${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Docker 正常"

# ------------------------------------------------------------
# 3. 前端启动（后台 dev server，端口 5181）
# ------------------------------------------------------------
start_frontend() {
    cd "$ROOT_DIR/frontend"

    if [ ! -d node_modules ]; then
        echo -e "  ${YELLOW}首次运行，安装前端依赖（可能需要几分钟）...${NC}"
        npm install
    fi

    if curl -s -o /dev/null --max-time 1 http://localhost:5181; then
        echo -e "  ${GREEN}✓${NC} 前端已在运行: http://localhost:5181"
    else
        nohup npm run dev > /tmp/moocow-agent-frontend.log 2>&1 &
        sleep 4
        echo -e "  ${GREEN}✓${NC} 前端已启动: http://localhost:5181"
    fi

    cd "$ROOT_DIR"
}

# ------------------------------------------------------------
# 模式选择
# ------------------------------------------------------------
echo -e "\n${BLUE}[3/3] 选择启动模式：${NC}"
echo -e "  ${GREEN}1)${NC} 一键启动（Docker 后端 + RAG + 前端）"
echo -e "  ${GREEN}2)${NC} 仅启动 Docker 服务（后端 + RAG，前端自行启动）"
echo -e "  ${GREEN}3)${NC} 停止所有服务"
echo -e "  ${GREEN}4)${NC} 查看服务状态"
read -p "请输入选项 [1-4]: " mode

case $mode in
    1)
        echo -e "\n${BLUE}启动 Docker 服务（首次运行会构建镜像，约 10-20 分钟）...${NC}"
        docker compose up -d

        echo -e "\n${BLUE}启动前端...${NC}"
        start_frontend

        echo -e "\n${GREEN}✅ 全部启动完成！${NC}"
        echo -e "\n服务地址："
        echo -e "  - 前端:     ${BLUE}http://localhost:5181${NC}"
        echo -e "  - 后端API:  ${BLUE}http://localhost:8080${NC}"
        echo -e "  - API文档:  ${BLUE}http://localhost:8080/docs${NC}"
        echo -e "  - RAG服务:  ${BLUE}http://localhost:8001${NC}"
        echo -e "\n查看日志：${YELLOW}docker compose logs -f${NC}"
        ;;

    2)
        echo -e "\n${BLUE}启动 Docker 服务（首次运行会构建镜像，约 10-20 分钟）...${NC}"
        docker compose up -d

        echo -e "\n${GREEN}✅ Docker 服务启动完成！${NC}"
        echo -e "\n服务地址："
        echo -e "  - 后端API:  ${BLUE}http://localhost:8080${NC}"
        echo -e "  - RAG服务:  ${BLUE}http://localhost:8001${NC}"
        echo -e "\n前端请手动启动：${YELLOW}cd frontend && npm run dev${NC}"
        ;;

    3)
        echo -e "\n${BLUE}停止所有服务...${NC}"
        docker compose down
        echo -e "${GREEN}✅ 服务已停止${NC}"
        ;;

    4)
        echo -e "\n${BLUE}Docker 服务状态：${NC}"
        docker compose ps
        echo -e "\n${BLUE}前端状态：${NC}"
        if curl -s -o /dev/null --max-time 1 http://localhost:5181; then
            echo -e "  ${GREEN}✓${NC} 前端运行中: http://localhost:5181"
        else
            echo -e "  ${YELLOW}✗${NC} 前端未运行"
        fi
        ;;

    *)
        echo -e "${RED}❌ 无效选项${NC}"
        exit 1
        ;;
esac

echo -e "\n${BLUE}========================================${NC}"
