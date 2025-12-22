from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.db.models import Job, JobStatus, Upload
from app.worker.tasks import process_video_task
from app.services.storage import StorageService
from pydantic import BaseModel, HttpUrl, field_validator
import uuid
from datetime import datetime

router = APIRouter()

class JobCreate(BaseModel):
    input_url: HttpUrl
    copies: int = 1

    @field_validator('copies')
    @classmethod
    def validate_copies(cls, v: int) -> int:
        if v < 1:
            return 1
        if v > 20: # Limit max copies to prevent abuse
            return 20
        return v

class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
    input_url: str
    output_url: str | None = None
    metrics: dict | None = None
    error_message: str | None = None
    
    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    id: uuid.UUID
    input_url: str
    created_at: datetime
    jobs: list[JobResponse]
    
    class Config:
        from_attributes = True

@router.post("/uploads", response_model=list[UploadResponse])
async def create_job(job_in: JobCreate, db: AsyncSession = Depends(get_db)):
    # Create Upload record to group variations
    upload = Upload(input_url=str(job_in.input_url))
    
    created_jobs = []
    for _ in range(job_in.copies):
        job = Job(
            input_url=str(job_in.input_url),
            status=JobStatus.PENDING.value
        )
        # Link to upload using relationship
        upload.jobs.append(job)
        created_jobs.append(job)
    
    db.add(upload)
    await db.commit()
    
    for job in created_jobs:
        await db.refresh(job)
        # Trigger Celery task
        process_video_task.delay(str(job.id))
    
    return created_jobs

@router.get("/uploads", response_model=list[UploadResponse])
async def get_uploads(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Upload)
        .options(selectinload(Upload.jobs))
        .order_by(desc(Upload.created_at))
        .offset(skip)
        .limit(limit)
    )
    uploads = result.scalars().all()
    return uploads

@router.get("/uploads/{upload_id}", response_model=UploadResponse)
async def get_upload(upload_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Upload)
        .options(selectinload(Upload.jobs))
        .where(Upload.id == upload_id)
    )
    upload = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload

@router.get("/jobs", response_model=list[JobResponse])
async def get_jobs(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(desc(Job.created_at)).offset(skip).limit(limit))
    jobs = result.scalars().all()
    return jobs

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
        return StreamingResponse(
            file_stream.iter_chunks(),
            media_type="video/mp4",
            headers={"Content-Disposition": f"attachment; filename=processed_video_{job_id}.mp4"}
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found in storage")

@router.delete("/uploads/{upload_id}", status_code=204)
async def delete_upload(upload_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Fetch upload with all associated jobs
    result = await db.execute(
        select(Upload)
        .options(selectinload(Upload.jobs))
        .where(Upload.id == upload_id)
    )
    upload = result.scalars().first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
        
    storage = StorageService()
    
    # Delete all associated files from storage
    for job in upload.jobs:
        # Reconstruct the key based on the convention used in worker
        key = f"processed/{job.id}/processed_input_video.mp4"
        try:
            storage.delete_file(key)
        except Exception:
            # Log error but continue deletion
            pass
    
    # Delete upload (cascade will delete jobs from DB)
    await db.delete(upload)
    await db.commit()
