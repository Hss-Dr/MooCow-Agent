#!/bin/bash
set -e

echo "=========================================="
echo "Backend容器启动脚本"
echo "=========================================="

# 等待PostgreSQL就绪
echo "等待PostgreSQL就绪..."
until PGPASSWORD=pg123456 psql -h gsk_pg -U postgres -d gsk -c '\q'; do
  echo "PostgreSQL未就绪，等待..."
  sleep 2
done
echo "✅ PostgreSQL已就绪"

# 初始化数据库
echo "初始化数据库..."
cd /app
python scripts/init_database.py

# 启动FastAPI应用
echo "启动FastAPI应用..."
# 使用--reload实现代码热重载（开发模式）
exec uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
