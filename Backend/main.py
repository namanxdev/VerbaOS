"""
Speech-to-Intent Backend API
FastAPI backend for patient speech-to-intent assistive system.

This is the main entry point for the application.
Run with: uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes import audio_router, health_router, users_router


# Create FastAPI application
app = FastAPI(
    title="Speech-to-Intent API",
    description="""
## Patient Speech-to-Intent Assistive System

This API receives short audio recordings from patients and returns detected intents
with appropriate UI actions for caregivers.

### How It Works

1. **Patient presses "Speak"** on the frontend interface
2. **Frontend records audio** using Web Audio API (1-3 seconds)
3. **Frontend sends .wav file** to `POST /api/audio`
4. **Backend calls Azure ML** model for speech-to-intent
5. **Backend returns intent** with confidence and UI buttons
6. **Patient/Caregiver confirms** the action

### Audio Requirements

- Format: WAV
- Sample Rate: 16000 Hz
- Channels: Mono
- Duration: Max 3 seconds
- Size: Max 1 MB

### Supported Intents

| Intent | Description | UI Options |
|--------|-------------|------------|
| HELP | Patient needs assistance | Confirm Help, Cancel |
| EMERGENCY | Urgent situation | Cancel Emergency |
| WATER | Patient needs water | Confirm Water, Cancel |
| YES | Confirmation | OK |
| NO | Cancellation | OK |
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(audio_router)
app.include_router(health_router)
app.include_router(users_router)


# Custom exception handler for consistent error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Return consistent JSON error responses."""
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "request_error", "message": str(detail)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
    )
