from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, List, Any, Union
from datetime import datetime
from enum import Enum

class ResponseStatus(str, Enum):
    SUBMITTED = "submitted"
    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class LabelQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPAM = "spam"

class ResponseCreate(BaseModel):
    task_id: str
    session_id: str
    response_data: Any  # The actual response content (answer, selection, etc.)
    client_metadata: Optional[Dict[str, Any]] = None
    response_time_ms: int  # How long it took to complete the task
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ResponseInDB(ResponseCreate):
    response_id: str
    publisher_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: ResponseStatus = ResponseStatus.SUBMITTED
    quality_score: Optional[float] = None  # 0-1 score from quality checks
    quality_level: Optional[LabelQuality] = None
    review_status: Optional[bool] = None  # Result of human review if performed
    review_notes: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BatchResponseSubmit(BaseModel):
    session_id: str
    responses: List[ResponseCreate]
    batch_metadata: Optional[Dict[str, Any]] = None

class ResponseStats(BaseModel):
    total_responses: int = 0
    responses_by_status: Dict[str, int] = Field(default_factory=dict)
    responses_by_quality: Dict[str, int] = Field(default_factory=dict)
    average_response_time_ms: Optional[float] = None
    response_rate: Optional[float] = None  # % of tasks that get responses

class ResponseFeedback(BaseModel):
    response_id: str
    feedback_type: str  # "quality", "review", etc.
    score: Optional[float] = None
    notes: Optional[str] = None
    reviewer_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }