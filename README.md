# RAG Job Listings API — challenge1-weaction

> **Mini RAG pipeline** cho job listings: embed mô tả công việc → lưu Postgres → truy vấn semantic similarity → trả về context + mock LLM answer.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 🏗️ Architecture

```
POST /jobs          → Embed text (bag-of-words, 256-dim) → Store in Postgres
POST /rag/query     → Embed query → Cosine similarity → Top-K jobs → Mock LLM answer
GET  /jobs/{id}     → Retrieve single job by ID
GET  /health        → API + DB connectivity check
```

```
rag-job-listings-challenge1-weaction/
├── app/
│   ├── main.py              # FastAPI app, router registration
│   ├── database.py          # SQLAlchemy engine + DB retry on startup
│   ├── models.py            # SQLAlchemy ORM + Pydantic schemas
│   ├── routers/
│   │   ├── health.py        # GET /health
│   │   ├── jobs.py          # POST /jobs, GET /jobs/{id}, GET /jobs
│   │   └── rag.py           # POST /rag/query
│   └── services/
│       ├── embedding.py     # embed() — swap with real model here
│       └── rag_service.py   # retrieve_top_k, mock_llm_answer, log_query
├── docs/RUNBOOK.md
├── AVOIDANCE_TABLE.md
├── Dockerfile               # Multi-stage, python:3.11-slim, non-root user
├── docker-compose.yml       # API + Postgres, healthcheck, env injection
├── requirements.txt
└── .env.example
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

## 🔑 Thay thế Embedding & LLM

| File | Thay đổi |
|------|----------|
| `app/services/embedding.py` | Đã thay hàm `embed()` bằng model BGE-M3 qua `FlagEmbedding` |
| `app/services/rag_service.py` | Đã thay hàm `mock_llm_answer()` bằng `generate_answer()` gọi Gemma-4 qua Google GenAI SDK |

---

## 🛑 Các Sai Lầm Đã Tránh

Xem chi tiết trong [AVOIDANCE_TABLE.md](./docs/AVOIDANCE_TABLE.md).

---

## 📖 Runbook

Xem [docs/RUNBOOK.md](./docs/RUNBOOK.md) cho hướng dẫn deploy, debug, và scale.
