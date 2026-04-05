from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import retrieve_top_k, generate_answer, log_query

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="RAG: retrieve relevant jobs + generate answer",
)
def rag_query(payload: RAGQueryRequest, db: Session = Depends(get_db)):
    """
    1. Embeds the query text.
    2. Retrieves top-k semantically similar job listings from Postgres.
    3. Passes context to Gemma LLM (via Google GenAI) to generate an answer.
    4. Logs the query + result to DB for tracking.
    """
    top_jobs = retrieve_top_k(db, payload.query, payload.top_k)
    answer   = generate_answer(payload.query, top_jobs)
    log      = log_query(
        db,
        query=payload.query,
        top_k=payload.top_k,
        result_ids=[j.id for j in top_jobs],
        answer=answer,
    )
    return RAGQueryResponse(
        query=payload.query,
        top_k=payload.top_k,
        context_jobs=top_jobs,
        answer=answer,
        query_id=log.id,
    )
