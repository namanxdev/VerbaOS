"""
Azure ML endpoint integration service.
Supports HuBERT (primary) with Wav2Vec fallback.
"""

import base64
import httpx
from fastapi import HTTPException, status

from ..config import settings
from .intent_logic import detect_intent_from_transcription


async def _call_single_endpoint(audio_base64: str, scoring_url: str, api_key: str, model_name: str) -> dict:
    """
    Call a single Azure ML endpoint.
    
    Args:
        audio_base64: Base64 encoded audio
        scoring_url: The endpoint URL
        api_key: The API key
        model_name: Name for logging purposes
        
    Returns:
        dict: ML endpoint response
        
    Raises:
        Exception: If the endpoint fails
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    payload = {
        "audio": audio_base64,
        "sample_rate": settings.SAMPLE_RATE,
    }
    
    async with httpx.AsyncClient() as client:
        print(f"[INFO] Calling {model_name} endpoint: {scoring_url}")
        response = await client.post(
            scoring_url,
            json=payload,
            headers=headers,
            timeout=settings.AZURE_ML_TIMEOUT_SECONDS,
        )
        
        if response.status_code != 200:
            raise Exception(f"{model_name} returned status {response.status_code}: {response.text}")
        
        result = response.json()
        print(f"[INFO] {model_name} returned successfully")
        return result


async def call_azure_ml(audio_bytes: bytes) -> dict:
    """
    Call Azure ML endpoint with audio data.
    Uses HuBERT as primary model, falls back to Wav2Vec on failure.
    
    The audio is sent as base64-encoded JSON payload matching
    the existing Azure ML endpoint format.
    
    Args:
        audio_bytes: Raw WAV audio bytes
        
    Returns:
        dict: ML endpoint response with 'model_used' field added
        
    Raises:
        HTTPException: If all ML endpoints fail
    """
    # Encode audio as base64 (matching existing endpoint format)
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    errors = []
    
    # Try HuBERT first (primary model)
    if settings.HUBERT_SCORING_URL and settings.HUBERT_API_KEY:
        try:
            result = await _call_single_endpoint(
                audio_base64,
                settings.HUBERT_SCORING_URL,
                settings.HUBERT_API_KEY,
                "HuBERT"
            )
            result["model_used"] = "HuBERT"
            return result
        except Exception as e:
            error_msg = f"HuBERT failed: {str(e)}"
            print(f"[WARNING] {error_msg}")
            errors.append(error_msg)
    
    # Fallback to Wav2Vec
    if settings.WAVE2VEC_SCORING_URL and settings.WAVE2VEC_API_KEY:
        try:
            print("[INFO] Falling back to Wav2Vec model...")
            result = await _call_single_endpoint(
                audio_base64,
                settings.WAVE2VEC_SCORING_URL,
                settings.WAVE2VEC_API_KEY,
                "Wav2Vec"
            )
            result["model_used"] = "Wav2Vec"
            return result
        except Exception as e:
            error_msg = f"Wav2Vec failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            errors.append(error_msg)
    
    # Both models failed
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"All Azure ML endpoints failed: {'; '.join(errors)}",
    )


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


async def check_ml_endpoint_health() -> dict:
    """
    Check if Azure ML endpoints are reachable.
    
    Returns:
        dict: Health status for each configured endpoint
    """
    health = {
        "hubert": {"configured": False, "reachable": False},
        "wave2vec": {"configured": False, "reachable": False},
    }
    
    # Check HuBERT
    if settings.HUBERT_SCORING_URL and settings.HUBERT_API_KEY:
        health["hubert"]["configured"] = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    settings.HUBERT_SCORING_URL,
                    headers={"Authorization": f"Bearer {settings.HUBERT_API_KEY}"},
                    timeout=5.0,
                )
                health["hubert"]["reachable"] = True
        except Exception:
            pass
    
    # Check Wav2Vec
    if settings.WAVE2VEC_SCORING_URL and settings.WAVE2VEC_API_KEY:
        health["wave2vec"]["configured"] = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    settings.WAVE2VEC_SCORING_URL,
                    headers={"Authorization": f"Bearer {settings.WAVE2VEC_API_KEY}"},
                    timeout=5.0,
                )
                health["wave2vec"]["reachable"] = True
        except Exception:
            pass
    
    return health
