# RAG Service - 向量检索知识库服务

基于Elasticsearch的RAG（Retrieval Augmented Generation）服务，提供文档向量化、语义检索和上下文增强功能。

## 服务架构

```
rag-service/
├── docker-compose.yml   # Docker服务编排
├── .env                 # 环境变量配置
├── init.sql             # PostgreSQL初始化脚本
└── README.md            # 本文档
```

## 服务组件

### 1. moocowagent_rag (端口8001)
- FastAPI应用
- 提供文档上传、检索、对话API
- 处理文档解析与向量化

### 2. Elasticsearch (es01)
- 版本：8.11.3
- 向量数据库
- 存储文档嵌入向量
- 支持语义搜索

### 3. PostgreSQL (gsk_pg)
- 版本：15-alpine
- 存储结构化数据
- 用户信息、会话记录等

### 4. Redis (gsk_redis)
- 版本：7-alpine
- 缓存层
- 会话状态管理

## 快速开始

### 1. 配置环境变量

编辑`.env`文件：

```env
# Elasticsearch密码
ELASTIC_PASSWORD=your_secure_password_here

# 内存限制
MEM_LIMIT=2g

# 时区
TIMEZONE=Asia/Shanghai
```

### 2. 启动服务

```bash
docker compose up -d
```

### 3. 验证服务状态

```bash
# 查看容器状态
docker ps

# 期望输出：
# NAMES       STATUS                    PORTS
# moocowagent_rag    Up X minutes              0.0.0.0:8001->8001/tcp
# gsk-es-01   Up X minutes (healthy)    9200/tcp, 9300/tcp
# gsk_pg      Up X minutes              5432/tcp
# gsk_redis   Up X minutes              6379/tcp
```

### 4. 健康检查

```bash
# Elasticsearch
curl http://localhost:9200/_cluster/health

# moocowagent_rag（如果有健康检查端点）
curl http://localhost:8001/health
```

## 环境变量说明

### docker-compose.yml中的配置

```yaml
services:
  moocowagent_rag:
    environment:
      # Hugging Face镜像（用于下载模型）
      - HF_ENDPOINT=https://hf-mirror.com
      
      # PostgreSQL连接
      - DATABASE_URL=postgresql://postgres:pg123456@gsk_pg:5432/gsk
      
      # Elasticsearch连接
      - ES_HOST=http://es01:9200
      
      # API根路径
      - ROOT_PATH=http://localhost:8001
      
      # Redis连接
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=0

  es01:
    environment:
      # Elasticsearch配置
      - node.name=es01
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.http.ssl.enabled=false
      
      # 磁盘水位线设置（防止磁盘满）
      - cluster.routing.allocation.disk.watermark.low=5gb
      - cluster.routing.allocation.disk.watermark.high=3gb
      - cluster.routing.allocation.disk.watermark.flood_stage=2gb
      
      # JVM内存设置
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
```

## 数据持久化

Docker volumes确保数据持久化：

```yaml
volumes:
  gsk_esdata01:    # Elasticsearch数据
  pg_data:         # PostgreSQL数据
  redis_data:      # Redis数据
```

即使容器重启，数据也不会丢失。

## 端口映射

- **8001**: moocowagent_rag HTTP服务（映射到宿主机）
- **9200**: Elasticsearch HTTP API（容器内部）
- **9300**: Elasticsearch节点通信（容器内部）
- **5432**: PostgreSQL（容器内部）
- **6379**: Redis（容器内部）

如需从宿主机访问Elasticsearch/PostgreSQL，修改`docker-compose.yml`添加端口映射：

```yaml
services:
  es01:
    ports:
      - "9200:9200"  # 添加此行
  
  gsk_pg:
    ports:
      - "5432:5432"  # 添加此行
```

## 常用操作

### 查看日志

```bash
# 所有服务
docker compose logs -f

# 特定服务
docker compose logs -f moocowagent_rag
docker compose logs -f es01
```

### 停止服务

```bash
# 停止但保留数据
docker compose stop

# 停止并删除容器（保留volumes）
docker compose down

# 完全清理（包括volumes，会丢失数据！）
docker compose down -v
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart moocowagent_rag
```

### 进入容器

```bash
# 进入moocowagent_rag容器
docker exec -it moocowagent_rag bash

# 进入PostgreSQL
docker exec -it gsk_pg psql -U postgres -d gsk

# 进入Redis
docker exec -it gsk_redis redis-cli
```

## API使用示例

### 文档上传

```bash
curl -X POST "http://localhost:8001/api/upload" \
  -F "file=@document.pdf" \
  -F "user_id=user123"
```

### 知识库检索

```bash
curl -X POST "http://localhost:8001/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何配置VPN？",
    "user_id": "user123",
    "top_k": 5
  }'
```

### RAG对话

```bash
curl -X POST "http://localhost:8001/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "公司有哪些VPN配置方案？",
    "user_id": "user123",
    "session_id": "session_abc"
  }'
```

## Elasticsearch管理

### 查看索引

```bash
# 列出所有索引
curl -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cat/indices?v

# 查看特定索引
curl -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/documents/_search?pretty
```

### 删除索引

```bash
curl -X DELETE -u elastic:${ELASTIC_PASSWORD} \
  http://localhost:9200/documents
```

### 重建索引

如果向量模型更新，需要重新索引：

```bash
# 1. 删除旧索引
curl -X DELETE -u elastic:${ELASTIC_PASSWORD} \
  http://localhost:9200/documents

# 2. 重新上传文档（通过moocowagent_rag）
```

## PostgreSQL管理

### 连接数据库

```bash
docker exec -it gsk_pg psql -U postgres -d gsk
```

### 常用SQL

```sql
-- 查看所有表
\dt

-- 查看用户
SELECT * FROM users LIMIT 10;

-- 查看会话
SELECT * FROM sessions WHERE user_id = 'user123';

-- 清理旧数据
DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '30 days';
```

## 故障排查

### 1. Elasticsearch未启动/不健康

```bash
# 查看日志
docker logs gsk-es-01

# 常见原因：
# - 内存不足：增加MEM_LIMIT
# - 磁盘空间不足：清理磁盘或调整水位线
# - 权限问题：检查volume权限
```

### 2. moocowagent_rag启动失败

```bash
# 查看日志
docker logs moocowagent_rag

# 常见原因：
# - 等待Elasticsearch启动：添加depends_on + healthcheck
# - 环境变量错误：检查.env文件
# - 模型下载失败：检查HF_ENDPOINT或网络
```

### 3. 连接被拒绝

```bash
# 检查网络
docker network inspect moocowagent_backend_gsk_network

# 检查容器是否在同一网络
docker inspect moocowagent_rag | grep NetworkMode
```

### 4. 磁盘空间不足

```bash
# 查看volume使用情况
docker system df -v

# 清理未使用的资源
docker system prune -a --volumes
```

## 性能优化

### 1. Elasticsearch内存调优

根据可用内存调整：

```yaml
environment:
  - "ES_JAVA_OPTS=-Xms1g -Xmx1g"  # 增加到1GB
```

推荐：设置为系统内存的25-50%，但不超过32GB。

### 2. PostgreSQL连接池

在moocowagent_rag配置中：

```python
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
```

### 3. Redis持久化

如需持久化Redis数据，修改配置：

```yaml
redis:
  command: redis-server --appendonly yes
```

## 备份与恢复

### Elasticsearch快照

```bash
# 配置快照仓库
curl -X PUT -u elastic:${ELASTIC_PASSWORD} \
  http://localhost:9200/_snapshot/my_backup \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "fs",
    "settings": {
      "location": "/usr/share/elasticsearch/backup"
    }
  }'

# 创建快照
curl -X PUT -u elastic:${ELASTIC_PASSWORD} \
  http://localhost:9200/_snapshot/my_backup/snapshot_1?wait_for_completion=true
```

### PostgreSQL备份

```bash
# 导出
docker exec gsk_pg pg_dump -U postgres gsk > backup.sql

# 导入
docker exec -i gsk_pg psql -U postgres gsk < backup.sql
```

## 升级指南

### 升级Elasticsearch

1. 备份数据
2. 修改docker-compose.yml中的版本号
3. 重启服务

```bash
docker compose down
docker compose up -d
```

### 升级moocowagent_rag

如果有新的Docker镜像：

```bash
docker compose pull moocowagent_rag
docker compose up -d moocowagent_rag
```

## 监控

### 基础监控

```bash
# 容器资源使用
docker stats

# Elasticsearch集群状态
curl -u elastic:${ELASTIC_PASSWORD} \
  http://localhost:9200/_cluster/health?pretty
```

### 集成Prometheus（高级）

添加Elasticsearch exporter：

```yaml
services:
  elasticsearch-exporter:
    image: quay.io/prometheuscommunity/elasticsearch-exporter:latest
    command:
      - '--es.uri=http://elastic:${ELASTIC_PASSWORD}@es01:9200'
    ports:
      - "9114:9114"
    networks:
      - gsk_network
```

## 安全建议

1. **修改默认密码**: 生产环境必须修改ELASTIC_PASSWORD和PostgreSQL密码
2. **网络隔离**: 不要将内部端口暴露到公网
3. **启用SSL**: Elasticsearch生产环境应启用HTTPS
4. **定期更新**: 及时更新镜像版本修复安全漏洞
5. **访问控制**: 使用Elasticsearch的角色权限管理

## 相关文档

- [Elasticsearch官方文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [PostgreSQL文档](https://www.postgresql.org/docs/)
- [Redis文档](https://redis.io/documentation)
- [Docker Compose文档](https://docs.docker.com/compose/)
