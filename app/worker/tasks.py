import asyncio
import os
import uuid
from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.db.models import Job, JobStatus
from app.services.storage import StorageService
from app.engine.pipeline import Pipeline, ProcessingContext
from app.engine.steps.ffmpeg_steps import (
    MetadataMutationStep, 
    NoiseInjectionStep, 
    ColorModulationStep,
    GeometricTransformStep
)
from app.engine.analyzer import VideoHasher
from sqlalchemy import select

async def update_job_status(job_id: uuid.UUID, status: str, **kwargs):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalars().first()
            if job:
                job.status = status
                for k, v in kwargs.items():
                    setattr(job, k, v)
                await session.commit()

@celery_app.task(bind=True)
def process_video_task(self, job_id_str: str):
    job_id = uuid.UUID(job_id_str)
    loop = asyncio.get_event_loop()
    
    # 1. Update status to PROCESSING
    loop.run_until_complete(update_job_status(job_id, JobStatus.PROCESSING.value))
    
    temp_dir = f"/tmp/video_processing/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)
    input_path = os.path.join(temp_dir, "input_video.mp4")
    
    try:
        # Fetch job details (need a separate read, or pass data in args. For MVP, read from DB)
        # We need the input_url.
        async def get_job_data():
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Job).where(Job.id == job_id))
                return result.scalars().first()
        
        job = loop.run_until_complete(get_job_data())
        if not job:
            return "Job not found"

        # 2. Download
        storage = StorageService()
        storage.download_file(job.input_url, input_path)
        
        # 3. Calculate Original Metrics
        orig_md5 = VideoHasher.calculate_file_hash(input_path)
        orig_phash = VideoHasher.calculate_perceptual_hashes(input_path)
        
        # 4. Build Pipeline based on profile
        # For MVP, hardcode a "Standard" profile
        steps = [
            MetadataMutationStep(),
            ColorModulationStep(),
            NoiseInjectionStep(),
            GeometricTransformStep()
        ]
        
        pipeline = Pipeline(steps)
        
        config = {
            'noise_intensity': 5,
            'output_params': {
                'c:v': 'libx264',
                'crf': 23,
                'preset': 'fast'
            }
        }
        
        ctx = ProcessingContext(input_path, temp_dir, config)
        
        # 5. Run Pipeline
        output_path = pipeline.run(ctx)
        
        # 6. Calculate New Metrics
        new_md5 = VideoHasher.calculate_file_hash(output_path)
        new_phash = VideoHasher.calculate_perceptual_hashes(output_path)
        dist = VideoHasher.compare_hashes(orig_phash, new_phash)
        
        # 7. Upload Result
        output_key = f"processed/{job_id}/{os.path.basename(output_path)}"
        storage.upload_file(output_path, output_key)
        
        # Construct API URL for download
        # Assuming API is running on localhost:8000 for now, or use a config
        output_url = f"https://uniq.powercodeai.space/api/v1/jobs/{job_id}/download"
        
        # 8. Update DB
        metrics = {
            'original_md5': orig_md5,
            'processed_md5': new_md5,
            'phash_distance': dist
        }
        
        loop.run_until_complete(update_job_status(
            job_id, 
            JobStatus.COMPLETED.value,
            output_url=output_url,
            metrics=metrics,
            original_hashes=orig_phash,
            processed_hashes=new_phash
        ))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        loop.run_until_complete(update_job_status(
            job_id, 
            JobStatus.FAILED.value,
            error_message=str(e)
        ))
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
