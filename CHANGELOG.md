# Changelog

All notable changes to `rag-job-listings-challenge1-weaction` will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]
> Changes in progress, not yet released

### Added
- Real embedding model integration (replacing mock hash-based vectorizer)
- Authentication endpoint for API access control

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
- `AVOIDANCE_TABLE.md` — documents 8 common mistakes avoided in this project
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