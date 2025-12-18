from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import Job, JobStatus
from app.worker.tasks import process_video_task
from app.services.storage import StorageService
from pydantic import BaseModel, HttpUrl
import uuid

router = APIRouter()

class JobCreate(BaseModel):
    input_url: HttpUrl
    profile: str = "standard"

class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
    input_url: str
    output_url: str | None = None
    metrics: dict | None = None
    error_message: str | None = None

@router.post("/jobs", response_model=JobResponse)
async def create_job(job_in: JobCreate, db: AsyncSession = Depends(get_db)):
    job = Job(
        input_url=str(job_in.input_url),
        profile_name=job_in.profile,
        status=JobStatus.PENDING.value
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Trigger Celery task
    process_video_task.delay(str(job.id))
    
    return job

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/jobs/{job_id}/download")
async def download_video(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    
    if not job or job.status != JobStatus.COMPLETED.value:
        raise HTTPException(status_code=404, detail="Video not found or not ready")
        
    storage = StorageService()
    # Reconstruct the key based on the convention used in worker
    key = f"processed/{job_id}/processed_input_video.mp4"
    
    try:
        file_stream = storage.get_file_stream(key)
        return StreamingResponse(file_stream, media_type="video/mp4")
    except Exception:
        raise HTTPException(status_code=404, detail="File not found in storage")
