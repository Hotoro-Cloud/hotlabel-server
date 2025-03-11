from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from app.models.task import TaskStatus
from app.models.response import ResponseStats
from app.utils.redis_client import RedisService, KEY_STATS, KEY_TASK_QUEUE
from app.services.stats_service import StatsService

router = APIRouter()
logger = logging.getLogger("hotlabel.admin")

# Dependencies
def get_redis():
    return RedisService()

def get_stats_service():
    return StatsService(RedisService())

@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics(
    stats_service: StatsService = Depends(get_stats_service)
):
    """
    Get system-wide metrics and statistics
    """
    try:
        # Get various stats
        task_stats = stats_service.get_task_stats()
        response_stats = stats_service.get_response_stats()
        user_stats = stats_service.get_user_stats()
        queue_stats = stats_service.get_queue_stats()
        
        return {
            "tasks": task_stats,
            "responses": response_stats,
            "users": user_stats,
            "queues": queue_stats,
            "updated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    timeframe: str = Query("day", description="Timeframe for data (day, week, month)"),
    stats_service: StatsService = Depends(get_stats_service)
):
    """
    Get dashboard data with charts and time series
    """
    try:
        # Calculate date range based on timeframe
        now = datetime.utcnow()
        if timeframe == "day":
            start_date = now - timedelta(days=1)
            interval = "hour"
        elif timeframe == "week":
            start_date = now - timedelta(days=7)
            interval = "day"
        elif timeframe == "month":
            start_date = now - timedelta(days=30)
            interval = "day"
        else:
            raise HTTPException(status_code=400, detail="Invalid timeframe")
        
        # Get time series data
        task_timeseries = stats_service.get_task_timeseries(start_date, now, interval)
        response_timeseries = stats_service.get_response_timeseries(start_date, now, interval)
        quality_distribution = stats_service.get_quality_distribution()
        category_distribution = stats_service.get_category_distribution()
        
        return {
            "timeframe": timeframe,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
            "task_timeseries": task_timeseries,
            "response_timeseries": response_timeseries,
            "quality_distribution": quality_distribution,
            "category_distribution": category_distribution
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard data: {str(e)}")

@router.get("/queue-status", response_model=Dict[str, Any])
async def get_queue_status(
    redis: RedisService = Depends(get_redis)
):
    """
    Get status of task queues
    """
    try:
        # Get count of tasks in queue
        queue_length = redis.get_queue_length(KEY_TASK_QUEUE)
        
        # Get next tasks preview
        next_tasks = redis.get_next_tasks(5)
        
        return {
            "queue_length": queue_length,
            "next_tasks_preview": next_tasks,
            "updated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve queue status: {str(e)}")

@router.post("/reset-stats", response_model=Dict[str, Any])
async def reset_stats(
    redis: RedisService = Depends(get_redis)
):
    """
    Reset all statistics (for testing purposes)
    """
    try:
        # Get keys matching stats prefix
        all_keys = redis.redis.keys(f"{KEY_STATS}*")
        
        # Delete all stat keys
        if all_keys:
            redis.redis.delete(*all_keys)
        
        return {
            "success": True,
            "message": f"Reset {len(all_keys)} statistics keys",
            "reset_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset statistics: {str(e)}")

@router.post("/purge-queue/{queue_name}", response_model=Dict[str, Any])
async def purge_queue(
    queue_name: str,
    redis: RedisService = Depends(get_redis)
):
    """
    Purge all items from a queue (for testing purposes)
    """
    try:
        # Delete the queue
        redis.redis.delete(queue_name)
        
        return {
            "success": True,
            "message": f"Purged queue: {queue_name}",
            "purged_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error purging queue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to purge queue: {str(e)}")