import redis
import json
import os
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger("hotlabel.redis")

# Redis connection settings from environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Redis key prefixes
KEY_TASK = "task:"
KEY_USER_PROFILE = "user:"
KEY_RESPONSE = "response:"
KEY_TASK_QUEUE = "queue:tasks"
KEY_STATS = "stats:"

# Redis client singleton
_redis_client = None

def get_redis_client() -> redis.Redis:
    """Get or create a Redis client instance"""
    global _redis_client
    
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        logger.info(f"Redis client initialized: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    
    return _redis_client

class RedisService:
    """Service for Redis operations"""
    
    def __init__(self):
        self.redis = get_redis_client()
    
    def store_json(self, key: str, data: Any, expiry: Optional[int] = None) -> bool:
        """Store JSON data in Redis"""
        try:
            json_data = json.dumps(data)
            self.redis.set(key, json_data)
            if expiry:
                self.redis.expire(key, expiry)
            return True
        except Exception as e:
            logger.error(f"Error storing JSON data: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Any]:
        """Get JSON data from Redis"""
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting JSON data: {e}")
            return None
    
    def push_to_queue(self, queue_name: str, data: Any) -> bool:
        """Push data to a Redis list (queue)"""
        try:
            json_data = json.dumps(data)
            self.redis.lpush(queue_name, json_data)
            return True
        except Exception as e:
            logger.error(f"Error pushing to queue: {e}")
            return False
    
    def pop_from_queue(self, queue_name: str) -> Optional[Any]:
        """Pop data from a Redis list (queue)"""
        try:
            data = self.redis.rpop(queue_name)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error popping from queue: {e}")
            return None
    
    def get_queue_length(self, queue_name: str) -> int:
        """Get the length of a Redis list (queue)"""
        try:
            return self.redis.llen(queue_name)
        except Exception as e:
            logger.error(f"Error getting queue length: {e}")
            return 0
    
    def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment a counter in Redis"""
        try:
            return self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing counter: {e}")
            return 0
    
    def add_to_sorted_set(self, set_name: str, value: str, score: float) -> bool:
        """Add a value to a sorted set"""
        try:
            self.redis.zadd(set_name, {value: score})
            return True
        except Exception as e:
            logger.error(f"Error adding to sorted set: {e}")
            return False
    
    def get_from_sorted_set(self, set_name: str, min_score: float, max_score: float, count: int) -> List[str]:
        """Get values from a sorted set within a score range"""
        try:
            return self.redis.zrangebyscore(set_name, min_score, max_score, start=0, num=count)
        except Exception as e:
            logger.error(f"Error getting from sorted set: {e}")
            return []
    
    # Task-specific methods
    
    def store_task(self, task_data: Dict) -> bool:
        """Store a task in Redis"""
        task_id = task_data.get("task_id")
        if not task_id:
            logger.error("Cannot store task without task_id")
            return False
        
        key = f"{KEY_TASK}{task_id}"
        return self.store_json(key, task_data)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a task from Redis"""
        key = f"{KEY_TASK}{task_id}"
        return self.get_json(key)
    
    def add_task_to_queue(self, task_data: Dict, priority: float = 1.0) -> bool:
        """Add a task to the task queue with priority"""
        task_id = task_data.get("task_id")
        if not task_id:
            logger.error("Cannot add task to queue without task_id")
            return False
        
        # Store the task
        self.store_task(task_data)
        
        # Add to sorted set queue with priority score
        return self.add_to_sorted_set(KEY_TASK_QUEUE, task_id, priority)
    
    def get_next_tasks(self, count: int = 10) -> List[Dict]:
        """Get next tasks from the queue"""
        # Get task IDs from the sorted set
        task_ids = self.redis.zrange(KEY_TASK_QUEUE, 0, count-1)
        
        # Get tasks by ID
        tasks = []
        for task_id in task_ids:
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        
        return tasks
    
    # User profile methods
    
    def store_user_profile(self, user_profile: Dict) -> bool:
        """Store a user profile in Redis"""
        session_id = user_profile.get("session_id")
        if not session_id:
            logger.error("Cannot store user profile without session_id")
            return False
        
        key = f"{KEY_USER_PROFILE}{session_id}"
        # Store with expiry of 30 days
        return self.store_json(key, user_profile, expiry=60*60*24*30)
    
    def get_user_profile(self, session_id: str) -> Optional[Dict]:
        """Get a user profile from Redis"""
        key = f"{KEY_USER_PROFILE}{session_id}"
        return self.get_json(key)
    
    # Response methods
    
    def store_response(self, response_data: Dict) -> bool:
        """Store a response in Redis"""
        response_id = response_data.get("response_id")
        if not response_id:
            logger.error("Cannot store response without response_id")
            return False
        
        key = f"{KEY_RESPONSE}{response_id}"
        return self.store_json(key, response_data)
    
    def get_response(self, response_id: str) -> Optional[Dict]:
        """Get a response from Redis"""
        key = f"{KEY_RESPONSE}{response_id}"
        return self.get_json(key)