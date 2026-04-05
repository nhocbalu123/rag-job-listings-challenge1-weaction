# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Lỗi #1 tránh: dùng slim thay vì python:3.11 full (~900MB → ~180MB)
WORKDIR /app

# Cài thư viện vào prefix riêng để copy sang stage 2
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Lỗi #2 tránh: không chạy container với quyền root
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages từ builder
COPY --from=builder /install /usr/local

# Create HF cache dir owned by appuser so the named volume inherits correct permissions
RUN mkdir -p /tmp/huggingface && chown -R appuser:appgroup /tmp/huggingface

# Copy source code
COPY --chown=appuser:appgroup app/ ./app/

USER appuser

EXPOSE 8000

# Worker count is configurable to avoid high memory usage when the embedding model is loaded per worker
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1}"]
