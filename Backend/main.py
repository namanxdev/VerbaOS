"""
Speech-to-Intent Backend API
FastAPI backend for patient speech-to-intent assistive system.

This is the main entry point for the application.
Run with: uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routes import audio_router, health_router
from app.routes.users_db import router as users_db_router
from app.services.postgres_db import init_db, close_db


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("[INFO] Initializing PostgreSQL database connection...")
    await init_db()
    print("[OK] Database connected")
    
    yield
    
    # Shutdown
    await close_db()
    print("[INFO] Database connection closed")


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
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://verbao.vercel.app",
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative local port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://verbao[a-z0-9_-]*\.vercel\.app",  # Allow all Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(audio_router)
app.include_router(health_router)
app.include_router(users_db_router)


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
