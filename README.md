<div align="center">

# 🐮 MooCow-Agent

### 新能源汽车全链路智能助手 · 多智能体 + Skill 插件 + RAG 知识库

**从售前咨询到售后救援，一个助手全程领航。**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Ant Design](https://img.shields.io/badge/Ant_Design-5-0170FE?logo=antdesign&logoColor=white)](https://ant.design/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek_V4_Pro-4D6BFE)](https://www.deepseek.com/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.11-FEC514?logo=elasticsearch&logoColor=black)](https://www.elastic.co/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

[快速开始](#-快速开始) · [功能特性](#-功能特性) · [系统架构](#-系统架构) · [Skill 插件机制](#-skill-插件机制) · [项目结构](#-项目结构) · [常见问题](#-常见问题)

</div>

---

## 📖 简介

MooCow-Agent 是面向新能源汽车场景的**全链路智能客服系统**，基于多智能体协作架构，覆盖：

| 场景 | 能力 |
|------|------|
| 🛒 **销售售前** | 购车咨询、车型推荐、配置对比、价格金融方案、试驾预约 |
| 🔧 **售后技术** | 故障诊断、维修建议、保养周期、充电问题、电池健康、质保政策 |
| 🌐 **实时资讯** | 股价、天气、新闻等实时信息联网搜索 |
| 🗺️ **服务站导航** | 附近充电站/服务中心查询、路线规划（百度地图） |
| 📚 **私域知识库** | 企业文档上传、混合检索（公司公共库 + 个人库）、回答溯源 |

系统内置**深度思考开关**：开启时主调度使用推理模型并流式展示思考过程，关闭时切换快速模型直接作答。

## 🚀 快速开始

### 前置要求

- Docker Desktop（含 Docker Compose）
- Node.js ≥ 18（前端 dev server 使用）

### 一键启动

```bash
git clone <your-repo-url> moocow-agent
cd moocow-agent
./start.sh          # 选择 1：一键启动
```

脚本会自动完成：

1. 从 `.env.example` 生成缺失的 `.env` 配置
2. 构建并启动全部 Docker 服务（后端 / RAG / ES / PG / Redis）
3. 安装前端依赖并后台启动 dev server

启动完成后访问：

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5181 |
| 后端 API | http://localhost:8080/docs |
| RAG 服务 | http://localhost:8001/docs |

> ⚠️ **首次启动前唯一需要做的事**：编辑 `backend/.env`，填入真实的模型 API Key（占位符密钥下服务可启动但对话不可用）。

### 手动启动

<details>
<summary>不使用一键脚本时的步骤</summary>

```bash
# 1. 配置环境
cp backend/.env.example backend/.env       # 填入真实密钥
cp rag-service/.env.example rag-service/.env
cp frontend/.env.example frontend/.env

# 2. 启动 Docker 服务
docker compose up -d

# 3. 启动前端
cd frontend && npm install && npm run dev
```

</details>

## ✨ 功能特性

### 多智能体协作

| Agent | 职责 | 模型 |
|-------|------|------|
| **主调度智能体** | 意图识别、任务路由、结果聚合 | DeepSeek-V4-Pro（深度思考）/ DeepSeek-V3（快速） |
| **全链路智能体** | 销售售前 + 售后技术 + 实时资讯 | DeepSeek-V4-Pro |
| **服务站专家** | 充电站/服务中心查询、POI 导航 | DeepSeek-V4-Pro |

### Skill 插件机制（按需加载）

参考 Claude Code 的 Skill 设计：系统提示词只做场景判定，销售/售后等业务玩法封装为 **Skill**，模型判断任务类型后调用 `load_skill` 工具将其注入对话。**新增能力 = 新增一个 Markdown 文件，零代码改动。**

### RAG 混合知识库

- **双库检索**：公司公共库（`company_kb`）+ 用户个人库，一次查询合并召回
- **三级排序链路**：ES RRF 融合粗排（BM25 + KNN）→ SiliconFlow `bge-reranker-v2-m3` 语义精排 → 本地混合相似度兜底
- **文档管理**：上传 → deepdoc 解析（ONNX 模型）→ 入库，全流程可视化
- **回答溯源**：引用文档显示在回答下方，点击可展开检索片段原文

### 沉浸式对话体验

- 流式输出：思考过程（可折叠）/ 工具调用 / 最终答案 / 参考来源，四种事件类型实时推送
- 深色主题：按 DeepSeek 深色模式设计，纯黑底 + 灰阶层次 + 单一品牌蓝
- 思考可视化：thinking-orbs 点阵球动画（空闲 `solving` / 生成中 `working`）、输入框流动光束
- 按天分组的会话列表、停止生成、重新生成、一键复制

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  前端（React 18 + Ant Design）                              │
│  对话界面 / 文档管理 · SSE 流式解析                           │
│  （THINKING · PROCESS · ANSWER · REFERENCE）                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ SSE
┌───────────────────────────▼─────────────────────────────────┐
│  后端（FastAPI + openai-agents）                            │
│  · 路由层：auth / session / chat / repository               │
│  · 主调度智能体：意图识别 · 任务路由                         │
│  · 全链路智能体：销售 · 售后 · 实时资讯                      │
│  · 服务站专家：百度地图导航                                  │
│  · Skill 加载器：sales · aftersales                         │
│  · RAG 客户端 · 联网搜索 MCP（DashScope WebSearch）          │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
┌─────────────▼─────────────┐   ┌─────────────▼───────────────┐
│  RAG 服务（moocowagent_rag）      │   │  基础设施                   │
│  · 混合检索（公共库+个人库）│   │  · Elasticsearch 8.11       │
│  · RRF 融合粗排            │   │  · PostgreSQL 15            │
│  · Rerank 语义精排         │   │  · Redis 7                  │
│  · deepdoc 文档解析        │   │                             │
└───────────────────────────┘   └─────────────────────────────┘
```

## 🧩 Skill 插件机制

```
用户提问："预算20万，推荐一款家用SUV"
    ↓
全链路智能体：场景判定 → 销售售前
    ↓
调用 load_skill("sales") → 销售 Skill 指令注入对话
    ↓
严格按 Skill 流程执行（需求澄清 → 知识库检索 → 推荐）
    ↓
输出：结构化回答 + 参考来源
```

新增 Skill 只需在 `backend/skills/` 下创建：

```
skills/
├── sales_skill/
│   └── SKILL.md          # frontmatter description + 业务指令
└── aftersales_skill/
    └── SKILL.md
```

系统在启动时自动扫描目录，把技能清单注入工具描述，模型按需调用。

## 📁 项目结构

```
moocow-agent/
├── frontend/              # 前端（Vite + React 18 + TS + Ant Design）
│   └── src/
│       ├── pages/         # chat / login / repository
│       ├── components/    # sender / thinking-block / session-list ...
│       └── store/         # valtio 状态管理
├── backend/               # 后端（FastAPI + 多智能体）
│   ├── multi_agent/       # 主调度 / 全链路 / 服务站 Agent
│   ├── prompts/           # 系统提示词
│   ├── skills/            # ★ Skill 插件（销售 / 售后）
│   ├── infrastructure/    # AI 客户端 / Skill 加载器 / 本地工具 / MCP
│   ├── api/               # 路由（auth / chat / session / repository）
│   └── services/          # 业务服务（流式响应 / 会话）
├── rag-service/           # RAG 服务（检索 / 解析 / 入库，基于 RagFlow 改编）
├── docker-compose.yml     # 全套服务编排
└── start.sh               # 一键启动脚本
```

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vite 6 · React 18 · TypeScript 5 · Ant Design 5 · valtio · SCSS Modules |
| 后端 | FastAPI · openai-agents · DeepSeek-V4-Pro / V3（SiliconFlow） |
| RAG | Elasticsearch 8.11 · RRF 混合检索 · bge-reranker-v2-m3 · deepdoc（ONNX）· huqie 分词 |
| 通信 | SSE 流式（4 类事件） · MCP（DashScope WebSearch / 百度地图） |
| 基础设施 | Docker Compose · PostgreSQL 15 · Redis 7 · JWT 认证 |

## 🔧 环境配置

所有敏感配置均通过 `.env` 管理，仓库只提供 `.env.example` 模板：

| 文件 | 内容 |
|------|------|
| `backend/.env` | LLM API Key、模型名、MCP 搜索 Key、JWT 密钥 |
| `rag-service/.env` | RAG 模型、ES 密码、数据库连接、管理员白名单 |
| `frontend/.env` | API 代理地址 |

```bash
cp backend/.env.example backend/.env      # 然后填入真实密钥
```

## ❓ 常见问题

<details>
<summary><b>启动后对话报错 / 回答为空？</b></summary>

检查 `backend/.env` 中的 `SF_API_KEY` 是否已替换为真实密钥；查看后端日志 `docker compose logs -f backend`。
</details>

<details>
<summary><b>上传文档失败？</b></summary>

- 首次解析大型 PDF 可能需要 1-2 分钟（超时已放宽至 120s）
- 同名文件重复上传会被拒绝，请先删除旧文件
- RAG 侧公共库上传仅限管理员（`rag-service/.env` 的 `ADMIN_USER_IDS`）
</details>

<details>
<summary><b>为什么回答引用不了我的文档？</b></summary>

检索范围 = 公司公共库 + 当前登录用户的个人库。确认文档已上传成功（文档管理页可见），且登录账号与上传账号一致。
</details>

<details>
<summary><b>百度地图导航不可用？</b></summary>

需要在 `backend/.env` 填写真实的 `BAIDUMAP_AK`。
</details>

## 📄 许可与致谢

- 本项目后端与前端代码基于 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 发布
- `rag-service/` 目录部分代码基于 [RagFlow](https://github.com/infiniflow/ragflow)（Apache 2.0）改编，包括文档解析（deepdoc）、分词（huqie）、ES 混合检索等模块，特此致谢

---

<div align="center">

**MooCow-Agent** · 从售前咨询到售后救援，一个助手全程领航 🐮⚡

</div>
