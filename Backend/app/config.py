"""
Application configuration and environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Azure ML Configuration
    AZURE_ML_SCORING_URL: str = os.getenv("REST_END_POINT") or os.getenv("AZURE_ML_SCORING_URL", "")
    AZURE_ML_API_KEY: str = os.getenv("PRIMARY_KEY") or os.getenv("AZURE_ML_API_KEY", "")
    
    # Audio Constraints
    MAX_AUDIO_SIZE_BYTES: int = 1 * 1024 * 1024  # 1 MB
    MAX_AUDIO_DURATION_SECONDS: int = 3
    ALLOWED_AUDIO_EXTENSIONS: list = [".wav"]
    SAMPLE_RATE: int = 16000
    
    # Azure ML Timeout
    AZURE_ML_TIMEOUT_SECONDS: int = 120
    
    # Confidence Thresholds
    CONFIDENCE_CONFIRMED: float = 0.75
    CONFIDENCE_NEEDS_CONFIRMATION: float = 0.4
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()

# Validate required settings
if not settings.AZURE_ML_SCORING_URL:
    raise RuntimeError("Azure ML scoring URL not configured. Set REST_END_POINT or AZURE_ML_SCORING_URL in .env")
if not settings.AZURE_ML_API_KEY:
    raise RuntimeError("Azure ML API key not configured. Set PRIMARY_KEY or AZURE_ML_API_KEY in .env")
