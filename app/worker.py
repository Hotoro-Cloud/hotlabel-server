import os
from celery import Celery
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("hotlabel.worker")

# Redis connection settings from environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Celery configuration
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
if REDIS_PASSWORD:
    BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Initialize Celery
celery_app = Celery("hotlabel", broker=BROKER_URL)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
)

# Import models and services to use in tasks
from app.models.task import TaskStatus
from app.models.response import ResponseStatus, LabelQuality
from app.utils.redis_client import RedisService, KEY_TASK_QUEUE

# Task definitions
@celery_app.task(name="process_expired_tasks")
def process_expired_tasks():
    """Process tasks that have expired (assigned but not completed)"""
    logger.info("Processing expired tasks")
    redis = RedisService()
    
    # Get all tasks
    task_keys = redis.redis.keys("task:*")
    now = datetime.utcnow()
    expired_count = 0
    
    for key in task_keys:
        task_data = redis.get_json(key)
        if not task_data:
            continue
        
        # Check if task is assigned and has an expiry time
        if (
            task_data.get("status") == TaskStatus.ASSIGNED and
            task_data.get("expires_at")
        ):
            # Parse expiry time
            expires_at = datetime.fromisoformat(task_data["expires_at"].replace("Z", "+00:00"))
            
            # Check if expired
            if now > expires_at:
                # Update task status
                task_data["status"] = TaskStatus.EXPIRED
                task_data["updated_at"] = now.isoformat()
                redis.store_json(key, task_data)
                
                # Re-queue task
                task_id = task_data.get("task_id")
                if task_id:
                    redis.add_to_sorted_set(KEY_TASK_QUEUE, task_id, 5.0)  # Higher priority for re-queued tasks
                
                expired_count += 1
    
    logger.info(f"Processed {expired_count} expired tasks")
    return expired_count

@celery_app.task(name="calculate_user_quality_scores")
def calculate_user_quality_scores():
    """Calculate quality scores for users based on their response history"""
    logger.info("Calculating user quality scores")
    redis = RedisService()
    
    # Get all user profiles
    user_keys = redis.redis.keys("user:*")
    updated_count = 0
    
    for key in user_keys:
        user_data = redis.get_json(key)
        if not user_data or "session_id" not in user_data:
            continue
        
        session_id = user_data["session_id"]
        
        # Get response quality data for this user
        response_keys = redis.redis.keys(f"response:*")
        quality_scores = []
        
        for resp_key in response_keys:
            resp_data = redis.get_json(resp_key)
            if not resp_data or resp_data.get("session_id") != session_id:
                continue
            
            # Collect quality scores
            quality_score = resp_data.get("quality_score")
            if quality_score is not None:
                quality_scores.append(float(quality_score))
        
        # Update user quality score if we have data
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            
            # Update user profile
            if "task_history" not in user_data:
                user_data["task_history"] = {}
            
            user_data["task_history"]["quality_score"] = avg_quality
            redis.store_json(key, user_data)
            updated_count += 1
    
    logger.info(f"Updated quality scores for {updated_count} users")
    return updated_count

@celery_app.task(name="analyze_task_distribution")
def analyze_task_distribution():
    """Analyze task distribution and adjust priorities"""
    logger.info("Analyzing task distribution")
    redis = RedisService()
    
    # This would implement logic to analyze how tasks are distributed
    # and adjust priorities based on various factors:
    # - Low-coverage tasks get higher priority
    # - Tasks close to completion get higher priority
    # - Balance task types, categories, languages, etc.
    
    # Simplified implementation for now
    tasks_analyzed = 0
    priorities_adjusted = 0
    
    # Get tasks from queue
    task_ids = redis.redis.zrange(KEY_TASK_QUEUE, 0, -1, withscores=True)
    
    for task_id, priority in task_ids:
        task_data = redis.get_task(task_id)
        if not task_data:
            continue
        
        tasks_analyzed += 1
        
        # Example logic: increase priority for tasks that have been in queue longer
        created_at = datetime.fromisoformat(task_data["created_at"].replace("Z", "+00:00"))
        now = datetime.utcnow()
        age_hours = (now - created_at).total_seconds() / 3600
        
        # Boost priority for older tasks (max +5 boost)
        age_boost = min(age_hours / 24, 5)
        
        # Example logic: boost tasks with fewer responses
        response_count = redis.redis.get(f"stats:task:{task_id}:responses") or 0
        response_count = int(response_count) if response_count else 0
        
        response_boost = max(5 - response_count, 0)
        
        # Calculate new priority
        new_priority = float(priority) + age_boost + response_boost
        
        # Update priority if it changed significantly
        if abs(new_priority - float(priority)) > 1.0:
            redis.add_to_sorted_set(KEY_TASK_QUEUE, task_id, new_priority)
            priorities_adjusted += 1
    
    logger.info(f"Analyzed {tasks_analyzed} tasks, adjusted {priorities_adjusted} priorities")
    return {
        "tasks_analyzed": tasks_analyzed,
        "priorities_adjusted": priorities_adjusted
    }

@celery_app.task(name="clean_old_data")
def clean_old_data():
    """Clean up old data from Redis"""
    logger.info("Cleaning old data")
    redis = RedisService()
    
    # Define maximum age for different types of data
    max_ages = {
        "task": 90,      # 90 days for tasks
        "response": 90,  # 90 days for responses
        "user": 60,      # 60 days for user profiles
    }
    
    deleted_count = 0
    now = datetime.utcnow()
    
    # Process tasks
    task_keys = redis.redis.keys("task:*")
    for key in task_keys:
        task_data = redis.get_json(key)
        if not task_data or "created_at" not in task_data:
            continue
        
        created_at = datetime.fromisoformat(task_data["created_at"].replace("Z", "+00:00"))
        age_days = (now - created_at).days
        
        if age_days > max_ages["task"]:
            redis.redis.delete(key)
            deleted_count += 1
    
    # Process responses
    response_keys = redis.redis.keys("response:*")
    for key in response_keys:
        resp_data = redis.get_json(key)
        if not resp_data or "created_at" not in resp_data:
            continue
        
        created_at = datetime.fromisoformat(resp_data["created_at"].replace("Z", "+00:00"))
        age_days = (now - created_at).days
        
        if age_days > max_ages["response"]:
            redis.redis.delete(key)
            deleted_count += 1
    
    # Process user profiles
    user_keys = redis.redis.keys("user:*")
    for key in user_keys:
        user_data = redis.get_json(key)
        if not user_data or "last_active" not in user_data:
            continue
        
        last_active = datetime.fromisoformat(user_data["last_active"].replace("Z", "+00:00"))
        age_days = (now - last_active).days
        
        if age_days > max_ages["user"]:
            redis.redis.delete(key)
            deleted_count += 1
    
    logger.info(f"Cleaned {deleted_count} old data items")
    return deleted_count

# Define periodic tasks
@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Process expired tasks every 5 minutes
    sender.add_periodic_task(
        300.0,  # 5 minutes
        process_expired_tasks.s(),
        name="process expired tasks every 5 minutes"
    )
    
    # Calculate user quality scores daily
    sender.add_periodic_task(
        timedelta(days=1),
        calculate_user_quality_scores.s(),
        name="calculate user quality scores daily"
    )
    
    # Analyze task distribution hourly
    sender.add_periodic_task(
        timedelta(hours=1),
        analyze_task_distribution.s(),
        name="analyze task distribution hourly"
    )
    
    # Clean old data weekly
    sender.add_periodic_task(
        timedelta(days=7),
        clean_old_data.s(),
        name="clean old data weekly"
    )

if __name__ == "__main__":
    celery_app.start()