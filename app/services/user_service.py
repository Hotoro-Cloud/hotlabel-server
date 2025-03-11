from app.models.user_profile import UserProfile, UserProfileUpdate, BrowserInfo, InterestProfile, ExpertiseProfile, TaskHistory, BehavioralProfile
from app.utils.redis_client import RedisService, KEY_USER_PROFILE, KEY_STATS
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import uuid

logger = logging.getLogger("hotlabel.user_service")

class UserService:
    """Service for user profile management"""
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
    
    def get_profile(self, session_id: str) -> Optional[UserProfile]:
        """Get a user profile by session ID"""
        profile_data = self.redis.get_user_profile(session_id)
        if not profile_data:
            return None
        return UserProfile(**profile_data)
    
    def create_profile(self, browser_info: BrowserInfo) -> UserProfile:
        """Create a new user profile"""
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create profile
        profile = UserProfile(
            session_id=session_id,
            browser_info=browser_info,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )
        
        # Store profile
        self.redis.store_user_profile(profile.dict())
        
        # Increment counter
        self.redis.increment_counter(f"{KEY_STATS}users:total")
        
        return profile
    
    def update_profile(self, session_id: str, update: UserProfileUpdate) -> UserProfile:
        """Update a user profile with new information"""
        # Get existing profile or create new one
        profile_data = self.redis.get_user_profile(session_id)
        if not profile_data:
            # Create new profile if not exists
            if not update.browser_info:
                raise ValueError("Browser info required for new profiles")
            
            profile = self.create_profile(update.browser_info)
            return profile
        
        # Update existing profile
        profile = UserProfile(**profile_data)
        profile.updated_at = datetime.utcnow()
        profile.last_active = datetime.utcnow()
        
        # Update browser info if provided
        if update.browser_info:
            profile.browser_info = update.browser_info
        
        # Update recent sites
        if update.recent_sites:
            profile.recent_sites = update.recent_sites
        
        # Update interests based on current site
        if update.current_site_category:
            interest_score = 0.7  # Default interest score
            if update.time_on_page:
                # Adjust based on time spent (more time = more interest)
                if update.time_on_page > 120:  # More than 2 minutes
                    interest_score = 0.9
                elif update.time_on_page > 60:  # More than 1 minute
                    interest_score = 0.8
                elif update.time_on_page < 15:  # Less than 15 seconds
                    interest_score = 0.5
            
            # Adjust based on interaction depth
            if update.interaction_depth is not None:
                interest_score *= (0.5 + update.interaction_depth * 0.5)
            
            # Update interest profile
            profile.interests.update_interest(update.current_site_category, interest_score)
        
        # Process additional metadata
        if update.metadata:
            self._process_profile_metadata(profile, update.metadata)
        
        # Store updated profile
        self.redis.store_user_profile(profile.dict())
        
        return profile
    
    def update_task_history(self, session_id: str, task_type: str, category: str, completion_time_ms: int, is_completed: bool) -> Optional[UserProfile]:
        """Update a user's task history based on task completion"""
        profile_data = self.redis.get_user_profile(session_id)
        if not profile_data:
            logger.warning(f"No profile found for session {session_id}")
            return None
        
        profile = UserProfile(**profile_data)
        
        # Update task history
        profile.task_history.update_history(
            task_type=task_type,
            category=category,
            completion_time_ms=completion_time_ms,
            is_completed=is_completed
        )
        
        # If task was completed, update expertise
        if is_completed:
            # Update expertise in the domain/topic
            expertise_gain = 0.05  # Small increment for each completed task
            profile.expertise.update_expertise(category, expertise_gain)
            
            # Adjust technical level based on task complexity
            # This would normally come from the task data, using a placeholder
            task_complexity = 0.5  # Medium complexity
            # Small adjustment to technical level
            profile.expertise.technical_level = (
                profile.expertise.technical_level * 0.95 + task_complexity * 0.05
            )
        
        # Store updated profile
        self.redis.store_user_profile(profile.dict())
        
        return profile
    
    def _process_profile_metadata(self, profile: UserProfile, metadata: Dict[str, Any]):
        """Process additional metadata to update the profile"""
        # Process language information
        if "detected_language" in metadata:
            lang = metadata["detected_language"]
            if lang not in profile.expertise.languages:
                profile.expertise.languages[lang] = 0.7  # Initial proficiency estimate
        
        # Process domain expertise signals
        if "technical_terms" in metadata and isinstance(metadata["technical_terms"], list):
            for term_data in metadata["technical_terms"]:
                domain = term_data.get("domain")
                confidence = term_data.get("confidence", 0.5)
                if domain:
                    profile.expertise.update_expertise(domain, confidence, weight=0.03)
        
        # Process behavioral data
        if "active_hour" in metadata:
            hour = int(metadata["active_hour"])
            if hour not in profile.behavioral.active_hours:
                profile.behavioral.active_hours.append(hour)
                # Keep only the 5 most active hours
                if len(profile.behavioral.active_hours) > 5:
                    profile.behavioral.active_hours = profile.behavioral.active_hours[-5:]
        
        # Process engagement metrics
        if "engagement_signals" in metadata:
            signals = metadata["engagement_signals"]
            if "scroll_depth" in signals:
                profile.behavioral.page_engagement = (
                    profile.behavioral.page_engagement * 0.7 +
                    float(signals["scroll_depth"]) * 0.3
                )
            
            if "click_pattern" in signals:
                profile.behavioral.click_pattern_score = (
                    profile.behavioral.click_pattern_score * 0.7 +
                    float(signals["click_pattern"]) * 0.3
                )
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get statistics about users"""
        total_users = self.redis.redis.get(f"{KEY_STATS}users:total") or 0
        total_users = int(total_users) if total_users else 0
        
        # This is a simplified implementation
        # In a real system, use more sophisticated analytics
        return {
            "total_users": total_users,
            "active_today": 0,  # Placeholder
            "active_this_week": 0,  # Placeholder
            "average_tasks_per_user": 0  # Placeholder
        }