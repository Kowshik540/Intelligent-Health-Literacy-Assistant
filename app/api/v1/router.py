"""
API v1 Router — Aggregates all route modules under the /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.feedback import router as feedback_router
from app.api.v1.routes.safety import router as safety_router


# Main API router — all endpoints are prefixed with /api/v1
api_v1_router = APIRouter(prefix="/api/v1")


api_v1_router.include_router(health_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(feedback_router)
api_v1_router.include_router(safety_router)