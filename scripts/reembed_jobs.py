import os
import sys

# Add the root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import JobListing
from app.services.embedding import embed

def main():
    db: Session = SessionLocal()
    try:
        jobs = db.query(JobListing).filter(JobListing.embedding.isnot(None)).all()
        print(f"Found {len(jobs)} jobs to re-embed.")
        
        for job in jobs:
            text = f"{job.title} {job.company} {job.location or ''} {job.description} {' '.join(job.skills)}"
            print(f"Re-embedding job ID {job.id}: {job.title}")
            job.embedding = embed(text)
        
        db.commit()
        print("Re-embedding complete.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
