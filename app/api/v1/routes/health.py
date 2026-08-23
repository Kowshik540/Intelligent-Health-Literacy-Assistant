"""
Health Check Route — Used by monitoring tools to verify the service is running.
"""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])


# Returns service status, name, and version — used by load balancers and uptime monitors
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.API_VERSION,
    }
