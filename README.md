<div align="center">

# 🐮 MooCow-Agent

### Full-Chain Intelligent Assistant for New Energy Vehicles · Multi-Agent + Skill Plugins + RAG

**From pre-sales consultation to after-sales rescue — one assistant, all the way.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Ant Design](https://img.shields.io/badge/Ant_Design-5-0170FE?logo=antdesign&logoColor=white)](https://ant.design/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek_V4_Pro-4D6BFE)](https://www.deepseek.com/)
[![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.11-FEC514?logo=elasticsearch&logoColor=black)](https://www.elastic.co/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

**English** · [简体中文](README.zh-CN.md)

[Quick Start](#-quick-start) · [Features](#-features) · [Architecture](#-architecture) · [Skill Plugins](#-skill-plugins) · [Project Structure](#-project-structure) · [FAQ](#-faq)

</div>

---

## 📖 Introduction

MooCow-Agent is a **full-chain intelligent customer-service system** for the new energy vehicle (NEV) industry, built on a multi-agent architecture:

| Scenario | Capabilities |
|----------|--------------|
| 🛒 **Pre-sales** | Vehicle consultation, model recommendations, config comparison, pricing & financing, test-drive booking |
| 🔧 **After-sales** | Fault diagnosis, repair advice, maintenance schedules, charging issues, battery health, warranty policies |
| 🌐 **Real-time Info** | Stock prices, weather, news via live web search |
| 🗺️ **Navigation** | Nearby charging/ service stations, route planning (Baidu Maps) |
| 📚 **Private Knowledge Base** | Enterprise document upload, hybrid retrieval (company-shared + personal), answer sourcing |

A built-in **Deep Think toggle** switches the orchestrator between a reasoning model (with streamed thinking process) and a fast model for direct answers.

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (with Docker Compose)
- Node.js ≥ 18 (for the frontend dev server)

### One-click Launch

```bash
git clone <your-repo-url> moocow-agent
cd moocow-agent
./start.sh          # choose 1: one-click launch
```

The script automatically:

1. Generates missing `.env` files from `.env.example` templates
2. Builds and starts all Docker services (backend / RAG / ES / PG / Redis)
3. Installs frontend dependencies and starts the dev server in the background

After startup:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5181 |
| Backend API | http://localhost:8080/docs |
| RAG Service | http://localhost:8001/docs |

> ⚠️ **The only manual step**: edit `backend/.env` and fill in real model API keys. Services will start without them, but AI chat won't work.

### Manual Setup

<details>
<summary>Steps without the one-click script</summary>

```bash
# 1. Configure environments
cp backend/.env.example backend/.env       # fill in real keys
cp rag-service/.env.example rag-service/.env
cp frontend/.env.example frontend/.env

# 2. Start Docker services
docker compose up -d

# 3. Start the frontend
cd frontend && npm install && npm run dev
```

</details>

## ✨ Features

### Multi-Agent Collaboration

| Agent | Responsibility | Model |
|-------|----------------|-------|
| **Orchestrator** | Intent recognition, task routing, result aggregation | DeepSeek-V4-Pro (deep think) / DeepSeek-V3 (fast) |
| **Full-Chain Agent** | Pre-sales + after-sales + real-time info | DeepSeek-V4-Pro |
| **Service Station Expert** | Charging/ service station lookup, POI navigation | DeepSeek-V4-Pro |

### Skill Plugins (On-Demand Loading)

Inspired by Claude Code's Skill design: the system prompt only routes scenarios, while domain know-how lives in **Skills**. The model calls a `load_skill` tool to inject the right skill into the conversation. **Adding a capability = adding one Markdown file — zero code changes.**

### Hybrid RAG Knowledge Base

- **Dual-library retrieval**: company-shared (`company_kb`) + user personal library merged in one query
- **Three-stage ranking**: ES RRF fusion (BM25 + KNN) → SiliconFlow `bge-reranker-v2-m3` semantic reranking → local hybrid-similarity fallback
- **Document management**: upload → deepdoc parsing (ONNX models) → indexing, fully visualized
- **Answer sourcing**: referenced documents appear below each answer — click to expand the exact retrieved snippet

### Immersive Chat Experience

- Streaming: thinking (collapsible) / tool calls / final answer / references — four event types pushed in real time
- Dark theme: DeepSeek-dark-inspired — pure black canvas, gray layering, a single brand blue
- Thinking visualization: thinking-orbs dot-sphere animations (idle `solving` / streaming `working`), glowing input border
- Day-grouped session list, stop generation, regenerate, one-click copy

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React 18 + Ant Design)                           │
│  Chat UI / Document Management · SSE stream parsing         │
│  (THINKING · PROCESS · ANSWER · REFERENCE)                  │
└───────────────────────────┬─────────────────────────────────┘
                            │ SSE
┌───────────────────────────▼─────────────────────────────────┐
│  Backend (FastAPI + openai-agents)                          │
│  · Routes: auth / session / chat / repository               │
│  · Orchestrator: intent recognition · task routing          │
│  · Full-Chain Agent: sales · after-sales · real-time info   │
│  · Service Station Expert: Baidu Maps navigation            │
│  · Skill Loader: sales · aftersales                         │
│  · RAG Client · Web Search MCP (DashScope WebSearch)        │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
┌─────────────▼─────────────┐   ┌─────────────▼───────────────┐
│  RAG Service               │   │  Infrastructure             │
│  · Hybrid retrieval        │   │  · Elasticsearch 8.11       │
│  · RRF coarse ranking      │   │  · PostgreSQL 15            │
│  · Rerank semantic ranking │   │  · Redis 7                  │
│  · deepdoc parsing         │   │                             │
└───────────────────────────┘   └─────────────────────────────┘
```

## 🧩 Skill Plugins

```
User asks: "Budget is 200k, recommend a family SUV"
    ↓
Full-Chain Agent: scenario detection → pre-sales
    ↓
Calls load_skill("sales") → sales Skill injected into conversation
    ↓
Executes strictly by the Skill (needs discovery → RAG retrieval → recommendation)
    ↓
Output: structured answer + referenced sources
```

Add a new skill by creating one folder under `backend/skills/`:

```
skills/
├── sales_skill/
│   └── SKILL.md          # frontmatter description + domain instructions
└── aftersales_skill/
    └── SKILL.md
```

The system scans the directory at startup and injects the skill catalog into the tool description; the model loads skills on demand.

## 📁 Project Structure

```
moocow-agent/
├── frontend/              # Frontend (Vite + React 18 + TS + Ant Design)
│   └── src/
│       ├── pages/         # chat / login / repository
│       ├── components/    # sender / thinking-block / session-list ...
│       └── store/         # valtio state management
├── backend/               # Backend (FastAPI + multi-agent)
│   ├── multi_agent/       # Orchestrator / Full-Chain / Service Station agents
│   ├── prompts/           # System prompts
│   ├── skills/            # ★ Skill plugins (sales / after-sales)
│   ├── infrastructure/    # AI clients / Skill loader / local tools / MCP
│   ├── api/               # Routes (auth / chat / session / repository)
│   └── services/          # Business services (streaming / session)
├── rag-service/           # RAG service (retrieval / parsing / indexing, adapted from RagFlow)
├── docker-compose.yml     # Full service orchestration
└── start.sh               # One-click startup script
```

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|--------------|
| Frontend | Vite 6 · React 18 · TypeScript 5 · Ant Design 5 · valtio · SCSS Modules |
| Backend | FastAPI · openai-agents · DeepSeek-V4-Pro / V3 (SiliconFlow) |
| RAG | Elasticsearch 8.11 · RRF hybrid retrieval · bge-reranker-v2-m3 · deepdoc (ONNX) · huqie tokenizer |
| Communication | SSE streaming (4 event types) · MCP (DashScope WebSearch / Baidu Maps) |
| Infrastructure | Docker Compose · PostgreSQL 15 · Redis 7 · JWT auth |

## 🔧 Configuration

All sensitive config lives in `.env` files; the repository ships only `.env.example` templates:

| File | Contents |
|------|----------|
| `backend/.env` | LLM API keys, model names, MCP search key, JWT secret |
| `rag-service/.env` | RAG models, ES password, DB connection, admin whitelist |
| `frontend/.env` | API proxy address |

```bash
cp backend/.env.example backend/.env      # then fill in real keys
```

## ❓ FAQ

<details>
<summary><b>Chat errors or empty answers after startup?</b></summary>

Check that `SF_API_KEY` in `backend/.env` is replaced with a real key; inspect logs via `docker compose logs -f backend`.
</details>

<details>
<summary><b>Document upload fails?</b></summary>

- Parsing a large PDF for the first time may take 1–2 minutes (timeout relaxed to 120s)
- Duplicate filenames are rejected — delete the old file first
- Uploads to the shared library are admin-only (`ADMIN_USER_IDS` in `rag-service/.env`)
</details>

<details>
<summary><b>Why can't my answers reference my documents?</b></summary>

Retrieval scope = company-shared library + the current user's personal library. Make sure the document was uploaded successfully (visible in the document manager) and that you're logged in with the same account that uploaded it.
</details>

<details>
<summary><b>Baidu Maps navigation unavailable?</b></summary>

Fill in a real `BAIDUMAP_AK` in `backend/.env`.
</details>

## 📄 License & Credits

- Backend and frontend code are released under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- Parts of `rag-service/` are adapted from [RagFlow](https://github.com/infiniflow/ragflow) (Apache 2.0), including document parsing (deepdoc), tokenization (huqie), and ES hybrid retrieval modules. Our sincere thanks to the RagFlow team.

---

<div align="center">

**MooCow-Agent** · From pre-sales consultation to after-sales rescue, one assistant all the way 🐮⚡

</div>
