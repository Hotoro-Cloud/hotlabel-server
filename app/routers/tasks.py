from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import uuid

from app.models.task import TaskCreate, TaskInDB, TaskStatus, UserTaskMatch
from app.models.user_profile import UserProfile, UserProfileUpdate
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils.redis_client import RedisService

router = APIRouter()
logger = logging.getLogger("hotlabel.tasks")

# Dependencies
def get_task_service():
    return TaskService(RedisService())

def get_user_service():
    return UserService(RedisService())

@router.post("/", response_model=TaskInDB)
async def create_task(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Create a new task for labeling
    """
    try:
        # Add task to the database
        task_db = task_service.create_task(task)
        
        # Add to queue for processing (done in background)
        background_tasks.add_task(task_service.queue_task, task_db)
        
        logger.info(f"Task created: {task_db.task_id}")
        return task_db
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.post("/batch", response_model=Dict[str, Any])
async def create_tasks_batch(
    tasks: List[TaskCreate],
    background_tasks: BackgroundTasks,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Create multiple tasks at once
    """
    try:
        created_tasks = []
        failed_tasks = []
        
        for task in tasks:
            try:
                # Add task to database
                task_db = task_service.create_task(task)
                created_tasks.append(task_db)
                
                # Queue for processing
                background_tasks.add_task(task_service.queue_task, task_db)
            except Exception as e:
                failed_tasks.append({"task_id": task.task_id, "error": str(e)})
        
        logger.info(f"Batch created: {len(created_tasks)} tasks successful, {len(failed_tasks)} failed")
        return {
            "success": len(created_tasks),
            "failed": len(failed_tasks),
            "created_tasks": created_tasks,
            "failed_tasks": failed_tasks
        }
    except Exception as e:
        logger.error(f"Error in batch creation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process batch: {str(e)}")

@router.get("/{task_id}", response_model=TaskInDB)
async def get_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Get a task by ID
    """
    task = task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/", response_model=List[TaskInDB])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 10,
    offset: int = 0,
    task_service: TaskService = Depends(get_task_service)
):
    """
    List tasks with optional filtering
    """
    return task_service.list_tasks(status=status, limit=limit, offset=offset)

@router.post("/request", response_model=Optional[TaskInDB])
async def request_task(
    user_profile: UserProfileUpdate,
    session_id: str = Query(..., description="User session ID"),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Request a task for the user based on their profile
    """
    # Update user profile with latest data
    profile = user_service.update_profile(session_id, user_profile)
    
    # Find a suitable task
    task = task_service.find_task_for_user(profile)
    if not task:
        return None
    
    # Assign task to user
    assigned_task = task_service.assign_task(task.task_id, session_id)
    return assigned_task

@router.post("/match", response_model=List[UserTaskMatch])
async def match_tasks_to_user(
    user_profile: UserProfile,
    limit: int = 5,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Find tasks that match a user profile
    """
    matches = task_service.match_tasks_to_user(user_profile, limit)
    return matches