from app.utils.redis_client import RedisService, KEY_STATS, KEY_TASK_QUEUE
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger("hotlabel.stats_service")

class StatsService:
    """Service for collecting and retrieving statistics"""
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get task-related statistics"""
        # Get basic counts
        total_tasks = self._get_counter("tasks:total")
        pending_tasks = self._get_counter("tasks:status:pending")
        assigned_tasks = self._get_counter("tasks:status:assigned")
        completed_tasks = self._get_counter("tasks:status:completed")
        
        # Category breakdown
        categories = {}
        for key in self.redis.redis.keys(f"{KEY_STATS}tasks:category:*"):
            category = key.split(":")[-1]
            count = self.redis.redis.get(key) or 0
            categories[category] = int(count)
        
        # Type breakdown
        types = {}
        for key in self.redis.redis.keys(f"{KEY_STATS}tasks:type:*"):
            task_type = key.split(":")[-1]
            count = self.redis.redis.get(key) or 0
            types[task_type] = int(count)
        
        return {
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "assigned_tasks": assigned_tasks, 
            "completed_tasks": completed_tasks,
            "completion_rate": self._safe_percentage(completed_tasks, total_tasks),
            "by_category": categories,
            "by_type": types
        }
    
    def get_response_stats(self) -> Dict[str, Any]:
        """Get response-related statistics"""
        # Get counts by quality level
        high_quality = self._get_counter("responses:quality:high")
        medium_quality = self._get_counter("responses:quality:medium")
        low_quality = self._get_counter("responses:quality:low")
        spam = self._get_counter("responses:quality:spam")
        
        total_responses = high_quality + medium_quality + low_quality + spam
        
        # Get counts by status
        submitted = self._get_counter("responses:status:submitted")
        accepted = self._get_counter("responses:status:accepted")
        rejected = self._get_counter("responses:status:rejected")
        
        return {
            "total_responses": total_responses,
            "quality_breakdown": {
                "high": high_quality,
                "medium": medium_quality,
                "low": low_quality,
                "spam": spam
            },
            "quality_percentages": {
                "high": self._safe_percentage(high_quality, total_responses),
                "medium": self._safe_percentage(medium_quality, total_responses),
                "low": self._safe_percentage(low_quality, total_responses),
                "spam": self._safe_percentage(spam, total_responses)
            },
            "status_breakdown": {
                "submitted": submitted,
                "accepted": accepted,
                "rejected": rejected
            }
        }
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get user-related statistics"""
        total_users = self._get_counter("users:total")
        
        # For a real system, we would track more detailed user metrics
        # This is a simplified implementation
        return {
            "total_users": total_users,
            "active_users": {
                "last_24h": 0,  # Placeholder
                "last_7d": 0,   # Placeholder
                "last_30d": 0   # Placeholder
            },
            "average_tasks_per_user": 0,  # Placeholder
            "average_quality_score": 0    # Placeholder
        }
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue-related statistics"""
        queue_length = self.redis.get_queue_length(KEY_TASK_QUEUE)
        
        # For a real system, we would track more queue metrics
        # This is a simplified implementation
        return {
            "queue_length": queue_length,
            "processing_rate": 0,  # Placeholder: tasks per minute
            "average_wait_time": 0  # Placeholder: seconds
        }
    
    def get_task_timeseries(self, start_date: datetime, end_date: datetime, interval: str) -> List[Dict[str, Any]]:
        """Get task creation/completion time series data"""
        # This would normally query time series data from Redis or another time series database
        # This is a simplified implementation that returns mock data
        
        # Generate time points based on interval
        time_points = self._generate_time_points(start_date, end_date, interval)
        
        # Generate mock data
        result = []
        for time_point in time_points:
            created = int(10 + 20 * self._mock_variation())
            completed = int(created * 0.7 * self._mock_variation())
            
            result.append({
                "timestamp": time_point.isoformat(),
                "tasks_created": created,
                "tasks_completed": completed
            })
        
        return result
    
    def get_response_timeseries(self, start_date: datetime, end_date: datetime, interval: str) -> List[Dict[str, Any]]:
        """Get response submission time series data"""
        # Similar to get_task_timeseries but for responses
        # This is a simplified implementation that returns mock data
        
        # Generate time points based on interval
        time_points = self._generate_time_points(start_date, end_date, interval)
        
        # Generate mock data
        result = []
        for time_point in time_points:
            responses = int(15 + 30 * self._mock_variation())
            avg_quality = 0.6 + 0.2 * self._mock_variation()
            
            result.append({
                "timestamp": time_point.isoformat(),
                "responses": responses,
                "average_quality": avg_quality
            })
        
        return result
    
    def get_quality_distribution(self) -> Dict[str, int]:
        """Get distribution of response quality levels"""
        return {
            "high": self._get_counter("responses:quality:high"),
            "medium": self._get_counter("responses:quality:medium"),
            "low": self._get_counter("responses:quality:low"),
            "spam": self._get_counter("responses:quality:spam")
        }
    
    def get_category_distribution(self) -> Dict[str, int]:
        """Get distribution of task categories"""
        categories = {}
        for key in self.redis.redis.keys(f"{KEY_STATS}tasks:category:*"):
            category = key.split(":")[-1]
            count = self.redis.redis.get(key) or 0
            categories[category] = int(count)
        
        return categories
    
    def _get_counter(self, key: str) -> int:
        """Get a counter value from Redis"""
        full_key = f"{KEY_STATS}{key}"
        value = self.redis.redis.get(full_key)
        return int(value) if value else 0
    
    def _safe_percentage(self, part: int, total: int) -> float:
        """Calculate percentage safely handling division by zero"""
        return round((part / total) * 100, 1) if total else 0
    
    def _generate_time_points(self, start_date: datetime, end_date: datetime, interval: str) -> List[datetime]:
        """Generate a list of time points between start and end dates based on interval"""
        time_points = []
        current = start_date
        
        if interval == "hour":
            delta = timedelta(hours=1)
        elif interval == "day":
            delta = timedelta(days=1)
        elif interval == "week":
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(days=1)  # Default to daily
        
        while current <= end_date:
            time_points.append(current)
            current += delta
        
        return time_points
    
    def _mock_variation(self) -> float:
        """Generate a random variation factor for mock data"""
        import random
        return 0.7 + random.random() * 0.6  # Between 0.7 and 1.3