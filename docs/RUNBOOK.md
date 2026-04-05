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

## 8. Upgrade Embedding Model

Sửa `app/services/embedding.py`:

```python
# Thay thế embed() bằng sentence-transformers
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")

def embed(text: str) -> list[float]:
    return _model.encode(text).tolist()
```

Thêm vào requirements.txt: `sentence-transformers==2.7.0`

---

## 9. Thay Mock LLM bằng Real LLM

Sửa `app/services/rag_service.py` → `mock_llm_answer()`:

```python
import openai, os

def mock_llm_answer(query: str, jobs) -> str:
    context = "\n".join(f"- {j.title} at {j.company}: {j.description[:200]}" for j in jobs)
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a job search assistant."},
            {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}\n\nAnswer:"}
        ]
    )
    return resp.choices[0].message.content
```

Thêm `OPENAI_API_KEY` vào `.env`.

---

## 10. Các Lỗi Thường Gặp

| Triệu chứng | Nguyên nhân | Giải pháp |
|-------------|-------------|-----------|
| `connection refused` khi API start | DB chưa ready | `depends_on + healthcheck` đã xử lý; xem logs db |
| `422 Unprocessable Entity` | Input sai schema | Kiểm tra Pydantic validator, xem `/docs` |
| `404 Not Found` cho `/jobs/{id}` | ID không tồn tại | Chạy `GET /jobs` để xem danh sách |
| Container exit code 1 | Env var thiếu | Kiểm tra `.env` file đủ chưa |
