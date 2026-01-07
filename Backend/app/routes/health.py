"""
Health check API routes.
"""

from fastapi import APIRouter

from ..models.schemas import HealthResponse
from ..services.azure_ml import check_ml_endpoint_health

router = APIRouter(tags=["Health"])


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for frontend and monitoring.
    
    Verifies that:
    - Backend API is running
    - Azure ML endpoint is reachable
    
    Use this endpoint for:
    - Load balancer health checks
    - Frontend connectivity verification
    - Monitoring and alerting
    """
    is_ml_reachable = await check_ml_endpoint_health()
    
    return HealthResponse(
        status="ok",
        ml_endpoint="reachable" if is_ml_reachable else "unreachable",
    )


@router.get("/")
async def root():
    """
    Root endpoint with API information.
    
    Provides basic API metadata and available endpoints.
    """
    return {
        "name": "Speech-to-Intent API",
        "version": "1.0.0",
        "description": "Backend API for patient speech-to-intent assistive system",
        "endpoints": {
            "audio": {
                "process": "POST /api/audio",
                "requirements": "GET /api/audio/requirements",
            },
            "health": "GET /api/health",
            "docs": "GET /docs",
        },
    }
