from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import retrieve_and_rerank, generate_answer, log_query

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="RAG: retrieve relevant jobs + generate answer",
)
def rag_query(payload: RAGQueryRequest, db: Session = Depends(get_db)):
    """
    Two-stage retrieval pipeline:
    1. Embed the query with BGE-M3.
    2. Cosine-search Postgres for the top RETRIEVAL_K candidates.
    3. Rerank candidates with bge-reranker-v2-m3; keep only top_k.
    4. Pass the reranked context to Gemma (Google GenAI) to generate an answer.
    5. Log the query + result to DB for tracking.
    """
    top_jobs = retrieve_and_rerank(db, payload.query, payload.top_k)
    try:
        answer = generate_answer(payload.query, top_jobs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
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
