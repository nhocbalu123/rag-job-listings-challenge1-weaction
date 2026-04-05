from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.database import Base

# ── SQLAlchemy ORM ──────────────────────────────────────────────────────────

class JobListing(Base):
    __tablename__ = "job_listings"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(200), nullable=False)
    company     = Column(String(200), nullable=False)
    location    = Column(String(200), nullable=True)
    description = Column(Text, nullable=False)
    skills      = Column(JSON, default=list)
    embedding   = Column(JSON, nullable=True)   # stored as list[float]
    created_at  = Column(DateTime, default=datetime.utcnow)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id          = Column(Integer, primary_key=True, index=True)
    query_text  = Column(Text, nullable=False)
    top_k       = Column(Integer, default=3)
    result_ids  = Column(JSON, default=list)
    answer      = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


# ── Pydantic Schemas ────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title:       str  = Field(..., min_length=2, max_length=200, example="Senior AI Engineer")
    company:     str  = Field(..., min_length=1, max_length=200, example="TechCorp Vietnam")
    location:    Optional[str] = Field(None, max_length=200, example="Ho Chi Minh City")
    description: str  = Field(..., min_length=10, example="Build and deploy LLM-powered products...")
    skills:      List[str] = Field(default_factory=list, example=["Python", "FastAPI", "LangChain"])

    @field_validator("title", "company", "description")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class JobResponse(BaseModel):
    id:          int
    title:       str
    company:     str
    location:    Optional[str]
    description: str
    skills:      List[str]
    created_at:  datetime

    model_config = {"from_attributes": True}


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, example="AI engineer with Python and FastAPI")
    top_k: int = Field(default=3, ge=1, le=10)


class RAGQueryResponse(BaseModel):
    query:        str
    top_k:        int
    context_jobs: List[JobResponse]
    answer:       str
    query_id:     int
