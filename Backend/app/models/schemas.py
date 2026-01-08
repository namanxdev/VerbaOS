"""
Pydantic schemas for API request/response models.
"""

from typing import Optional
from pydantic import BaseModel


class IntentResponse(BaseModel):
    """Response model for audio processing endpoint."""
    intent: str
    confidence: float
    status: str
    ui_options: list[str]
    next_action: str
    transcription: Optional[str] = None  # Debug: show what was heard


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str
    ml_endpoints: dict  # Status for each model (hubert, wave2vec)


class ErrorResponse(BaseModel):
    """Response model for error responses."""
    error: str
    message: Optional[str] = None


class AudioRecordingInfo(BaseModel):
    """Information about audio recording requirements for frontend."""
    format: str = "wav"
    sample_rate: int = 16000
    max_duration_seconds: int = 3
    max_size_bytes: int = 1048576  # 1 MB
    channels: int = 1  # Mono
    bit_depth: int = 16
