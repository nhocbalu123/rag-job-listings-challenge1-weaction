from fastapi import FastAPI
from app.database import Base, engine
from app.routers import health, jobs, rag

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
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
