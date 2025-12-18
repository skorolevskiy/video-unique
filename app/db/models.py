import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.db.base import Base

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
