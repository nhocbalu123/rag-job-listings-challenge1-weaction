# AVOIDANCE_TABLE.md — Các Lỗi Đã Tránh Được

> Tôi đã tránh được các lỗi phổ biến khi build FastAPI + Docker + Postgres.  
> Mỗi lỗi có mô tả cách xử lý + code snippet minh chứng.

---

## Lỗi #1 — Xung Đột Version Của Thư Viện `transformers`

**Vấn đề:** Khi sử dụng `FlagEmbedding` để gọi model BGE-M3, thư viện này phụ thuộc vào `transformers`. Ở các phiên bản `transformers` mới (>= 4.45.0), hàm `is_torch_fx_available` đã bị xóa, gây ra lỗi `ImportError: cannot import name 'is_torch_fx_available'` khi khởi động app.  
**Cách xử lý:** Pin cứng phiên bản của `transformers` xuống dưới 4.45.0 trong `requirements.txt`.

```txt
# requirements.txt
FlagEmbedding>=1.2.10
transformers<4.45.0
```

---

## Lỗi #2 — Lỗi Permission Khi Tải Model HuggingFace Trong Docker

**Vấn đề:** Container chạy dưới quyền user `appuser` (non-root) không có thư mục home thực sự (`/nonexistent`). Khi `FlagEmbedding` cố gắng tải weights của model về cache mặc định (`~/.cache/huggingface/hub`), nó sẽ báo lỗi permission denied.  
**Cách xử lý:** Ghi đè đường dẫn cache của HuggingFace và Transformers sang thư mục `/tmp` (nơi mọi user đều có quyền ghi) bằng cách truyền environment variables trong `docker-compose.yml`.

```yaml
# docker-compose.yml
services:
  api:
    environment:
      HF_HOME: /tmp/huggingface
      TRANSFORMERS_CACHE: /tmp/huggingface
```

---

## Lỗi #3 — Lazy Load Model Nặng Gây Chậm Request Đầu Tiên

**Vấn đề:** Model BGE-M3 khá nặng (~2.2GB). Nếu load model ngay trong hàm `embed()` ở request đầu tiên (lazy loading), request `POST /jobs` đầu tiên sẽ bị treo hơn 1 phút. Ngoài ra, việc dùng `use_fp16=True` trên CPU thường không được tối ưu và có thể làm giảm hiệu năng.  
**Cách xử lý:** Sử dụng event `lifespan` của FastAPI để preload model vào bộ nhớ ngay khi server startup. Đồng thời tắt `use_fp16=False` để tăng tốc độ inference trên CPU.

```python
# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Pre-loading BGE-M3 embedding model...")
    get_model()  # Load model vào RAM
    yield

app = FastAPI(lifespan=lifespan)
```

---

## Tổng Kết

| # | Lỗi | Giải pháp |
|---|-----|-----------|
| 1 | Lỗi import `transformers` | Pin version `transformers<4.45.0` |
| 2 | Lỗi permission tải model HF | Set env `HF_HOME=/tmp/huggingface` |
| 3 | Request đầu tiên quá chậm | Preload model bằng FastAPI `lifespan` + `use_fp16=False` |