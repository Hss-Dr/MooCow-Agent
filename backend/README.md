# Backend - FastAPI多Agent智能对话系统

## 目录结构

```
backend/
├── api/                    # API路由层
│   ├── main.py            # FastAPI应用入口
│   ├── chat_routes.py     # 对话相关路由
│   ├── session_routes.py  # 会话管理路由
│   └── repository_routes.py # 文件管理路由
├── multi_agent/           # 多Agent系统
│   ├── orchestrator_agent.py  # 编排Agent
│   ├── technical_agent.py     # 技术Agent
│   ├── service_agent.py       # 服务Agent
│   └── agent_factory.py       # Agent工厂
├── services/              # 业务服务层
│   ├── agent_service.py         # Agent服务
│   ├── session_service.py       # 会话服务
│   └── stream_response_service.py # 流式响应服务
├── infrastructure/        # 基础设施
│   ├── ai/               # AI客户端封装
│   │   ├── openai_client.py  # OpenAI客户端
│   │   ├── prompt_loader.py  # 提示词加载器
│   │   └── skill_loader.py   # 技能加载器
│   ├── clients/          # 外部服务客户端
│   │   └── rag_client.py     # RAG服务客户端
│   ├── database/         # 数据库连接池
│   ├── logging/          # 日志系统
│   └── tools/            # Agent工具集
│       ├── local/        # 本地工具
│       └── mcp/          # MCP工具
├── schemas/              # Pydantic数据模型
│   ├── chat.py          # 对话模型
│   ├── session.py       # 会话模型
│   ├── request.py       # 请求模型
│   └── response.py      # 响应模型
├── prompts/             # Agent提示词模板
│   ├── orchestrator.md
│   ├── technical_agent.md
│   └── comprehensive_service_agent.md
├── skills/              # Agent技能定义
├── config/              # 配置管理
│   └── settings.py
├── storage/             # 本地存储
│   └── uploads/         # 用户上传文件
├── logs/                # 日志文件
├── requirements.txt     # Python依赖
└── .env                 # 环境变量配置
```

## 核心组件

### 1. Multi-Agent系统

#### OrchestratorAgent (编排Agent)
- 负责任务分解与多Agent协调
- 决策路由到专业Agent
- 整合多Agent响应

#### TechnicalAgent (技术Agent)
- IT技术问题解答
- 系统故障诊断
- 技术文档查询

#### ServiceAgent (服务Agent)
- 客户服务咨询
- 业务流程指导
- 产品信息查询

### 2. RAG集成

通过`RAGClient`与外部RAG服务通信：
- 知识库检索
- 文档向量化
- 上下文增强

### 3. 流式响应

支持Server-Sent Events (SSE)实时推送：
- 打字机效果
- 实时Agent思考过程
- 中断控制

## 环境配置

### 必需环境变量

```env
# OpenAI配置
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4-turbo-preview

# RAG服务
RAG_SERVICE_URL=http://localhost:8001
RAG_SERVICE_TIMEOUT=30
RAG_DEFAULT_USER_ID=default_user

# 数据库（如果直连）
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# 应用配置
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:5173"]
```

## 安装依赖

### 使用Conda（推荐）

```bash
conda create -n llm python=3.12
conda activate llm
pip install -r requirements.txt
```

### 使用virtualenv

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 启动服务

### 开发模式

```bash
# 设置PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH

# 启动（带热重载）
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

### 生产模式

```bash
# 使用Gunicorn + Uvicorn workers
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080 \
  --timeout 120
```

## API端点

### 会话管理

#### POST /api/create_session
创建新会话

```json
{
  "user_id": "user123"
}
```

响应：
```json
{
  "session_id": "abc123def456",
  "user_id": "user123",
  "created_at": "2024-08-18T14:30:00Z"
}
```

#### GET /api/get_sessions/
获取用户所有会话

参数：
- `user_id` (query): 用户ID

#### GET /api/get_messages/
获取会话消息历史

参数：
- `session_id` (query): 会话ID

### 对话

#### POST /api/ai_search/
AI对话（SSE流式响应）

```json
{
  "message": "如何配置VPN？",
  "web_search": false,
  "deep_research": false,
  "attachments": []
}
```

响应：Server-Sent Events流
```
data: {"type": "agent", "content": "正在分析您的问题..."}
data: {"type": "text", "content": "VPN配置步骤如下：\n1. ..."}
data: {"type": "done"}
```

### 文件管理

#### POST /api/upload_files/
上传文件到知识库

```bash
curl -X POST "http://localhost:8080/api/upload_files/" \
  -F "files=@document.pdf" \
  -F "user_id=user123"
```

#### GET /api/get_files/
获取用户文件列表

#### DELETE /api/delete_file/
删除文件

## 开发指南

### 添加新API端点

1. 在`api/`创建路由文件：

```python
# api/my_routes.py
from fastapi import APIRouter
from schemas.my_schema import MyRequest, MyResponse

router = APIRouter()

@router.post("/my_endpoint", response_model=MyResponse)
async def my_endpoint(request: MyRequest):
    # 业务逻辑
    return MyResponse(...)
```

2. 在`api/main.py`注册：

```python
from api.my_routes import router as my_router
app.include_router(my_router, prefix="/api", tags=["my_feature"])
```

### 添加新Agent

1. 创建Agent类：

```python
# multi_agent/my_agent.py
from agents import Agent

class MyAgent(Agent):
    def __init__(self):
        super().__init__(
            name="my_agent",
            instructions="你的角色是...",
            model="gpt-4-turbo-preview"
        )
```

2. 在`agent_factory.py`注册：

```python
def create_my_agent():
    return MyAgent()
```

### 添加新工具

1. 在`infrastructure/tools/local/`创建：

```python
# infrastructure/tools/local/my_tool.py
def my_tool_function(param: str) -> str:
    """工具说明"""
    return f"结果: {param}"
```

2. 在Agent中声明：

```markdown
# prompts/my_agent.md

## 可用工具

### my_tool_function
- 参数：param (string)
- 返回：处理结果
- 用途：...
```

## 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_async.py -v

# 覆盖率报告
pytest --cov=. --cov-report=html
```

## 日志

日志文件位置：
- `logs/app.log` - 应用日志
- `logs/error.log` - 错误日志
- `logs/agent_debug.log` - Agent调试日志

查看实时日志：
```bash
tail -f logs/app.log
```

## 故障排查

### 1. 模块导入错误
```
ModuleNotFoundError: No module named 'xxx'
```

解决：
```bash
export PYTHONPATH=$PWD:$PYTHONPATH
# 或在启动命令前加：
PYTHONPATH=$PWD uvicorn api.main:app
```

### 2. RAG服务连接失败
检查RAG服务是否运行：
```bash
docker ps | grep MooCow-Agent
curl http://localhost:8001/health
```

### 3. OpenAI API错误
检查`.env`中的API密钥和base URL配置

## 性能优化

### 1. 连接池配置
在`config/settings.py`调整：
```python
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20
```

### 2. 异步优化
所有I/O操作使用async/await：
```python
async def get_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
```

### 3. 缓存策略
使用Redis缓存频繁查询：
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_config():
    # 昂贵的配置加载
    pass
```

## 安全建议

1. **API密钥**: 永远不要提交`.env`到版本控制
2. **输入验证**: 使用Pydantic严格验证所有输入
3. **SQL注入**: 使用参数化查询
4. **CORS**: 生产环境限制允许的来源
5. **速率限制**: 考虑使用slowapi或类似库

## 扩展阅读

- [FastAPI文档](https://fastapi.tiangolo.com/)
- [OpenAI Agents SDK](https://github.com/openai/openai-agents)
- [Pydantic文档](https://docs.pydantic.dev/)
