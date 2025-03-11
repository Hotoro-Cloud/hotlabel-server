from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, Request, Body
import logging
import time
import json
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

# Then ensure the CORS middleware is properly configured
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to help debug request bodies
@app.middleware("http")
async def debug_request_body(request: Request, call_next):
    # Log request method and path
    logger.debug(f"Request: {request.method} {request.url.path}")
    
    # For POST/PUT requests, attempt to log the body for debugging
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                body_str = body.decode()
                logger.debug(f"Request body: {body_str}")
                # Store body for reuse
                request.state.raw_body = body
        except Exception as e:
            logger.error(f"Error reading request body: {e}")
    
    # Continue with the request
    response = await call_next(request)
    return response

# Log request timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"Request: {request.method} {request.url.path} - Took: {process_time:.4f}s")
    return response

@app.middleware("http")
async def parse_json_body(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                # Parse the request body manually to avoid issues
                body = await request.body()
                if body:
                    # Store the parsed body in request.state to access it later
                    request.state.body = json.loads(body)
            except Exception as e:
                pass
    
    response = await call_next(request)
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

# Include routers - using custom prefix classes to handle the body parsing issue
class CustomTasksRouter(tasks.router.__class__):
    async def __call__(self, *args, **kwargs):
        request = kwargs.get("request")
        if request and request.method in ["POST"]:
            # Try to parse body from state if available
            if hasattr(request.state, "raw_body"):
                try:
                    body_str = request.state.raw_body.decode()
                    kwargs["body"] = json.loads(body_str)
                except Exception as e:
                    logger.error(f"Error parsing body in tasks router: {e}")
        
        return await super().__call__(*args, **kwargs)

class CustomResponsesRouter(responses.router.__class__):
    async def __call__(self, *args, **kwargs):
        request = kwargs.get("request")
        if request and request.method in ["POST"]:
            # Try to parse body from state if available
            if hasattr(request.state, "raw_body"):
                try:
                    body_str = request.state.raw_body.decode()
                    kwargs["body"] = json.loads(body_str)
                except Exception as e:
                    logger.error(f"Error parsing body in responses router: {e}")
        
        return await super().__call__(*args, **kwargs)

# Modified router includes with custom wrapper classes
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