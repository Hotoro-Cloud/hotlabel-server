from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Dict, Optional, List, Any, Literal
from enum import Enum
import uuid
from datetime import datetime

class TaskStatus(str, Enum):
    PENDING = "pending"       # Task created but not assigned
    ASSIGNED = "assigned"     # Task assigned to a user
    COMPLETED = "completed"   # Task completed successfully
    REJECTED = "rejected"     # Task rejected due to quality issues
    EXPIRED = "expired"       # Task expired (no completion within time limit)

class TaskType(str, Enum):
    MULTIPLE_CHOICE = "multiple-choice"
    TRUE_FALSE = "true-false"
    SHORT_ANSWER = "short-answer"
    RATING = "rating"
    VQA = "vqa"               # Visual Question Answering

class TaskCategory(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VQA = "vqa"               # Visual Question Answering
    AUDIO = "audio"
    CODE = "code"

class ImageContent(BaseModel):
    url: HttpUrl
    alt_text: Optional[str] = None

class TextContent(BaseModel):
    text: str

class AudioContent(BaseModel):
    url: HttpUrl
    duration_seconds: Optional[float] = None

class ContentUnion(BaseModel):
    image: Optional[ImageContent] = None
    text: Optional[TextContent] = None
    audio: Optional[AudioContent] = None

class TaskQuestion(BaseModel):
    text: str
    choices: Optional[Dict[str, str]] = None

class TaskRequirements(BaseModel):
    language: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    expertise_level: Optional[int] = Field(None, ge=1, le=5)  # 1-5 scale
    min_completion_time: Optional[int] = None  # Minimum seconds to complete
    
class TaskCreate(BaseModel):
    task_id: Optional[str] = None
    track_id: Optional[str] = None
    language: str
    category: TaskCategory
    type: TaskType
    topic: str
    complexity: int = Field(ge=1, le=5)  # 1-5 scale
    content: ContentUnion
    task: TaskQuestion
    requirements: Optional[TaskRequirements] = None
    
    @validator('task_id', pre=True, always=True)
    def set_task_id(cls, v):
        return v or str(uuid.uuid4())
    
    @validator('track_id', pre=True, always=True)
    def set_track_id(cls, v):
        return v or str(uuid.uuid4())

class TaskInDB(TaskCreate):
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_to: Optional[str] = None  # User session ID
    assigned_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    priority: int = 0  # Higher numbers = higher priority
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TaskResponse(BaseModel):
    task_id: str
    session_id: str
    response: Any  # Could be a string, dict, or other type depending on task
    response_time_ms: int
    confidence: Optional[float] = None  # Self-reported confidence (0-1)
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserTaskMatch(BaseModel):
    task_id: str
    session_id: str
    match_score: float
    match_reasons: List[str]