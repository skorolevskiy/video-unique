import boto3
import os
from botocore.client import Config
from app.core.config import settings

class StorageService:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION_NAME,
            config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})
        )
        
        # Client for presigning with external URL (localhost for dev)
        self.s3_presign = boto3.client(
            's3',
            endpoint_url="http://localhost:9000",
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION_NAME,
            config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})
        )

        self.bucket = settings.S3_BUCKET_NAME
        
        # Ensure bucket exists
        try:
            self.s3.create_bucket(Bucket=self.bucket)
        except Exception:
            pass # Bucket might exist

    def upload_file(self, file_path: str, object_name: str = None) -> str:
        if object_name is None:
            object_name = os.path.basename(file_path)
            
        self.s3.upload_file(file_path, self.bucket, object_name)
        
        # Generate presigned URL for access
        url = self.s3_presign.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': object_name},
            ExpiresIn=3600*24 # 24 hours
        )
        return url

    def get_file_stream(self, object_name: str):
        return self.s3.get_object(Bucket=self.bucket, Key=object_name)['Body']

    def download_file(self, url: str, dest_path: str):
        # If it's a presigned URL or public URL, use requests
        # If it's s3://, use boto3
        import requests
        
        if url.startswith("http"):
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(dest_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        else:
            # Assume s3 key for MVP? Or just fail.
            raise ValueError("Only HTTP/HTTPS URLs supported for MVP input")
