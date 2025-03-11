from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
import uuid

class BrowserInfo(BaseModel):
    user_agent: str
    language: str
    preferred_languages: Optional[List[str]] = None
    timezone: Optional[str] = None
    screen_resolution: Optional[str] = None
    platform: Optional[str] = None
    is_mobile: Optional[bool] = None

class InterestProfile(BaseModel):
    categories: Dict[str, float] = {}  # Category name -> interest score (0-1)
    topics: Dict[str, float] = {}      # Topic name -> interest score (0-1)
    
    def update_interest(self, category: str, score: float, weight: float = 0.1):
        """Update interest score with exponential moving average"""
        current = self.categories.get(category, 0.5)
        self.categories[category] = current * (1 - weight) + score * weight

class ExpertiseProfile(BaseModel):
    domains: Dict[str, float] = {}      # Domain name -> expertise score (0-1)
    languages: Dict[str, float] = {}    # Language code -> proficiency (0-1)
    technical_level: float = 0.5        # General technical proficiency (0-1)
    
    def update_expertise(self, domain: str, score: float, weight: float = 0.05):
        """Update expertise score with exponential moving average"""
        current = self.domains.get(domain, 0.5)
        self.domains[domain] = current * (1 - weight) + score * weight

class TaskHistory(BaseModel):
    completed_tasks: int = 0
    abandoned_tasks: int = 0
    average_completion_time_ms: Optional[float] = None
    task_types_completed: Dict[str, int] = {}  # Task type -> count
    categories_completed: Dict[str, int] = {}  # Category -> count
    quality_score: float = 0.5  # Overall quality score (0-1)
    
    def update_history(self, task_type: str, category: str, completion_time_ms: int, is_completed: bool):
        if is_completed:
            self.completed_tasks += 1
            self.task_types_completed[task_type] = self.task_types_completed.get(task_type, 0) + 1
            self.categories_completed[category] = self.categories_completed.get(category, 0) + 1
            
            # Update average completion time
            if self.average_completion_time_ms is None:
                self.average_completion_time_ms = float(completion_time_ms)
            else:
                self.average_completion_time_ms = (
                    (self.average_completion_time_ms * (self.completed_tasks - 1) + completion_time_ms) 
                    / self.completed_tasks
                )
        else:
            self.abandoned_tasks += 1

class BehavioralProfile(BaseModel):
    active_hours: List[int] = []        # Hours of day (0-23) when most active
    average_session_length: Optional[float] = None  # In minutes
    page_engagement: float = 0.5        # How deeply user engages with content (0-1)
    click_pattern_score: float = 0.5    # Deliberate vs. random clicking (0-1)
    visit_frequency: Optional[str] = None  # "daily", "weekly", etc.

class UserProfile(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    browser_info: BrowserInfo
    interests: InterestProfile = Field(default_factory=InterestProfile)
    expertise: ExpertiseProfile = Field(default_factory=ExpertiseProfile)
    task_history: TaskHistory = Field(default_factory=TaskHistory)
    behavioral: BehavioralProfile = Field(default_factory=BehavioralProfile)
    recent_sites: List[str] = []  # Categories of recently visited sites
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserProfileUpdate(BaseModel):
    browser_info: Optional[BrowserInfo] = None
    recent_sites: Optional[List[str]] = None
    current_site_category: Optional[str] = None
    current_page_topic: Optional[str] = None
    time_on_page: Optional[int] = None  # In seconds
    interaction_depth: Optional[float] = None  # How far down the page scrolled (0-1)
    
    # Additional behavioral signals
    metadata: Optional[Dict[str, Any]] = None