# RAG Job Listings API — challenge1-weaction

> **Mini RAG pipeline** cho job listings: embed mô tả công việc bằng BGE-M3 → lưu Postgres → truy vấn semantic similarity → trả về context + Gemma 4 LLM answer.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 🏗️ Architecture

```
POST /jobs          → Embed text (BGE-M3, 1024-dim dense) → Store in Postgres
POST /rag/query     → Embed query → Cosine similarity → Top-K jobs → Gemma 4 LLM answer
GET  /jobs          → List all job listings (paginated)
GET  /jobs/{id}     → Retrieve single job by ID
GET  /health        → API + DB connectivity check
```

```
rag-job-listings-challenge1-weaction/
├── app/
│   ├── main.py              # FastAPI app, lifespan model preload, router registration
│   ├── database.py          # SQLAlchemy engine + DB retry on startup
│   ├── models.py            # SQLAlchemy ORM + Pydantic schemas
│   ├── routers/
│   │   ├── health.py        # GET /health
│   │   ├── jobs.py          # POST /jobs, GET /jobs/{id}, GET /jobs
│   │   └── rag.py           # POST /rag/query
│   └── services/
│       ├── embedding.py     # BGE-M3 embedding (1024-dim), thread-safe lazy load
│       └── rag_service.py   # retrieve_top_k, generate_answer (Gemma 4), log_query
├── docs/
│   ├── AVOIDANCE_TABLE.md   # 8 common mistakes avoided in this project
│   ├── CHANGELOG.md         # Version history
│   └── RUNBOOK.md           # Deploy, debug, and scale guide
├── Dockerfile               # Multi-stage, python:3.11-slim, non-root user
├── docker-compose.yml       # API + Postgres, healthcheck, HF cache volume
├── requirements.txt
└── .env.example             # All configurable env vars with defaults
```

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/rag-job-listings-challenge1-weaction.git
cd rag-job-listings-challenge1-weaction

# 2. Configure env
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY (create one in Google AI Studio) or configure local models
# Optional: tune EMBEDDING_PRELOAD_ON_STARTUP/RAG_MAX_* and UVICORN_WORKERS for memory & latency

# 3. Build & run
docker-compose up --build -d

# 4. Verify
docker ps
curl http://localhost:8000/health

```

---

## 📡 API Endpoints

### `POST /jobs` — Thêm job listing
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior AI Engineer",
    "company": "TechCorp Vietnam",
    "location": "Ho Chi Minh City",
    "description": "Build and deploy LLM-powered products using FastAPI, LangChain, and RAG pipelines.",
    "skills": ["Python", "FastAPI", "LangChain", "RAG", "PostgreSQL"]
  }'
```

### `POST /rag/query` — RAG semantic search
```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "AI engineer with Python and FastAPI experience", "top_k": 3}'
```

### `GET /jobs/{id}` — Lấy job theo ID
```bash
curl http://localhost:8000/jobs/1
```

### `GET /health` — Health check
```bash
curl http://localhost:8000/health
# {"status":"ok","database":"connected"}
```

### Test 422 Validation Error (Swagger)
Mở `http://localhost:8000/docs` → thử POST /jobs với `description` bỏ trống → nhận 422 Unprocessable Entity.

---

## ⚙️ Environment Variables

All tuneable settings are loaded from `.env` (copy from `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | *(required)* | PostgreSQL password |
| `POSTGRES_DB` | `ragdb` | PostgreSQL database name |
| `GEMINI_API_KEY` | *(required)* | Google AI Studio API key |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace model name for BGE-M3 |
| `GENERATOR_MODEL` | `gemma-4-31b-it` | Gemini/Gemma model for answer generation |
| `EMBEDDING_PRELOAD_ON_STARTUP` | `true` | Preload BGE-M3 into RAM on startup (set `false` to defer) |
| `RAG_MAX_JOBS_IN_CONTEXT` | `5` | Max job listings passed to LLM context |
| `RAG_MAX_DESCRIPTION_CHARS` | `1000` | Max chars per job description (min: 3, truncated with `...`) |
| `RAG_MAX_TOTAL_CONTEXT_CHARS` | `4000` | Max total chars in LLM context window |
| `RAG_CONTEXT_SEPARATOR` | `\n\n` | Separator between job blocks in context |
| `UVICORN_WORKERS` | `1` | Number of uvicorn worker processes |

---

## 🔑 Thay thế Embedding & LLM

| File | Thay đổi |
|------|----------|
| `app/services/embedding.py` | BGE-M3 (1024-dim dense vectors) qua `FlagEmbedding`; thread-safe double-checked locking |
| `app/services/rag_service.py` | `generate_answer()` gọi Gemma 4 qua Google GenAI SDK; prompt hardened against injection; runtime config via env vars |

---

## 🛑 Các Sai Lầm Đã Tránh

Xem chi tiết trong [AVOIDANCE_TABLE.md](./docs/AVOIDANCE_TABLE.md).

---

## 📖 Runbook

Xem [docs/RUNBOOK.md](./docs/RUNBOOK.md) cho hướng dẫn deploy, debug, và scale.
