from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import uuid
import json

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
    task: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = None,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Create a new task for labeling
    """
    try:
        # Log the received task data for debugging
        logger.debug(f"Received task data: {task}")
        
        # Create TaskCreate from dictionary
        task_obj = TaskCreate(**task)
        
        # Add task to the database
        task_db = task_service.create_task(task_obj)
        
        # Add to queue for processing (done in background)
        if background_tasks:
            background_tasks.add_task(task_service.queue_task, task_db)
        
        logger.info(f"Task created: {task_db.task_id}")
        return task_db
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.post("/batch", response_model=Dict[str, Any])
async def create_tasks_batch(
    tasks: List[Dict[str, Any]] = Body(...),
    background_tasks: BackgroundTasks = None,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Create multiple tasks at once
    """
    try:
        # Log the received tasks data for debugging
        logger.debug(f"Received batch tasks data: {tasks}")
        
        created_tasks = []
        failed_tasks = []
        
        for task_data in tasks:
            try:
                # Create TaskCreate from dictionary
                task = TaskCreate(**task_data)
                
                # Add task to database
                task_db = task_service.create_task(task)
                created_tasks.append(task_db)
                
                # Queue for processing
                if background_tasks:
                    background_tasks.add_task(task_service.queue_task, task_db)
            except Exception as e:
                failed_tasks.append({"task_id": task_data.get("task_id"), "error": str(e)})
        
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
    profile: Dict[str, Any] = Body(...),
    session_id: str = Query(..., description="User session ID"),
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Request a task for the user based on their profile
    """
    try:
        # Log the received profile data for debugging
        logger.debug(f"Received profile data: {profile}")
        
        # Create UserProfileUpdate from dictionary
        profile_update = UserProfileUpdate(**profile)
        
        # Update user profile with latest data
        updated_profile = user_service.update_profile(session_id, profile_update)
        
        # Find a suitable task
        task = task_service.find_task_for_user(updated_profile)
        if not task:
            return None
        
        # Assign task to user
        assigned_task = task_service.assign_task(task.task_id, session_id)
        return assigned_task
    except Exception as e:
        logger.error(f"Error requesting task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to request task: {str(e)}")

@router.post("/match", response_model=List[UserTaskMatch])
async def match_tasks_to_user(
    user_profile: UserProfile,
    limit: int = 5,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Find tasks that match a user profile
    """
    try:
        matches = task_service.match_tasks_to_user(user_profile, limit)
        return matches
    except Exception as e:
        logger.error(f"Error matching tasks to user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to match tasks: {str(e)}")