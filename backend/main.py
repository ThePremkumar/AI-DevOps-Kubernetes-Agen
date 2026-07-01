import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from core import settings
from models import HealthResponse
from api import api_router

# Configure loguru logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API orchestrator for AI Kubernetes Troubleshooting Agent",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(api_router, prefix="/api")

@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint for the service.
    """
    logger.info("Health check endpoint hit")
    return HealthResponse(status="healthy", service="ai-kubernetes-agent")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
