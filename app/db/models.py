import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    jobs = relationship("Job", back_populates="upload", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=True)
    upload = relationship("Upload", back_populates="jobs")
    
    status = Column(String, default=JobStatus.PENDING.value)
    input_url = Column(Text, nullable=False)
    output_url = Column(Text, nullable=True)
    profile_name = Column(String, nullable=False)
    profile_config = Column(JSON, nullable=True)
    
    # Metrics
    original_hashes = Column(JSON, nullable=True)
    processed_hashes = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
