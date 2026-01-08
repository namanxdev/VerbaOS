"""
Azure ML endpoint integration service.
Supports HuBERT (primary) with Wav2Vec fallback.
Includes hybrid classification for improved accuracy on aphasia speech.
"""

import base64
import httpx
from fastapi import HTTPException, status

from ..config import settings
from .intent_logic import detect_intent_from_transcription
from .intent_embeddings import predict_intent, INTENTS


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


async def call_azure_ml_hybrid(audio_bytes: bytes) -> dict:
    """
    Call both HuBERT and Wav2Vec endpoints for hybrid classification.
    Combines embedding-based and transcription-based approaches.
    
    This is more robust for aphasia patients because:
    - HuBERT captures acoustic patterns (non-verbal sounds, tone, rhythm)
    - Wav2Vec captures word-level patterns when speech is partially clear
    
    Args:
        audio_bytes: Raw WAV audio bytes
        
    Returns:
        dict: Combined response with both model outputs
    """
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    results = {
        "hubert_result": None,
        "wav2vec_result": None,
        "model_used": "hybrid"
    }
    
    # Try HuBERT (embeddings)
    if settings.HUBERT_SCORING_URL and settings.HUBERT_API_KEY:
        try:
            hubert_result = await _call_single_endpoint(
                audio_base64,
                settings.HUBERT_SCORING_URL,
                settings.HUBERT_API_KEY,
                "HuBERT"
            )
            results["hubert_result"] = hubert_result
        except Exception as e:
            print(f"[WARNING] HuBERT failed in hybrid mode: {e}")
    
    # Try Wav2Vec (transcription)
    if settings.WAVE2VEC_SCORING_URL and settings.WAVE2VEC_API_KEY:
        try:
            wav2vec_result = await _call_single_endpoint(
                audio_base64,
                settings.WAVE2VEC_SCORING_URL,
                settings.WAVE2VEC_API_KEY,
                "Wav2Vec"
            )
            results["wav2vec_result"] = wav2vec_result
        except Exception as e:
            print(f"[WARNING] Wav2Vec failed in hybrid mode: {e}")
    
    # If neither worked, raise error
    if results["hubert_result"] is None and results["wav2vec_result"] is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Both HuBERT and Wav2Vec endpoints failed in hybrid mode",
        )
    
    return results


def _combine_predictions(
    hubert_intent: str, hubert_confidence: float,
    wav2vec_intent: str, wav2vec_confidence: float
) -> tuple[str, float]:
    """
    Combine predictions from HuBERT (embedding) and Wav2Vec (transcription).
    
    Strategy:
    - If both agree: boost confidence
    - If disagree: use higher confidence one, with penalty
    - Weight HuBERT slightly higher for aphasia (acoustic patterns matter more)
    """
    HUBERT_WEIGHT = 0.6  # Slightly favor HuBERT for acoustic patterns
    WAV2VEC_WEIGHT = 0.4
    
    if hubert_intent == wav2vec_intent:
        # Agreement - boost confidence
        combined_conf = min(1.0, (hubert_confidence * HUBERT_WEIGHT + wav2vec_confidence * WAV2VEC_WEIGHT) * 1.15)
        return hubert_intent, combined_conf
    
    # Disagreement - use weighted decision
    hubert_score = hubert_confidence * HUBERT_WEIGHT
    wav2vec_score = wav2vec_confidence * WAV2VEC_WEIGHT
    
    if hubert_score >= wav2vec_score:
        # Use HuBERT but penalize for disagreement
        return hubert_intent, hubert_confidence * 0.85
    else:
        # Use Wav2Vec but penalize
        return wav2vec_intent, wav2vec_confidence * 0.85


def process_ml_response(ml_response: dict) -> tuple[str, float, str, list[str], list[float]]:
    """
    Process Azure ML response and extract intent/confidence.
    
    Handles multiple response formats:
    - Hybrid: {"hubert_result": {...}, "wav2vec_result": {...}} -> combined classification
    - Embeddings: {"embeddings": [...]} -> cosine similarity matching
    - Transcription: {"transcription": "..."} -> keyword matching
    - Direct intent: {"intent": "HELP", "confidence": 0.92}
    
    Args:
        ml_response: Response from Azure ML endpoint
        
    Returns:
        tuple: (intent, confidence, transcription, alternatives, embedding)
    """
    transcription = ""
    alternatives = []
    embedding = []
    
    # Hybrid response - combine both models
    if "hubert_result" in ml_response or "wav2vec_result" in ml_response:
        return _process_hybrid_response(ml_response)
    
    # HuBERT embeddings response - use cosine similarity
    if "embeddings" in ml_response:
        embedding = ml_response["embeddings"]
        print(f"[DEBUG] Got embedding with {len(embedding)} dimensions")
        intent, confidence, alternatives = predict_intent(embedding)
        return intent, confidence, "", alternatives, embedding
    
    # Direct intent response
    if "intent" in ml_response and "confidence" in ml_response:
        return ml_response["intent"], float(ml_response["confidence"]), "", [], []
    
    # Transcription-based response (Wav2Vec)
    if "transcription" in ml_response:
        transcription = ml_response["transcription"]
        print(f"[DEBUG] Azure ML transcription: '{transcription}'")
        intent, confidence = detect_intent_from_transcription(transcription)
        return intent, confidence, transcription, [], []
    
    # Unknown response format
    return "UNKNOWN", 0.0, "", INTENTS[:3], []


def _process_hybrid_response(ml_response: dict) -> tuple[str, float, str, list[str], list[float]]:
    """
    Process hybrid response combining HuBERT and Wav2Vec predictions.
    """
    hubert_result = ml_response.get("hubert_result")
    wav2vec_result = ml_response.get("wav2vec_result")
    
    hubert_intent, hubert_conf = "UNKNOWN", 0.0
    wav2vec_intent, wav2vec_conf = "UNKNOWN", 0.0
    transcription = ""
    embedding = []
    alternatives = []
    
    # Process HuBERT result
    if hubert_result and "embeddings" in hubert_result:
        embedding = hubert_result["embeddings"]
        hubert_intent, hubert_conf, alternatives = predict_intent(embedding)
        print(f"[DEBUG] HuBERT prediction: {hubert_intent} ({hubert_conf:.2f})")
    
    # Process Wav2Vec result
    if wav2vec_result and "transcription" in wav2vec_result:
        transcription = wav2vec_result["transcription"]
        wav2vec_intent, wav2vec_conf = detect_intent_from_transcription(transcription)
        print(f"[DEBUG] Wav2Vec prediction: {wav2vec_intent} ({wav2vec_conf:.2f}) from '{transcription}'")
    
    # If only one model worked, use it
    if hubert_intent == "UNKNOWN" and wav2vec_intent != "UNKNOWN":
        return wav2vec_intent, wav2vec_conf, transcription, [], embedding
    if wav2vec_intent == "UNKNOWN" and hubert_intent != "UNKNOWN":
        return hubert_intent, hubert_conf, transcription, alternatives, embedding
    if hubert_intent == "UNKNOWN" and wav2vec_intent == "UNKNOWN":
        return "UNKNOWN", 0.0, transcription, INTENTS[:3], embedding
    
    # Both models produced results - combine them
    final_intent, final_conf = _combine_predictions(
        hubert_intent, hubert_conf,
        wav2vec_intent, wav2vec_conf
    )
    
    print(f"[DEBUG] Hybrid prediction: {final_intent} ({final_conf:.2f})")
    print(f"[DEBUG]   HuBERT: {hubert_intent} ({hubert_conf:.2f})")
    print(f"[DEBUG]   Wav2Vec: {wav2vec_intent} ({wav2vec_conf:.2f}) - '{transcription}'")
    
    return final_intent, final_conf, transcription, alternatives, embedding


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
