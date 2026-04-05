from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from app.database import Base, engine
from app.routers import health, jobs, rag
from app.services.embedding import get_model

@asynccontextmanager
async def lifespan(app: FastAPI):
    preload_enabled = os.getenv("EMBEDDING_PRELOAD_ON_STARTUP", "true").lower() == "true"
    if preload_enabled:
        # Pre-load the embedding model on startup so the first request is fast
        print("Pre-loading BGE-M3 embedding model...")
        get_model()
        print("Model loaded successfully!")
    else:
        print("Embedding model preload disabled by EMBEDDING_PRELOAD_ON_STARTUP.")
    yield

# Create tables on startup (use Alembic for production migrations)
# checkfirst=True prevents errors if tables already exist
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not create tables on startup: {e}")

app = FastAPI(
    title="RAG Job Listings API",
    description=(
        "A mini RAG pipeline for job listings: embed job descriptions, "
        "store in Postgres, retrieve by semantic similarity, generate answers."
    ),
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(rag.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "RAG Job Listings API",
        "docs":    "/docs",
        "health":  "/health",
    }
