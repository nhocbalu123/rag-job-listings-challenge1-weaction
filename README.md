# RAG Job Listings API — challenge1-weaction

> **Mini RAG pipeline** for job listings: embed job descriptions with BGE-M3 → store in Postgres → coarse cosine retrieval (top 20) → rerank with bge-reranker-v2-m3 → return context + Gemma 4 LLM answer.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-316192?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 🏗️ Architecture

```
POST /jobs          → Embed text (BGE-M3, 1024-dim dense) → Store in Postgres
POST /rag/query     → Embed query → Cosine top-20 → Rerank (bge-reranker-v2-m3) → top-K → Gemma 4 answer
GET  /jobs          → List all job listings (paginated)
GET  /jobs/{id}     → Retrieve single job by ID
GET  /health        → API + DB connectivity check
```

**Two-stage retrieval pipeline:**
```
User Query
│
▼
BGE-M3 Embed (1024-dim)
│
▼
Cosine Search → Top 20 candidates (PostgreSQL JSON scan)
│
▼
bge-reranker-v2-m3 → Top K
│
▼
Gemma 4 (Google GenAI) → Structured Answer + QueryLog
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
│       ├── reranker.py      # bge-reranker-v2-m3 singleton, rerank() function
│       └── rag_service.py   # retrieve_and_rerank (two-stage), generate_answer, log_query
├── docs/
│   ├── AVOIDANCE_TABLE.md   # 9 common mistakes avoided in this project
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
git clone https://github.com/<your-username>/rag-job-listings-challenge1-weaction.git
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

### `POST /jobs` — Create a job listing
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

### `GET /jobs` — List all job listings (paginated)
```bash
curl "http://localhost:8000/jobs?skip=0&limit=10"
```

### `GET /jobs/{id}` — Get job by ID
```bash
curl http://localhost:8000/jobs/1
```

### `GET /health` — Health check
```bash
curl http://localhost:8000/health
# {"status":"ok","database":"connected"}
```

### Test 422 Validation Error (Swagger)
Open `http://localhost:8000/docs` → try `POST /jobs` with an empty `description` → you will receive a `422 Unprocessable Entity`.

---

## ⚙️ Environment Variables

See [docs/RUNBOOK.md §8](./docs/RUNBOOK.md#8-environment-variables-reference) for the full reference table of all configurable settings.

---

## 🔑 Design Decisions

| File | Role |
|------|------|
| `app/services/embedding.py` | BGE-M3 (1024-dim dense vectors) via `FlagEmbedding`; thread-safe double-checked locking |
| `app/services/reranker.py` | bge-reranker-v2-m3 via `FlagReranker`; thread-safe singleton; pairs naturally with BGE-M3 |
| `app/services/rag_service.py` | Two-stage `retrieve_and_rerank()` — coarse top-20 cosine search → fine reranking → top-k; `generate_answer()` calls Gemma 4 |

**Why two-stage?** Cosine similarity on dense vectors is fast but approximate — it ranks by embedding closeness, not by true query–document relevance. The reranker scores each (query, job) pair jointly using a cross-encoder, significantly improving precision at the cost of a small extra inference step on only 20 candidates.

---

## 🛑 Common Mistakes Avoided

See [docs/AVOIDANCE_TABLE.md](./docs/AVOIDANCE_TABLE.md) for details on 9 pitfalls avoided during development.

---

## 📖 Runbook

See [docs/RUNBOOK.md](./docs/RUNBOOK.md) for deploy, debug, and scale instructions.
