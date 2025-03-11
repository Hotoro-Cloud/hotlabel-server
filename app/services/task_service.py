from app.models.task import TaskCreate, TaskInDB, TaskStatus, UserTaskMatch
from app.models.user_profile import UserProfile
from app.models.response import ResponseInDB, ResponseStatus, LabelQuality
from app.utils.redis_client import RedisService, KEY_STATS
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import json
import uuid

logger = logging.getLogger("hotlabel.task_service")

class TaskService:
    """Service for task management"""
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
    
    def create_task(self, task: TaskCreate) -> TaskInDB:
        """Create a new task and store it"""
        now = datetime.utcnow()
        
        # Convert to TaskInDB
        task_db = TaskInDB(
            **task.dict(),
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        
        # Store the task
        self.redis.store_task(task_db.dict())
        
        # Increment task counters
        self.redis.increment_counter(f"{KEY_STATS}tasks:total")
        self.redis.increment_counter(f"{KEY_STATS}tasks:category:{task.category}")
        self.redis.increment_counter(f"{KEY_STATS}tasks:type:{task.type}")
        
        return task_db
    
    def queue_task(self, task: TaskInDB) -> bool:
        """Add a task to the queue for distribution"""
        # Calculate priority based on complexity and other factors
        # Lower complexity = higher priority (easier tasks first)
        base_priority = 10 - task.complexity * 2  # 1=8, 2=6, 3=4, 4=2, 5=0
        
        # Adjust by other factors like topic popularity
        # For now, just use base priority
        priority = base_priority
        
        # Add to task queue
        return self.redis.add_task_to_queue(task.dict(), priority)
    
    def get_task(self, task_id: str) -> Optional[TaskInDB]:
        """Get a task by ID"""
        task_data = self.redis.get_task(task_id)
        if not task_data:
            return None
        return TaskInDB(**task_data)
    
    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 10, offset: int = 0) -> List[TaskInDB]:
        """List tasks with optional filtering"""
        # TODO: Implement filtering by status with Redis
        # This is a simple implementation that loads all tasks
        # In a real system, use Redis search or other methods for efficient filtering
        
        tasks = []
        task_ids = self.redis.redis.keys("task:*")
        
        # Apply offset and limit
        task_ids = task_ids[offset:offset+limit]
        
        for task_id in task_ids:
            task_data = self.redis.get_json(task_id)
            if task_data:
                task = TaskInDB(**task_data)
                if status is None or task.status == status:
                    tasks.append(task)
        
        return tasks
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> Optional[TaskInDB]:
        """Update a task's status"""
        task_data = self.redis.get_task(task_id)
        if not task_data:
            return None
        
        # Update status and updated_at
        task_data["status"] = status
        task_data["updated_at"] = datetime.utcnow().isoformat()
        
        # If completing, set completion time
        if status == TaskStatus.COMPLETED:
            task_data["completed_at"] = datetime.utcnow().isoformat()
        
        # Store updated task
        self.redis.store_task(task_data)
        
        # Increment status counter
        self.redis.increment_counter(f"{KEY_STATS}tasks:status:{status}")
        
        return TaskInDB(**task_data)
    
    def assign_task(self, task_id: str, session_id: str) -> Optional[TaskInDB]:
        """Assign a task to a user"""
        task_data = self.redis.get_task(task_id)
        if not task_data:
            return None
        
        # Check if already assigned
        if task_data.get("status") == TaskStatus.ASSIGNED:
            # If assigned to someone else, don't reassign
            if task_data.get("assigned_to") and task_data.get("assigned_to") != session_id:
                return None
        
        # Update task data
        now = datetime.utcnow()
        task_data["status"] = TaskStatus.ASSIGNED
        task_data["assigned_to"] = session_id
        task_data["assigned_at"] = now.isoformat()
        
        # Set expiry (tasks expire after 10 minutes if not completed)
        expires_at = now + timedelta(minutes=10)
        task_data["expires_at"] = expires_at.isoformat()
        
        # Store updated task
        self.redis.store_task(task_data)
        
        # Increment assignment counter
        self.redis.increment_counter(f"{KEY_STATS}tasks:assigned")
        
        return TaskInDB(**task_data)
    
    def find_task_for_user(self, user_profile: UserProfile) -> Optional[TaskInDB]:
        """Find a suitable task for the user based on their profile"""
        # This is a simplified implementation
        # In a real system, use more sophisticated matching algorithms
        
        # Get user's language preferences
        user_languages = [user_profile.browser_info.language]
        if user_profile.browser_info.preferred_languages:
            user_languages.extend(user_profile.browser_info.preferred_languages)
        
        # Get top expertise domains
        expertise_domains = sorted(
            user_profile.expertise.domains.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_domains = [domain for domain, _ in expertise_domains[:5]]
        
        # Get tasks from queue
        tasks = self.redis.get_next_tasks(20)
        
        # Score each task by match to user profile
        task_scores = []
        for task_data in tasks:
            score = 0
            task = TaskInDB(**task_data)
            
            # Match on language
            if task.language in user_languages:
                score += 2
            
            # Match on topic/domain
            if task.topic in top_domains:
                score += 3
            
            # Consider complexity vs. expertise level
            complexity_diff = abs(task.complexity - user_profile.expertise.technical_level * 5)
            score -= complexity_diff
            
            # Consider user's task history
            if task.category in user_profile.task_history.categories_completed:
                score += 1
                
            if task.type in user_profile.task_history.task_types_completed:
                score += 1
            
            task_scores.append((task, score))
        
        # Sort by score
        task_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the best match, if any
        return task_scores[0][0] if task_scores else None
    
    def match_tasks_to_user(self, user_profile: UserProfile, limit: int = 5) -> List[UserTaskMatch]:
        """
        Match tasks to a user profile and return scores and reasons
        """
        # Similar to find_task_for_user but returns multiple matches with details
        # Get user's language preferences
        user_languages = [user_profile.browser_info.language]
        if user_profile.browser_info.preferred_languages:
            user_languages.extend(user_profile.browser_info.preferred_languages)
        
        # Get top expertise domains
        expertise_domains = sorted(
            user_profile.expertise.domains.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_domains = [domain for domain, _ in expertise_domains[:5]]
        
        # Get tasks from queue
        tasks = self.redis.get_next_tasks(20)
        
        # Score each task by match to user profile
        matches = []
        for task_data in tasks:
            score = 0
            reasons = []
            task = TaskInDB(**task_data)
            
            # Match on language
            if task.language in user_languages:
                score += 2
                reasons.append(f"Language match: {task.language}")
            
            # Match on topic/domain
            if task.topic in top_domains:
                score += 3
                reasons.append(f"Topic match: {task.topic}")
            
            # Consider complexity vs. expertise level
            user_expertise = user_profile.expertise.technical_level * 5
            complexity_diff = abs(task.complexity - user_expertise)
            if complexity_diff <= 1:
                score += 2
                reasons.append(f"Complexity suitable: {task.complexity} vs expertise {user_expertise:.1f}")
            else:
                score -= complexity_diff
                if task.complexity > user_expertise:
                    reasons.append(f"Task may be too difficult: {task.complexity} vs expertise {user_expertise:.1f}")
                else:
                    reasons.append(f"Task may be too easy: {task.complexity} vs expertise {user_expertise:.1f}")
            
            # Consider user's task history
            if task.category in user_profile.task_history.categories_completed:
                score += 1
                reasons.append(f"User has experience with {task.category} tasks")
                
            if task.type in user_profile.task_history.task_types_completed:
                score += 1
                reasons.append(f"User has experience with {task.type} tasks")
            
            matches.append(UserTaskMatch(
                task_id=task.task_id,
                session_id=user_profile.session_id,
                match_score=score,
                match_reasons=reasons
            ))
        
        # Sort by score and limit
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return matches[:limit]
    
    def process_response(self, response: ResponseInDB) -> None:
        """
        Process a submitted response (quality checks, etc.)
        """
        # Get the task
        task_data = self.redis.get_task(response.task_id)
        if not task_data:
            logger.error(f"Task not found for response: {response.response_id}")
            return
        
        # Run quality checks
        quality_score = self._check_response_quality(response, task_data)
        
        # Update response with quality score
        response_data = self.redis.get_response(response.response_id)
        if response_data:
            response_data["quality_score"] = quality_score
            
            # Determine quality level
            if quality_score >= 0.8:
                quality_level = LabelQuality.HIGH
            elif quality_score >= 0.5:
                quality_level = LabelQuality.MEDIUM
            elif quality_score >= 0.2:
                quality_level = LabelQuality.LOW
            else:
                quality_level = LabelQuality.SPAM
            
            response_data["quality_level"] = quality_level
            self.redis.store_response(response_data)
            
            # Increment quality counter
            self.redis.increment_counter(f"{KEY_STATS}responses:quality:{quality_level}")
    
    def _check_response_quality(self, response: ResponseInDB, task: Dict) -> float:
        """
        Check the quality of a response
        Returns a score between 0 and 1
        """
        # This is a simplified quality check
        # In a real system, use more sophisticated methods
        
        score = 0.5  # Default middle score
        
        # Check response time - too quick might be spam
        min_expected_time = 1000  # 1 second
        if response.response_time_ms < min_expected_time:
            score -= 0.2
        
        # Check response against known answer (if available)
        correct_answer = task.get("correct_answer")
        if correct_answer and response.response_data != correct_answer:
            score -= 0.3
        
        # TODO: Implement more sophisticated quality checks
        # - Check against other responses for the same task (consensus)
        # - Check user's past quality history
        # - Use ML models to evaluate response quality
        
        # Ensure score is in 0-1 range
        return max(0.0, min(1.0, score))