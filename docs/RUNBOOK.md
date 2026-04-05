# RUNBOOK — RAG Job Listings API

## Prerequisites
- Docker ≥ 24.x
- Docker Compose ≥ 2.x
- Port 8000 và 5432 không bị chiếm

---

## 1. Deploy (First Time)

```bash
cp .env.example .env
# Đổi POSTGRES_PASSWORD thành password mạnh trong .env
docker-compose up --build -d
docker ps                        # kiểm tra cả 2 container đang running
curl http://localhost:8000/health
```

**Lưu ý:** Lần đầu khởi động, API container có thể mất 1-2 phút để tải và preload model BGE-M3 (khoảng 2.2GB) vào RAM. Hãy kiểm tra logs (`docker-compose logs -f api`) để xem khi nào ứng dụng sẵn sàng.

Expected: `{"status":"ok","database":"connected"}`

---

## 2. Seed Sample Data

```bash
# Thêm vài job listings
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

Mở trình duyệt: `http://localhost:8000/docs`

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
# Tăng worker trong Dockerfile CMD hoặc override:
docker-compose up --scale api=2
```

---

## 7. Stop & Clean Up

```bash
docker-compose down            # stop containers
docker-compose down -v         # stop + xóa volumes (data sẽ mất)
```

---

## 8. Upgrade Embedding Model (Đã thực hiện)

Sửa `app/services/embedding.py`:

```python
# Thread-safe lazy load with double-checked locking (see AVOIDANCE_TABLE.md #6)
from threading import Lock
from FlagEmbedding import BGEM3FlagModel
import os

_model = None
_model_lock = Lock()

def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
                # use_fp16=False: faster and safer on CPU (see AVOIDANCE_TABLE.md #3)
                _model = BGEM3FlagModel(model_name, use_fp16=False)
    return _model

def embed(text: str) -> list[float]:
    """Returns a 1024-dim dense vector using BGE-M3."""
    model = get_model()
    output = model.encode([text], return_dense=True, return_sparse=False, return_colbert_vecs=False)
    vec = output['dense_vecs'][0]
    return vec.tolist()
```

Đã thêm vào requirements.txt: `FlagEmbedding>=1.2.10` và `transformers<4.45.0`

---

## 9. Thay Mock LLM bằng Real LLM (Đã thực hiện)

Sửa `app/services/rag_service.py` → `generate_answer()`:

```python
from google import genai
import os

def generate_answer(query: str, jobs) -> str:
    if not jobs:
        return f'No relevant job listings found for "{query}".'

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Add it to your .env file (see .env.example)."
        )
    client = genai.Client(api_key=api_key)

    # All RAG limits are configurable via env vars (see AVOIDANCE_TABLE.md #7, #8)
    GENERATOR_MODEL         = os.getenv("GENERATOR_MODEL", "gemma-4-31b-it")
    max_jobs_in_context     = _get_positive_int_env("RAG_MAX_JOBS_IN_CONTEXT", 5)
    max_description_chars   = _get_positive_int_env("RAG_MAX_DESCRIPTION_CHARS", 1000, min_value=3)
    max_total_context_chars = _get_positive_int_env("RAG_MAX_TOTAL_CONTEXT_CHARS", 4000)
    context_separator       = os.getenv("RAG_CONTEXT_SEPARATOR", "\n\n")

    # Prompt-injection hardening: fence each listing (see AVOIDANCE_TABLE.md #5)
    context_parts = []
    for j in jobs[:max_jobs_in_context]:
        job_context = (
            "BEGIN_JOB_LISTING\n"
            f"Title: {j.title}\n"
            "Description:\n"
            "```text\n"
            f"{description}\n"
            "```\n"
            "END_JOB_LISTING"
        )
        context_parts.append(job_context)
    context = context_separator.join(context_parts)

    try:
        response = client.models.generate_content(model=GENERATOR_MODEL, contents=prompt)
        return (response.text or "").strip()
    except Exception as e:
        raise RuntimeError(f"Error generating answer ({type(e).__name__}): {e}") from e
```

Đã thêm `GEMINI_API_KEY` và các `RAG_MAX_*` vars vào `.env`.

---

## 10. Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | *(required)* | Google AI Studio key — raise `ValueError` at request time if missing |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace model ID for embedding |
| `GENERATOR_MODEL` | `gemma-4-31b-it` | Gemini/Gemma model for answer generation |
| `EMBEDDING_PRELOAD_ON_STARTUP` | `true` | Preload BGE-M3 at startup; set `false` to load lazily on first request |
| `RAG_MAX_JOBS_IN_CONTEXT` | `5` | Max jobs sent to LLM (min: 1) |
| `RAG_MAX_DESCRIPTION_CHARS` | `1000` | Max chars per description (min: 3; truncated with `...`) |
| `RAG_MAX_TOTAL_CONTEXT_CHARS` | `4000` | Max total context size sent to LLM (min: 1) |
| `RAG_CONTEXT_SEPARATOR` | `\n\n` | String separator between job blocks in prompt |
| `UVICORN_WORKERS` | `1` | Number of uvicorn worker processes |

---

## 11. Các Lỗi Thường Gặp

| Triệu chứng | Nguyên nhân | Giải pháp |
|-------------|-------------|-----------|
| `connection refused` khi API start | DB chưa ready | `depends_on + healthcheck` đã xử lý; xem `docker-compose logs db` |
| `422 Unprocessable Entity` | Input sai schema | Kiểm tra Pydantic validator, xem `/docs` |
| `404 Not Found` cho `/jobs/{id}` | ID không tồn tại | Chạy `GET /jobs` để xem danh sách |
| Container exit code 1 | Env var thiếu | Kiểm tra `.env` file — đặc biệt `GEMINI_API_KEY` và `POSTGRES_PASSWORD` |
| `ValueError: GEMINI_API_KEY ... not set` | API key chưa set | Thêm `GEMINI_API_KEY=...` vào `.env` |
| `ValueError: RAG_MAX_* must be an integer >= N` | Env var không phải số nguyên dương | Kiểm tra giá trị của `RAG_MAX_*` trong `.env` |
| `RuntimeError: Error generating answer (APIError): ...` | Gemini API lỗi | Kiểm tra API key còn quota; xem tên model trong `GENERATOR_MODEL` |
| `ValueError: Embedding dimension mismatch` | Job được embed với model cũ, query embed với model mới | Re-embed toàn bộ jobs sau khi thay đổi `EMBEDDING_MODEL` |
| Model load chậm lần đầu | BGE-M3 chưa cache (`~2.2GB`) | `huggingface_cache` volume lưu lại sau lần đầu; xem `docker-compose logs -f api` |
