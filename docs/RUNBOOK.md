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
# Đã thay thế embed() bằng BGE-M3
from FlagEmbedding import BGEM3FlagModel

# use_fp16=False: faster and safer on CPU (see AVOIDANCE_TABLE.md #3)
_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)

def embed(text: str) -> list[float]:
    output = _model.encode([text], return_dense=True, return_sparse=False, return_colbert_vecs=False)
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
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "gemma-4-31b-it")
    # ... build context and prompt ...
    response = client.models.generate_content(
        model=GENERATOR_MODEL,
        contents=prompt,
    )
    return response.text.strip()
```

Đã thêm `GEMINI_API_KEY` vào `.env`.

---

## 10. Các Lỗi Thường Gặp

| Triệu chứng | Nguyên nhân | Giải pháp |
|-------------|-------------|-----------|
| `connection refused` khi API start | DB chưa ready | `depends_on + healthcheck` đã xử lý; xem logs db |
| `422 Unprocessable Entity` | Input sai schema | Kiểm tra Pydantic validator, xem `/docs` |
| `404 Not Found` cho `/jobs/{id}` | ID không tồn tại | Chạy `GET /jobs` để xem danh sách |
| Container exit code 1 | Env var thiếu | Kiểm tra `.env` file đủ chưa |
