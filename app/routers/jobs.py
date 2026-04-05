from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import JobCreate, JobListing, JobResponse
from app.services.embedding import embed

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a job listing and embed it",
)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    """
    Accepts a job listing, generates an embedding from
    `title + description + skills`, persists to Postgres.
    """
    combined_text = (
        f"{payload.title} {payload.description} {' '.join(payload.skills)}"
    )
    job = JobListing(
        title=payload.title,
        company=payload.company,
        location=payload.location,
        description=payload.description,
        skills=payload.skills,
        embedding=embed(combined_text),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get a single job listing by ID",
)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobListing).filter(JobListing.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id={job_id} not found.",
        )
    return job


@router.get(
    "",
    response_model=List[JobResponse],
    summary="List all job listings",
)
def list_jobs(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(JobListing).offset(skip).limit(limit).all()
