from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models import JobListing, QueryLog
from app.services.embedding import embed, cosine_similarity


def retrieve_top_k(db: Session, query: str, top_k: int) -> List[JobListing]:
    """Embed query → cosine-rank all stored jobs → return top-k."""
    query_vec = embed(query)
    jobs: List[JobListing] = db.query(JobListing).all()

    scored: List[Tuple[float, JobListing]] = []
    for job in jobs:
        if job.embedding:
            score = cosine_similarity(query_vec, job.embedding)
            scored.append((score, job))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [job for _, job in scored[:top_k]]


def mock_llm_answer(query: str, jobs: List[JobListing]) -> str:
    """
    Mock LLM response — replace with real call to OpenAI / Groq / local model.
    Interface: context_jobs → structured answer string.
    """
    if not jobs:
        return (
            f'No relevant job listings found for "{query}". '
            "Try adding more jobs via POST /jobs."
        )

    job_summaries = "\n".join(
        f"- [{j.company}] {j.title} @ {j.location or 'Remote'}: "
        f"{', '.join(j.skills[:5]) if j.skills else 'N/A'}"
        for j in jobs
    )

    return (
        f'Based on your query "{query}", here are the most relevant job listings:\n\n'
        f"{job_summaries}\n\n"
        "[Mock LLM — swap with real model call in services/rag_service.py]"
    )


def log_query(
    db: Session,
    query: str,
    top_k: int,
    result_ids: List[int],
    answer: str,
) -> QueryLog:
    log = QueryLog(
        query_text=query,
        top_k=top_k,
        result_ids=result_ids,
        answer=answer,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
