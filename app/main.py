from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from app.routers import tasks, responses, admin
from app.utils.redis_client import get_redis_client
from app.models.task import TaskStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("hotlabel")

app = FastAPI(
    title="HotLabel API",
    description="API for HotLabel - Crowdsourced Data Labeling for LLM Alignment",
    version="0.1.0",
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log request timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Request: {request.method} {request.url.path} - Took: {process_time:.4f}s")
    return response

# Health check endpoint
@app.get("/health")
async def health():
    # Check Redis connection
    redis = get_redis_client()
    try:
        redis.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "operational",
        "redis": redis_status,
        "version": app.version
    }

# Include routers
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(responses.router, prefix="/responses", tags=["responses"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to HotLabel API",
        "docs": "/docs",
        "metrics": "/admin/metrics"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)