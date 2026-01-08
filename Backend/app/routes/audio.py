"""
Audio processing API routes.
"""

import time
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
import httpx

from ..config import settings
from ..models.schemas import IntentResponse, ErrorResponse, AudioRecordingInfo, ConfirmIntentRequest, IntentDBStats
from ..services.azure_ml import call_azure_ml, call_azure_ml_hybrid, process_ml_response
from ..services.intent_logic import determine_status_and_action, get_ui_options
from ..services.intent_embeddings import (
    add_embedding, add_embeddings_batch, get_db_stats, 
    get_available_intents, clear_intent, _recompute_centroids
)
from ..services.logger import log_request

router = APIRouter(prefix="/api", tags=["Audio"])

# Temporary storage for pending embeddings (for learning loop)
_pending_embeddings: dict[str, list[float]] = {}


@router.post(
    "/audio",
    response_model=IntentResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid audio file"},
        502: {"model": ErrorResponse, "description": "ML endpoint error"},
        503: {"model": ErrorResponse, "description": "ML service unavailable"},
    },
)
async def process_audio(
    audio: UploadFile = File(...),
    hybrid_mode: bool = Query(False, description="Use both HuBERT and Wav2Vec for better accuracy")
):
    """
    Process patient audio and return detected intent with UI actions.
    
    ## Audio Recording Flow
    
    1. Patient presses "Speak" button on frontend
    2. Frontend uses Web Audio API / MediaRecorder to record audio
    3. Frontend converts recording to WAV format (16kHz, mono, 16-bit)
    4. Frontend sends WAV file to this endpoint
    5. Backend calls Azure ML for intent detection
    6. Backend returns intent + UI options for patient to confirm
    
    ## Requirements
    
    - **Format**: WAV audio file
    - **Sample Rate**: 16000 Hz (16kHz)
    - **Channels**: Mono (1 channel)
    - **Max Duration**: 3 seconds
    - **Max Size**: 1 MB
    
    ## Response
    
    Returns detected intent, confidence score, status, UI button options,
    and next action for the frontend to take.
    """
    start_time = time.time()
    
    # Step 1: Validate file exists
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_audio", "message": "No audio file provided"},
        )
    
    # Step 2: Validate .wav extension
    filename = audio.filename or ""
    if not filename.lower().endswith(".wav"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_audio", "message": "Only .wav files are accepted"},
        )
    
    # Step 3: Read file as raw bytes
    try:
        audio_bytes = await audio.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_audio", "message": f"Failed to read audio file: {str(e)}"},
        )
    
    # Validate file size
    if len(audio_bytes) > settings.MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_audio", "message": "Audio file exceeds 1MB limit"},
        )
    
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_audio", "message": "Audio file is empty"},
        )
    
    # Step 4: Send to Azure ML endpoint
    try:
        if hybrid_mode:
            ml_response = await call_azure_ml_hybrid(audio_bytes)
        else:
            ml_response = await call_azure_ml(audio_bytes)
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        log_request("UNKNOWN", 0.0, "error", latency_ms, "ml_timeout")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ml_unavailable", "message": "Please try again"},
        )
    except httpx.ConnectError:
        latency_ms = int((time.time() - start_time) * 1000)
        log_request("UNKNOWN", 0.0, "error", latency_ms, "ml_connection_error")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ml_unavailable", "message": "Cannot connect to ML service"},
        )
    except HTTPException:
        raise
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        log_request("UNKNOWN", 0.0, "error", latency_ms, str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "ml_unavailable", "message": str(e)},
        )
    
    # Step 5: Process ML response
    intent, confidence, transcription, alternatives, embedding = process_ml_response(ml_response)
    
    # Store embedding for potential learning (if from HuBERT)
    embedding_id = None
    if embedding:
        embedding_id = str(uuid.uuid4())
        _pending_embeddings[embedding_id] = embedding
        # Keep only last 100 pending embeddings
        if len(_pending_embeddings) > 100:
            oldest = list(_pending_embeddings.keys())[0]
            del _pending_embeddings[oldest]
    
    # Step 6: Apply business logic
    status_result, next_action = determine_status_and_action(intent, confidence)
    ui_options = get_ui_options(intent, status_result)
    
    # Log the request
    latency_ms = int((time.time() - start_time) * 1000)
    log_request(intent, confidence, status_result, latency_ms)
    
    # Step 7: Return structured JSON
    return IntentResponse(
        intent=intent,
        confidence=round(confidence, 2),
        status=status_result,
        ui_options=ui_options,
        next_action=next_action,
        transcription=transcription if transcription else None,
        alternatives=alternatives if alternatives else None,
        embedding_id=embedding_id,
        model_used=ml_response.get("model_used"),
    )


@router.get(
    "/audio/requirements",
    response_model=AudioRecordingInfo,
    tags=["Audio"],
)
async def get_audio_requirements():
    """
    Get audio recording requirements for frontend.
    
    Frontend should use these specifications when recording audio
    from the patient to ensure compatibility with the ML model.
    
    ## Frontend Implementation
    
    ```javascript
    // Example using MediaRecorder API
    const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
            sampleRate: 16000,
            channelCount: 1,
        }
    });
    
    const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'  // Record as webm
    });
    
    // After recording, convert to WAV before sending
    // Use a library like 'audiobuffer-to-wav' for conversion
    ```
    """
    return AudioRecordingInfo(
        format="wav",
        sample_rate=settings.SAMPLE_RATE,
        max_duration_seconds=settings.MAX_AUDIO_DURATION_SECONDS,
        max_size_bytes=settings.MAX_AUDIO_SIZE_BYTES,
        channels=1,
        bit_depth=16,
    )


@router.post(
    "/audio/confirm",
    tags=["Learning"],
)
async def confirm_intent(embedding_id: str, intent: str):
    """
    Confirm an intent to add the embedding to the learning database.
    
    Called when user confirms intent (blink = YES or caregiver tap).
    This is the learning loop - the system learns from confirmed intents.
    
    Args:
        embedding_id: The embedding_id from the previous /audio response
        intent: The confirmed intent (must be one of the allowed intents)
    """
    # Validate intent
    allowed_intents = get_available_intents()
    if intent not in allowed_intents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_intent", "message": f"Intent must be one of: {allowed_intents}"},
        )
    
    # Get pending embedding
    if embedding_id not in _pending_embeddings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "embedding_not_found", "message": "Embedding expired or not found"},
        )
    
    embedding = _pending_embeddings.pop(embedding_id)
    
    # Add to database
    success = add_embedding(intent, embedding)
    
    if success:
        return {"status": "ok", "message": f"Learned: {intent}", "db_stats": get_db_stats()}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "learn_failed", "message": "Failed to store embedding"},
        )


@router.post(
    "/audio/feedback",
    tags=["Learning"],
)
async def submit_feedback(
    embedding_id: str,
    predicted_intent: str,
    is_correct: bool,
    correct_intent: str = None
):
    """
    Submit feedback on a classification result.
    
    This is the main feedback loop for improving the system:
    - If is_correct=True: The embedding is added to the predicted intent's database
    - If is_correct=False: The embedding is added to the correct_intent's database (if provided)
    
    Args:
        embedding_id: The embedding_id from the previous /audio response
        predicted_intent: What the system predicted
        is_correct: True if prediction was correct, False otherwise
        correct_intent: If is_correct=False, what the correct intent should be
        
    Returns:
        Feedback status and updated database stats
    """
    allowed_intents = get_available_intents()
    
    # Validate predicted intent
    if predicted_intent not in allowed_intents and predicted_intent != "UNKNOWN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_intent", "message": f"predicted_intent must be one of: {allowed_intents}"},
        )
    
    # Get pending embedding
    if embedding_id not in _pending_embeddings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "embedding_not_found", "message": "Embedding expired or not found. Please try again."},
        )
    
    embedding = _pending_embeddings.pop(embedding_id)
    
    if is_correct:
        # User confirmed the prediction was correct - learn it!
        if predicted_intent == "UNKNOWN":
            return {
                "status": "ok",
                "message": "Feedback noted (UNKNOWN cannot be learned)",
                "learned": False,
                "db_stats": get_db_stats()
            }
        
        success = add_embedding(predicted_intent, embedding)
        return {
            "status": "ok",
            "message": f"✓ Learned: This audio = {predicted_intent}",
            "learned": True,
            "intent_learned": predicted_intent,
            "db_stats": get_db_stats()
        }
    else:
        # User said prediction was WRONG
        if not correct_intent:
            # User just said "no" but didn't specify correct intent
            return {
                "status": "ok",
                "message": "Feedback noted. Please select the correct intent to help us learn.",
                "learned": False,
                "needs_correction": True,
                "available_intents": allowed_intents,
                "db_stats": get_db_stats()
            }
        
        # Validate correct intent
        if correct_intent not in allowed_intents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_intent", "message": f"correct_intent must be one of: {allowed_intents}"},
            )
        
        # Learn the correct mapping
        success = add_embedding(correct_intent, embedding)
        return {
            "status": "ok",
            "message": f"✓ Corrected: This audio = {correct_intent} (not {predicted_intent})",
            "learned": True,
            "intent_learned": correct_intent,
            "corrected_from": predicted_intent,
            "db_stats": get_db_stats()
        }


@router.get(
    "/audio/intents",
    response_model=IntentDBStats,
    tags=["Learning"],
)
async def get_intents_stats():
    """
    Get available intents and how many samples each has.
    
    Use this to check if the system has enough training data.
    Recommended: 2-3 samples per intent minimum.
    """
    return IntentDBStats(intents=get_db_stats())


@router.get(
    "/audio/intents/list",
    tags=["Learning"],
)
async def list_available_intents():
    """
    Get list of available intents that can be detected.
    """
    return {"intents": get_available_intents()}


# =============================================================================
# TRAINING / ADMIN ENDPOINTS
# =============================================================================

@router.post(
    "/audio/train/batch",
    tags=["Training"],
)
async def train_batch(
    intent: str,
    audio_files: list[UploadFile] = File(...),
):
    """
    Upload multiple audio files to train a specific intent.
    
    This endpoint allows you to upload multiple audio samples at once
    to build the training database. Each audio file will be sent to
    the HuBERT model to extract embeddings, which are then stored.
    
    Args:
        intent: The intent to train (HELP, WATER, YES, NO, etc.)
        audio_files: List of WAV audio files
        
    Returns:
        Training results with success/failure counts
    """
    # Validate intent
    allowed_intents = get_available_intents()
    if intent not in allowed_intents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_intent", "message": f"Intent must be one of: {allowed_intents}"},
        )
    
    results = {
        "intent": intent,
        "total": len(audio_files),
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    embeddings_to_add = []
    
    for audio in audio_files:
        try:
            # Read audio
            audio_bytes = await audio.read()
            
            # Validate WAV
            if not audio.filename.lower().endswith(".wav"):
                results["errors"].append(f"{audio.filename}: Not a WAV file")
                results["failed"] += 1
                continue
            
            if len(audio_bytes) == 0:
                results["errors"].append(f"{audio.filename}: Empty file")
                results["failed"] += 1
                continue
            
            # Get embedding from HuBERT
            ml_response = await call_azure_ml(audio_bytes)
            
            if "embeddings" not in ml_response:
                results["errors"].append(f"{audio.filename}: No embeddings in response")
                results["failed"] += 1
                continue
            
            embeddings_to_add.append(ml_response["embeddings"])
            results["success"] += 1
            
        except Exception as e:
            results["errors"].append(f"{audio.filename}: {str(e)}")
            results["failed"] += 1
    
    # Batch add embeddings
    if embeddings_to_add:
        added = add_embeddings_batch(intent, embeddings_to_add)
        results["added_to_db"] = added
    
    results["db_stats"] = get_db_stats()
    
    return results


@router.delete(
    "/audio/train/{intent}",
    tags=["Training"],
)
async def clear_intent_data(intent: str):
    """
    Clear all training data for a specific intent.
    
    Use this to reset training for an intent if the samples
    are causing incorrect classifications.
    """
    allowed_intents = get_available_intents()
    if intent not in allowed_intents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_intent", "message": f"Intent must be one of: {allowed_intents}"},
        )
    
    success = clear_intent(intent)
    
    if success:
        return {"status": "ok", "message": f"Cleared all samples for {intent}", "db_stats": get_db_stats()}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "clear_failed", "message": f"Failed to clear {intent}"},
        )


@router.post(
    "/audio/train/single",
    tags=["Training"],
)
async def train_single(
    intent: str = Query(..., description="Intent to train"),
    audio: UploadFile = File(...),
):
    """
    Upload a single audio file to train a specific intent.
    
    Simpler version of /train/batch for adding one sample at a time.
    """
    allowed_intents = get_available_intents()
    if intent not in allowed_intents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_intent", "message": f"Intent must be one of: {allowed_intents}"},
        )
    
    # Read and validate audio
    audio_bytes = await audio.read()
    
    if not audio.filename.lower().endswith(".wav"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_audio", "message": "Only WAV files are accepted"},
        )
    
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_audio", "message": "Audio file is empty"},
        )
    
    # Get embedding from HuBERT
    try:
        ml_response = await call_azure_ml(audio_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "ml_failed", "message": str(e)},
        )
    
    if "embeddings" not in ml_response:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "no_embeddings", "message": "HuBERT did not return embeddings"},
        )
    
    # Add to database
    success = add_embedding(intent, ml_response["embeddings"])
    
    if success:
        return {
            "status": "ok",
            "message": f"Added 1 sample to {intent}",
            "db_stats": get_db_stats()
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "store_failed", "message": "Failed to store embedding"},
        )


@router.post(
    "/audio/recompute-centroids",
    tags=["Training"],
)
async def recompute_centroids():
    """
    Manually recompute intent centroids.
    
    This is automatically done when adding samples, but can be
    triggered manually if needed.
    """
    _recompute_centroids()
    return {"status": "ok", "message": "Centroids recomputed", "db_stats": get_db_stats()}
