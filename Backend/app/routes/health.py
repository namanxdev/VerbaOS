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
    - Azure ML endpoints are reachable (HuBERT primary, Wav2Vec fallback)
    
    Use this endpoint for:
    - Load balancer health checks
    - Frontend connectivity verification
    - Monitoring and alerting
    """
    ml_health = await check_ml_endpoint_health()
    
    # System is healthy if at least one endpoint is reachable
    any_reachable = (
        ml_health["hubert"]["reachable"] or 
        ml_health["wave2vec"]["reachable"]
    )
    
    return HealthResponse(
        status="ok" if any_reachable else "degraded",
        ml_endpoints=ml_health,
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
