from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import uuid

from app.models.response import ResponseCreate, ResponseInDB, BatchResponseSubmit, ResponseFeedback
from app.models.task import TaskStatus
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils.redis_client import RedisService

router = APIRouter()
logger = logging.getLogger("hotlabel.responses")

# Dependencies
def get_task_service():
    return TaskService(RedisService())

def get_user_service():
    return UserService(RedisService())

@router.post("/", response_model=ResponseInDB)
async def submit_response(
    response: ResponseCreate,
    background_tasks: BackgroundTasks,
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Submit a response for a task
    """
    try:
        # Get the task to make sure it exists and is assigned to this user
        task = task_service.get_task(response.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status != TaskStatus.ASSIGNED or task.assigned_to != response.session_id:
            raise HTTPException(status_code=400, detail="Task not properly assigned to this user")
        
        # Create the response
        response_id = str(uuid.uuid4())
        response_db = ResponseInDB(
            **response.dict(),
            response_id=response_id,
            publisher_id=task.track_id or "unknown",
            created_at=datetime.utcnow()
        )
        
        # Store the response
        redis = RedisService()
        redis.store_response(response_db.dict())
        
        # Update task status
        task_service.update_task_status(task.task_id, TaskStatus.COMPLETED)
        
        # Update user profile with this task completion
        background_tasks.add_task(
            user_service.update_task_history,
            response.session_id,
            task.type,
            task.category,
            response.response_time_ms,
            True
        )
        
        # Run quality checks in background
        background_tasks.add_task(task_service.process_response, response_db)
        
        logger.info(f"Response submitted: {response_id} for task {task.task_id}")
        return response_db
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting response: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit response: {str(e)}")

@router.post("/batch", response_model=Dict[str, Any])
async def submit_responses_batch(
    batch: BatchResponseSubmit,
    background_tasks: BackgroundTasks,
    task_service: TaskService = Depends(get_task_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Submit multiple responses at once
    """
    try:
        session_id = batch.session_id
        successful_responses = []
        failed_responses = []
        
        for response in batch.responses:
            try:
                # Ensure session_id is consistent
                if response.session_id != session_id:
                    raise ValueError("Inconsistent session_id in batch")
                
                # Submit individual response
                response_db = await submit_response(
                    response,
                    background_tasks,
                    task_service,
                    user_service
                )
                successful_responses.append(response_db)
            except Exception as e:
                failed_responses.append({
                    "task_id": response.task_id,
                    "error": str(e)
                })
        
        logger.info(f"Batch responses: {len(successful_responses)} successful, {len(failed_responses)} failed")
        return {
            "success": len(successful_responses),
            "failed": len(failed_responses),
            "responses": successful_responses,
            "failed_responses": failed_responses
        }
    except Exception as e:
        logger.error(f"Error in batch response submission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process batch responses: {str(e)}")

@router.get("/{response_id}", response_model=ResponseInDB)
async def get_response(
    response_id: str,
    redis: RedisService = Depends(lambda: RedisService())
):
    """
    Get a response by ID
    """
    response = redis.get_response(response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    return response

@router.post("/feedback/{response_id}", response_model=ResponseFeedback)
async def submit_feedback(
    response_id: str,
    feedback: ResponseFeedback,
    redis: RedisService = Depends(lambda: RedisService())
):
    """
    Submit feedback for a response (for quality control)
    """
    # Get the response
    response = redis.get_response(response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    
    # Store the feedback
    feedback_key = f"feedback:{response_id}:{feedback.feedback_type}"
    redis.store_json(feedback_key, feedback.dict())
    
    # Update response quality if needed
    if feedback.feedback_type == "quality" and feedback.score is not None:
        response["quality_score"] = feedback.score
        redis.store_response(response)
    
    logger.info(f"Feedback submitted for response {response_id}: {feedback.feedback_type}")
    return feedback