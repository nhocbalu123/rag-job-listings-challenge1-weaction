# AVOIDANCE_TABLE.md — Các Lỗi Đã Tránh Được

> Tôi đã tránh được ≥8 lỗi phổ biến khi build FastAPI + Docker + Postgres.  
> Mỗi lỗi có mô tả cách xử lý + code snippet minh chứng.

---

## Lỗi #1 — Base Image Cồng Kềnh

**Vấn đề:** Dùng `python:3.11` full image → ~900MB, chậm pull, tốn disk.  
**Cách xử lý:** Multi-stage build với `python:3.11-slim` → image cuối ~180MB.

```dockerfile
# Stage 1: builder
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Stage 2: runtime — chỉ copy những gì cần
FROM python:3.11-slim AS runtime
COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup app/ ./app/
```

---

## Lỗi #2 — Chạy Container Với Quyền Root

**Vấn đề:** Container chạy root → bảo mật kém, nếu bị exploit có thể chiếm host.  
**Cách xử lý:** Tạo user không có quyền root, switch trước khi chạy app.

```dockerfile
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY --chown=appuser:appgroup app/ ./app/
USER appuser
```

---

## Lỗi #3 — Hardcode Secrets

**Vấn đề:** `DATABASE_URL = "postgresql://postgres:password@..."` trực tiếp trong code.  
**Cách xử lý:** Đọc từ `os.getenv()`, inject qua docker-compose env_file.

```python
# app/database.py
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/ragdb")
```

```yaml
# docker-compose.yml
services:
  api:
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
    env_file:
      - .env
```

`.env` file được thêm vào `.gitignore` — KHÔNG push lên GitHub.

---

## Lỗi #4 — Không Có Healthcheck → API Start Trước DB

**Vấn đề:** `depends_on: db` chỉ đợi container start, không đợi Postgres sẵn sàng → `connection refused`.  
**Cách xử lý:** Kết hợp `healthcheck` trên DB + `condition: service_healthy` + retry logic trong code.

```yaml
# docker-compose.yml
services:
  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 5s
      retries: 10
  api:
    depends_on:
      db:
        condition: service_healthy  # ← đợi DB healthy mới start API
```

```python
# app/database.py — retry logic phòng ngừa edge case
def create_engine_with_retry(url, retries=10, delay=2):
    for attempt in range(retries):
        try:
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            time.sleep(delay)
```

---

## Lỗi #5 — Không Validate Input (Thiếu Pydantic)

**Vấn đề:** Nhận JSON thô không validate → SQL injection, runtime error, dữ liệu rác vào DB.  
**Cách xử lý:** Pydantic v2 schema cho mọi request/response, với `Field` validators.

```python
# app/models.py
class JobCreate(BaseModel):
    title:       str  = Field(..., min_length=2, max_length=200)
    description: str  = Field(..., min_length=10)
    skills:      List[str] = Field(default_factory=list)

    @field_validator("title", "company", "description")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()
```

Test: POST `/jobs` với description rỗng → nhận **422 Unprocessable Entity** tự động.

---

## Lỗi #6 — Monolithic `main.py` (God File)

**Vấn đề:** Nhét tất cả endpoints vào 1 file → khó maintain, test, review.  
**Cách xử lý:** Tổ chức theo router folder, mỗi domain 1 file.

```
app/
├── routers/
│   ├── health.py   # GET /health
│   ├── jobs.py     # POST /jobs, GET /jobs/{id}
│   └── rag.py      # POST /rag/query
└── services/
    ├── embedding.py
    └── rag_service.py
```

```python
# app/main.py — chỉ đăng ký routers
app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(rag.router)
```

---

## Lỗi #7 — Không Có Error Handling Cho 404

**Vấn đề:** Query không tìm thấy record → Python raise `AttributeError` hoặc trả 500.  
**Cách xử lý:** Kiểm tra null, raise `HTTPException` với status code đúng.

```python
# app/routers/jobs.py
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id={job_id} not found.",
        )
    return job
```

---

## Lỗi #8 — Không Scale Workers

**Vấn đề:** Chạy 1 uvicorn worker → bottleneck khi có nhiều request đồng thời.  
**Cách xử lý:** Khởi động với `--workers 2` (hoặc điều chỉnh theo CPU cores).

```dockerfile
# Dockerfile — CMD với nhiều workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

## Tổng Kết

| # | Lỗi | Giải pháp |
|---|-----|-----------|
| 1 | Base image nặng | `python:3.11-slim` + multi-stage build |
| 2 | Chạy root | Non-root user `appuser` |
| 3 | Hardcode secrets | `os.getenv()` + `.env` + `.gitignore` |
| 4 | DB chưa ready | `healthcheck` + `condition: service_healthy` + retry |
| 5 | Không validate input | Pydantic v2 `Field` + `field_validator` |
| 6 | Monolithic code | Router folder structure |
| 7 | Thiếu 404 handling | `HTTPException` với đúng status code |
| 8 | 1 worker duy nhất | `uvicorn --workers 2` |
