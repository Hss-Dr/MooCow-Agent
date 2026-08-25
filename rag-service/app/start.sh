#!/bin/bash

echo "=== 应用启动脚本 ==="

# 等待数据库就绪
echo "等待数据库连接..."
python -c "
import time
import os
import psycopg2
from psycopg2 import OperationalError

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.close()
        print('数据库连接成功!')
        break
    except OperationalError:
        retry_count += 1
        print(f'等待数据库... ({retry_count}/{max_retries})')
        time.sleep(2)
else:
    print('数据库连接失败!')
    exit(1)
"

# 检查并运行数据库迁移
echo "检查数据库迁移状态..."
python -c "
import os
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from sqlalchemy import create_engine, text

try:
    # 检查是否存在alembic_version表
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as conn:
        result = conn.execute(text(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')\"))
        table_exists = result.scalar()
        
        if not table_exists:
            print('首次部署，标记baseline...')
            alembic_cfg = Config('alembic.ini')
            command.stamp(alembic_cfg, '980b32f130df')
            print('Baseline标记完成')
        
        print('运行数据库迁移...')
        command.upgrade(alembic_cfg, 'head')
        print('数据库迁移完成!')
        
except Exception as e:
    print(f'迁移过程出错: {e}')
    # 不退出，继续启动应用（向下兼容）
    print('警告: 迁移失败，但应用将继续启动')
"

echo "启动应用服务..."
exec "$@" 