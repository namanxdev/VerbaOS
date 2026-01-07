"""
Azure ML endpoint integration service.
"""

import base64
import httpx
from fastapi import HTTPException, status

from ..config import settings
from .intent_logic import detect_intent_from_transcription


async def call_azure_ml(audio_bytes: bytes) -> dict:
    """
    Call Azure ML endpoint with audio data.
    
    The audio is sent as base64-encoded JSON payload matching
    the existing Azure ML endpoint format.
    
    Args:
        audio_bytes: Raw WAV audio bytes
        
    Returns:
        dict: ML endpoint response
        
    Raises:
        HTTPException: If ML endpoint fails
    """
    # Encode audio as base64 (matching existing endpoint format)
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {settings.AZURE_ML_API_KEY}",
    }
    
    payload = {
        "audio": audio_base64,
        "sample_rate": settings.SAMPLE_RATE,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.AZURE_ML_SCORING_URL,
            json=payload,
            headers=headers,
            timeout=settings.AZURE_ML_TIMEOUT_SECONDS,
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Azure ML returned status {response.status_code}",
            )
        
        return response.json()


def process_ml_response(ml_response: dict) -> tuple[str, float, str]:
    """
    Process Azure ML response and extract intent/confidence.
    
    Handles multiple response formats:
    - Option A (MVP): {"embedding_dim": 768} or {"transcription": "..."}
    - Option B: {"intent": "HELP", "confidence": 0.92}
    
    Args:
        ml_response: Response from Azure ML endpoint
        
    Returns:
        tuple: (intent, confidence, transcription)
    """
    transcription = ""
    
    # Option B: Direct intent response
    if "intent" in ml_response and "confidence" in ml_response:
        return ml_response["intent"], float(ml_response["confidence"]), ""
    
    # Transcription-based response (current format)
    if "transcription" in ml_response:
        transcription = ml_response["transcription"]
        print(f"[DEBUG] Azure ML transcription: '{transcription}'")  # Debug log
        intent, confidence = detect_intent_from_transcription(transcription)
        return intent, confidence, transcription
    
    # Option A: Embedding only (fallback to unknown)
    if "embedding_dim" in ml_response:
        return "UNKNOWN", 0.5, ""
    
    # Unknown response format
    return "UNKNOWN", 0.3, ""


async def check_ml_endpoint_health() -> bool:
    """
    Check if Azure ML endpoint is reachable.
    
    Returns:
        bool: True if reachable, False otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            # Try HEAD request to score endpoint
            response = await client.head(
                settings.AZURE_ML_SCORING_URL,
                headers={"Authorization": f"Bearer {settings.AZURE_ML_API_KEY}"},
                timeout=5.0,
            )
            return True
    except Exception:
        # Try GET to base URL
        try:
            async with httpx.AsyncClient() as client:
                base_url = settings.AZURE_ML_SCORING_URL.replace("/score", "")
                response = await client.get(base_url, timeout=5.0)
                return True
        except Exception:
            return False
