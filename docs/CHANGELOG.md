# Changelog

All notable changes to `rag-job-listings-challenge1-weaction` will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

---

## [1.3.1] - 2026-04-05

### Fixed
- `PermissionError: [Errno 13] Permission denied: '/tmp/huggingface/models--BAAI--bge-reranker-v2-m3'` — Dockerfile now runs `mkdir -p /tmp/huggingface && chown -R appuser:appgroup /tmp/huggingface` before the `USER appuser` switch so that newly-created named volumes inherit the correct ownership from the image
- `RERANKER_PRELOAD_ON_STARTUP` was missing from `docker-compose.yml`; the code-level default of `true` caused the container to attempt a model download at startup before the volume permissions were properly initialized, entering a crash-restart loop — now explicitly set to `"false"` in `docker-compose.yml` (mirroring the existing `EMBEDDING_PRELOAD_ON_STARTUP: "false"` pattern; both models load lazily on first request)

---

## [1.3.0] - 2026-04-05

### Added
- `app/services/reranker.py` — new reranker module using `BAAI/bge-reranker-v2-m3` via `FlagReranker`; thread-safe double-checked locking singleton; handles single-job edge case where `compute_score` returns a bare float
- `retrieve_and_rerank()` in `rag_service.py` — two-stage retrieval pipeline: coarse embed-search (top `RETRIEVAL_K` candidates) → fine reranking → final `top_k` results
- `RETRIEVAL_K` constant (default `20`, overridable via env var) — internal candidate pool size; not exposed in the public API (Option A from the upgrade plan)
- `RERANKER_MODEL` env var — reranker model name (default: `BAAI/bge-reranker-v2-m3`)
- `RERANKER_PRELOAD_ON_STARTUP` env var — controls whether the reranker is preloaded on startup (default: `true`)

### Changed
- `POST /rag/query` now goes through the two-stage pipeline (`retrieve_and_rerank`) instead of direct cosine retrieval (`retrieve_top_k`)
- `app/main.py` lifespan now preloads both the BGE-M3 embedder and the bge-reranker-v2-m3 reranker on startup (each independently toggle-able via env vars)
- API version bumped to `1.3.0`
- `.env.example` updated with `RERANKER_MODEL`, `RERANKER_PRELOAD_ON_STARTUP`, and `RETRIEVAL_K` entries

---

## [1.2.0] - 2026-04-05

### Added
- `EMBEDDING_PRELOAD_ON_STARTUP` env var — controls whether BGE-M3 is preloaded on startup (default: `true`); set to `false` to defer load to first request
- `EMBEDDING_MODEL` env var — embedding model name (default: `BAAI/bge-m3`)
- `GENERATOR_MODEL` env var — LLM model name (default: `gemma-4-31b-it`)
- `RAG_MAX_JOBS_IN_CONTEXT` env var — max job listings passed to LLM context (default: `5`, min: `1`)
- `RAG_MAX_DESCRIPTION_CHARS` env var — max chars per job description in context (default: `1000`, min: `3`)
- `RAG_MAX_TOTAL_CONTEXT_CHARS` env var — max total context chars sent to LLM (default: `4000`, min: `1`)
- `RAG_CONTEXT_SEPARATOR` env var — separator string between job blocks in LLM prompt (default: `\n\n`)
- `UVICORN_WORKERS` env var — number of uvicorn worker processes
- `huggingface_cache` named Docker volume for BGE-M3 model weight persistence across container restarts
- `_get_positive_int_env()` internal helper validates all `RAG_MAX_*` env vars are positive integers at request time, raising descriptive `ValueError` on misconfiguration

### Changed
- Embedding model initialization is now thread-safe via double-checked locking with `threading.Lock`, preventing redundant concurrent downloads on startup
- LLM prompt hardened against prompt injection: job listing content is fenced with `BEGIN_JOB_LISTING`/`END_JOB_LISTING` delimiters and description wrapped in a code block; system instructions explicitly tell the model to ignore listing content as instructions
- Generation error messages now include the exception class name (e.g. `RuntimeError: Error generating answer (APIError): ...`) for faster root-cause identification
- `cosine_similarity()` dimension mismatch error now explains probable root causes (different models or stale DB embeddings)
- Context accumulation correctly accounts for separator length only after the first block, preventing off-by-one over-counting

### Fixed
- Fixed edge case where `RAG_MAX_DESCRIPTION_CHARS` < `len("...")` (3) would produce a negative slice index during description truncation; now enforced by `min_value=3` in config validation
- Fixed Docker Compose comment wording and Dockerfile constant alignment

---

## [1.1.0] - 2026-04-05

### Added
- Real embedding model integration using BGE-M3 via `FlagEmbedding` (replacing mock hash-based vectorizer)
- Real LLM generator integration using Gemma 4 via `google-genai` (replacing mock LLM answer)

### Changed
- Optimized embedding model loading: disabled `use_fp16` for faster CPU inference and implemented FastAPI `lifespan` to preload the BGE-M3 model on startup, eliminating the cold-start delay on the first request.

### Fixed
- Fixed `transformers` version conflict with `FlagEmbedding` by pinning `transformers<4.45.0`
- Fixed HuggingFace cache permission denied error in Docker by setting `HF_HOME` and `TRANSFORMERS_CACHE` to `/tmp/huggingface`
- Fixed silent `None` API key being passed to `genai.Client` when `GEMINI_API_KEY` is unset; now raises a descriptive `ValueError` early with instructions to check `.env`

---

## [1.0.0] - 2026-04-05

### Added
- `POST /jobs` — create a new job listing with automatic hash-based text embedding
- `GET /jobs/{id}` — retrieve a single job by ID, returns 404 if not found
- `GET /jobs` — list all job listings with pagination (`skip`, `limit`)
- `POST /rag/query` — RAG search pipeline: embed query → cosine similarity → top-K relevant jobs → mock LLM answer
- `GET /health` — check API status and PostgreSQL connection
- Pydantic v2 validation on all endpoints — automatically returns 422 on invalid input
- SQLAlchemy ORM with PostgreSQL, auto-creates tables on startup
- Docker multi-stage build using `python:3.11-slim` — final image ~180MB
- `docker-compose.yml` — spins up API + PostgreSQL with a single command
- Database healthcheck in Docker Compose, API retries DB connection up to 10 times on startup
- Non-root user inside container (`appuser`) for security
- All secrets loaded from `.env` via `os.getenv()` — no hardcoded credentials
- Routers split by domain into separate files (`routers/jobs.py`, `routers/rag.py`, `routers/health.py`)
- `AVOIDANCE_TABLE.md` — documents 4 common mistakes avoided in this project
- `docs/RUNBOOK.md` — operational guide covering setup, running, and debugging

---

## [0.1.0] - 2026-04-04

### Added
- Initial project structure and folder layout
- `app/models.py` — SQLAlchemy ORM models and Pydantic v2 schemas
- `app/database.py` — PostgreSQL connection with retry logic on startup
- `app/services/embedding.py` — hash-based text embedding (256 dimensions)
- `app/services/rag_service.py` — cosine similarity retrieval, mock LLM answer generation, and query logging
- `requirements.txt` with pinned dependency versions
- `.env.example` as a template for environment variable setup
- `.gitignore` configured to exclude `.env`, `__pycache__`, and local data folders
- Basic `README.md` with project overview

---

[Unreleased]: https://github.com/YOUR_USERNAME/rag-job-listings-challenge1-weaction/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/YOUR_USERNAME/rag-job-listings-challenge1-weaction/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/YOUR_USERNAME/rag-job-listings-challenge1-weaction/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/YOUR_USERNAME/rag-job-listings-challenge1-weaction/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/YOUR_USERNAME/rag-job-listings-challenge1-weaction/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/YOUR_USERNAME/rag-job-listings-challenge1-weaction/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/YOUR_USERNAME/rag-job-listings-challenge1-weaction/releases/tag/v0.1.0