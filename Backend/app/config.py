"""
Application configuration and environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Azure PostgreSQL Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "postgres")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "5432"))
    DATABASE_SSL: str = os.getenv("DATABASE_SSL", "require")
    
    # Azure ML Configuration - HuBERT (Primary)
    HUBERT_SCORING_URL: str = os.getenv("REST_END_POINT__HUBERT", "")
    HUBERT_API_KEY: str = os.getenv("PRIMARY_KEY__HUBERT", "")
    
    # Azure ML Configuration - Wav2Vec (Fallback)
    WAVE2VEC_SCORING_URL: str = os.getenv("REST_END_POINT__WAVE2VEC", "")
    WAVE2VEC_API_KEY: str = os.getenv("PRIMARY_KEY__WAVE2VEC", "")
    
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

# Validate required settings - at least one model must be configured
if not settings.HUBERT_SCORING_URL and not settings.WAVE2VEC_SCORING_URL:
    raise RuntimeError("No Azure ML endpoints configured. Set REST_END_POINT__HUBERT or REST_END_POINT__WAVE2VEC in .env")
if settings.HUBERT_SCORING_URL and not settings.HUBERT_API_KEY:
    raise RuntimeError("HuBERT API key not configured. Set PRIMARY_KEY__HUBERT in .env")
if settings.WAVE2VEC_SCORING_URL and not settings.WAVE2VEC_API_KEY:
    raise RuntimeError("Wav2Vec API key not configured. Set PRIMARY_KEY__WAVE2VEC in .env")
