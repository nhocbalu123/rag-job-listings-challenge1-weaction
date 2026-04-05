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


def generate_answer(query: str, jobs: List[JobListing]) -> str:
    """
    Generate an answer using Gemma 4 via Google GenAI SDK based on the retrieved jobs.
    """
    if not jobs:
        return (
            f'No relevant job listings found for "{query}". '
            "Try adding more jobs via POST /jobs."
        )

    import os
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Add it to your .env file (see .env.example)."
        )
    client = genai.Client(api_key=api_key)
    GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "gemma-4-31b-it")

    context = "\n\n".join(
        [
            (
                f"Job ID: {j.id}\n"
                f"Title: {j.title}\n"
                f"Company: {j.company}\n"
                f"Location: {j.location or 'Remote'}\n"
                f"Skills: {', '.join(j.skills or [])}\n"
                f"Description: {j.description}"
            )
            for j in jobs
        ]
    )

    prompt = f"""
You are a job-search assistant.
Answer the user's question using only the job listings below.
If the answer is uncertain, say so.
Prefer concise, factual answers.

User query:
{query}

Job listings:
{context}
"""

    try:
        response = client.models.generate_content(
            model=GENERATOR_MODEL,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Error generating answer: {str(e)}"


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
