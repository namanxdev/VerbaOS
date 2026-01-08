"""
Health check API routes and visitor tracking.
"""

import json
from pathlib import Path
from fastapi import APIRouter, Request

from ..models.schemas import HealthResponse
from ..services.azure_ml import check_ml_endpoint_health

router = APIRouter(tags=["Health"])

# Visitor counter persistence
VISITOR_FILE = Path(__file__).parent.parent.parent / "visitor_count.json"

def _load_visitor_count() -> dict:
    """Load visitor count from file."""
    if VISITOR_FILE.exists():
        try:
            with open(VISITOR_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"count": 0, "visitors": []}

def _save_visitor_count(data: dict):
    """Save visitor count to file."""
    try:
        with open(VISITOR_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[ERROR] Could not save visitor count: {e}")


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


@router.get("/api/visitors")
async def get_visitor_count():
    """
    Get the current visitor count without incrementing.
    """
    data = _load_visitor_count()
    return {"count": data["count"]}


@router.post("/api/visitors/register")
async def register_visitor(request: Request):
    """
    Register a new visitor and increment the counter.
    Uses client IP + User-Agent as a simple identifier.
    Only increments if this is a new unique visitor.
    """
    # Get client identifier
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")[:100]  # Limit length
    visitor_id = f"{client_ip}:{hash(user_agent) % 100000}"
    
    data = _load_visitor_count()
    
    # Check if this is a new visitor
    if visitor_id not in data["visitors"]:
        data["visitors"].append(visitor_id)
        data["count"] = len(data["visitors"])
        _save_visitor_count(data)
        is_new = True
    else:
        is_new = False
    
    return {
        "count": data["count"],
        "is_new_visitor": is_new
    }
