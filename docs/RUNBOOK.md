# RUNBOOK — RAG Job Listings API

## Table of Contents

1. [Deploy (First Time)](#1-deploy-first-time)
2. [Seed Sample Data](#2-seed-sample-data)
3. [Test RAG Query](#3-test-rag-query)
4. [View Swagger UI](#4-view-swagger-ui)
5. [Logs & Debug](#5-logs--debug)
6. [Scale API Workers](#6-scale-api-workers)
7. [Stop & Clean Up](#7-stop--clean-up)
8. [Environment Variables Reference](#8-environment-variables-reference)
9. [Docker Volume Permissions — Non-Root User](#9-docker-volume-permissions--non-root-user)
10. [Troubleshooting](#10-troubleshooting)

---

## Prerequisites
- Docker ≥ 24.x
- Docker Compose ≥ 2.x
- Ports 8000 and 5432 must be free

---

## 1. Deploy (First Time)

```bash
cp .env.example .env
# Set a strong POSTGRES_PASSWORD in .env, and add your GEMINI_API_KEY
docker-compose up --build -d
docker ps                        # verify both containers are running
curl http://localhost:8000/health
```

**Note:** Both models (BGE-M3 ~2.2 GB and bge-reranker-v2-m3 ~1.1 GB) load lazily on the first request that triggers them (preload is disabled in `docker-compose.yml`). The first call to `/rag/query` will be slower than normal. Monitor download progress with `docker-compose logs -f api`.

Expected: `{"status":"ok","database":"connected"}`

---

## 2. Seed Sample Data

```bash
for job in \
  '{"title":"AI Engineer","company":"FPT Software","location":"HCMC","description":"Build RAG pipelines and deploy LLM APIs using FastAPI and LangChain. Experience with vector databases preferred.","skills":["Python","FastAPI","LangChain","RAG"]}' \
  '{"title":"Backend Engineer","company":"VNG","location":"HCMC","description":"Develop high-performance REST APIs with FastAPI, manage PostgreSQL databases, optimize queries.","skills":["Python","FastAPI","PostgreSQL","Redis"]}' \
  '{"title":"ML Engineer","company":"Grab Vietnam","location":"HCMC","description":"Train and deploy machine learning models. MLOps experience, model serving with FastAPI.","skills":["Python","PyTorch","MLflow","Docker"]}'; do
  curl -s -X POST http://localhost:8000/jobs \
    -H "Content-Type: application/json" \
    -d "$job" | python3 -m json.tool
done
```

---

## 3. Test RAG Query

```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "looking for AI engineer with RAG and LangChain skills", "top_k": 2}'
```

---

## 4. View Swagger UI

Open in browser: `http://localhost:8000/docs`

---

## 5. Logs & Debug

```bash
docker-compose logs api        # API logs
docker-compose logs db         # Postgres logs
docker-compose logs -f api     # Follow live logs
```

---

## 6. Scale API Workers

```bash
# Increase workers via Dockerfile CMD or override:
docker-compose up --scale api=2
```

---

## 7. Stop & Clean Up

```bash
docker-compose down            # stop containers
docker-compose down -v         # stop + delete volumes (data will be lost)
```

---

## 8. Environment Variables Reference

All configurable settings. Copy `.env.example` → `.env` and override as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | *(required)* | PostgreSQL password |
| `POSTGRES_DB` | `ragdb` | PostgreSQL database name |
| `GEMINI_API_KEY` | *(required)* | Google AI Studio key — raises `ValueError` at request time if missing |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace model ID for embedding |
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | HuggingFace model ID for reranker |
| `GENERATOR_MODEL` | `gemma-4-31b-it` | Gemini/Gemma model for answer generation |
| `EMBEDDING_PRELOAD_ON_STARTUP` | `true` | Preload BGE-M3 at startup; set `false` to load lazily on first request |
| `RERANKER_PRELOAD_ON_STARTUP` | `true` | Preload reranker at startup; set `false` to load lazily on first request |
| `RETRIEVAL_K` | `20` | Internal candidate pool size before reranking (not in public API) |
| `RAG_MAX_JOBS_IN_CONTEXT` | `5` | Max jobs sent to LLM (min: 1) |
| `RAG_MAX_DESCRIPTION_CHARS` | `1000` | Max chars per description (min: 3; truncated with `...`) |
| `RAG_MAX_TOTAL_CONTEXT_CHARS` | `4000` | Max total context size sent to LLM (min: 1) |
| `RAG_CONTEXT_SEPARATOR` | `\n\n` | String separator between job blocks in prompt |
| `UVICORN_WORKERS` | `1` | Number of uvicorn worker processes |

---

## 9. Docker Volume Permissions — Non-Root User

### Problem

The container runs as non-root `appuser`. Docker named volumes are created with root ownership on first mount. If the Dockerfile does not pre-create `/tmp/huggingface` with the correct owner, any write to the volume (including lazy model loading) fails with:

```
PermissionError: [Errno 13] Permission denied: '/tmp/huggingface/models--BAAI--bge-reranker-v2-m3'
ERROR:    Application startup failed. Exiting.
```

The container then enters a `Restarting (N)` loop and port 8000 is unreachable.

### Fix (already applied)

**Dockerfile** — create the directory with the correct owner *before* `USER appuser`:

```dockerfile
# Create HF cache dir owned by appuser so the named volume inherits correct permissions
RUN mkdir -p /tmp/huggingface && chown -R appuser:appgroup /tmp/huggingface

COPY --chown=appuser:appgroup app/ ./app/

USER appuser
```

Docker named volumes copy ownership metadata from the image directory when first created empty. The new volume will be owned by `appuser`.

**docker-compose.yml** — disable preload to avoid a crash before the volume is ready:

```yaml
environment:
  EMBEDDING_PRELOAD_ON_STARTUP: "false"
  RERANKER_PRELOAD_ON_STARTUP: "false"
```

### Recovery if the volume was created with wrong permissions

```bash
docker-compose down
docker volume rm rag-job-listings-challenge1-weaction_huggingface_cache
docker-compose up -d --build   # new volume is created with correct permissions from image
```

See [AVOIDANCE_TABLE.md #9](AVOIDANCE_TABLE.md#mistake-9--docker-named-volume-owned-by-root-crashes-non-root-container) for the background on why this happens.

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `connection refused` on API start | DB not yet ready | `depends_on + healthcheck` handles this; check `docker-compose logs db` |
| `422 Unprocessable Entity` | Invalid request schema | Check Pydantic validator; see `/docs` |
| `404 Not Found` for `/jobs/{id}` | ID does not exist | Run `GET /jobs` to list available IDs |
| Container exit code 1 | Missing env var | Check `.env` — especially `GEMINI_API_KEY` and `POSTGRES_PASSWORD` |
| `ValueError: GEMINI_API_KEY ... not set` | API key not set | Add `GEMINI_API_KEY=...` to `.env` |
| `ValueError: RAG_MAX_* must be an integer >= N` | Env var is not a positive integer | Check `RAG_MAX_*` values in `.env` |
| `RuntimeError: Error generating answer (APIError): ...` | Gemini API error | Check API key quota; verify `GENERATOR_MODEL` name |
| `ValueError: Embedding dimension mismatch` | Job embedded with old model, query with new model | Re-embed all jobs after changing `EMBEDDING_MODEL` |
| BGE-M3 slow on first request | BGE-M3 not yet cached (~2.2 GB) | `huggingface_cache` volume persists after first download; monitor via `docker-compose logs -f api` |
| Reranker slow on first request | bge-reranker-v2-m3 not yet cached (~1.1 GB) | `huggingface_cache` volume persists; set `RERANKER_PRELOAD_ON_STARTUP=false` to defer load |
| Reranker returns unchanged results | Fewer than `top_k` jobs in DB | Cosine pool size = `min(RETRIEVAL_K, total jobs)` — add more jobs for reranking to take effect |
| `PermissionError: [Errno 13] Permission denied: '/tmp/huggingface/...'` | Named volume owned by root; non-root `appuser` cannot write | See §9; run `docker-compose down && docker volume rm ..._huggingface_cache && docker-compose up -d --build` |
| API container in `Restarting (N)` loop on startup | Startup crash — most commonly the permission error above | Run `docker logs <container-id>` to confirm; see row above for fix |
