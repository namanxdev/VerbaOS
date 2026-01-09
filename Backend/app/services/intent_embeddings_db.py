"""
Embedding-based intent classification using PostgreSQL pgvector.
Uses Azure PostgreSQL with native vector similarity search.

Optimized for stroke/aphasia patients with varied speech patterns:
- Cosine similarity via pgvector <=> operator
- Weighted scoring with nearest neighbors
- Confidence calibration for realistic uncertainty estimates
"""

import numpy as np
from typing import Optional, List, Tuple

from app.services.postgres_db import get_db

# Fixed intent set for stroke/aphasia patients
INTENTS = [
    "HELP",       # General assistance
    "WATER",      # Thirst/hydration
    "YES",        # Affirmative
    "NO",         # Negative
    "PAIN",       # Discomfort
    "EMERGENCY",  # Urgent medical
    "BATHROOM",   # Toileting
    "TIRED",      # Rest/sleep
    "COLD",       # Temperature - cold
    "HOT",        # Temperature - hot
]

# Classification parameters - tuned for aphasia speech variability
MIN_SAMPLES_FOR_PREDICTION = 2
K_NEIGHBORS = 5
CONFIDENCE_THRESHOLD = 0.65
HIGH_CONFIDENCE_THRESHOLD = 0.80
SIMILARITY_MARGIN = 0.05


def _calibrate_confidence(raw_score: float, margin: float, num_samples: int) -> float:
    """
    Calibrate confidence score for more realistic uncertainty estimates.
    """
    confidence = raw_score
    
    if margin < SIMILARITY_MARGIN:
        confidence *= 0.8
    
    if num_samples < 5:
        confidence *= 0.85
    elif num_samples < 10:
        confidence *= 0.95
    
    return max(0.0, min(1.0, confidence))


async def predict_intent_db(embedding: List[float]) -> Tuple[str, float, List[str], List[Tuple[str, float]]]:
    """
    Predict intent using PostgreSQL pgvector cosine similarity.
    
    Args:
        embedding: 768-dimensional HuBERT embedding
        
    Returns:
        tuple: (best_intent, confidence, alternatives, top_predictions)
    """
    db = await get_db()
    
    # Get stats to check sample counts
    stats = await db.get_intent_stats()
    
    # Check if we have enough samples
    valid_intents = {k: v for k, v in stats.items() if v >= MIN_SAMPLES_FOR_PREDICTION}
    
    if not valid_intents:
        print("[WARNING] No trained intents in database - classification unavailable")
        return "UNKNOWN", 0.0, INTENTS[:3], [("UNKNOWN", 0.0)]
    
    # Get nearest neighbors using pgvector
    neighbors = await db.find_similar_intents(embedding, k=K_NEIGHBORS * len(valid_intents))
    
    if not neighbors:
        return "UNKNOWN", 0.0, INTENTS[:3], [("UNKNOWN", 0.0)]
    
    # Aggregate scores by intent
    intent_scores = {}
    intent_similarities = {}
    
    for intent, similarity, _ in neighbors:
        if intent not in intent_scores:
            intent_scores[intent] = []
            intent_similarities[intent] = []
        intent_scores[intent].append(similarity)
        intent_similarities[intent].append(similarity)
    
    # Calculate combined scores for each intent
    combined_scores = {}
    for intent, similarities in intent_scores.items():
        if len(similarities) < MIN_SAMPLES_FOR_PREDICTION:
            continue
        
        # Weighted KNN score
        weights = [s ** 2 for s in similarities[:K_NEIGHBORS]]
        total_weight = sum(weights) if weights else 1
        knn_score = sum(s * w for s, w in zip(similarities[:K_NEIGHBORS], weights)) / total_weight if total_weight > 0 else 0
        
        # Max score
        max_score = max(similarities) if similarities else 0
        
        # Centroid approximation (average of top similarities)
        centroid_score = np.mean(similarities[:K_NEIGHBORS]) if similarities else 0
        
        # Combined score
        combined = 0.3 * centroid_score + 0.5 * knn_score + 0.2 * max_score
        combined_scores[intent] = combined
    
    if not combined_scores:
        return "UNKNOWN", 0.0, INTENTS[:3], [("UNKNOWN", 0.0)]
    
    # Sort by score
    sorted_intents = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Calibrate confidence
    calibrated_predictions = []
    for i, (intent, raw_score) in enumerate(sorted_intents):
        num_samples = stats.get(intent, 0)
        next_score = sorted_intents[i + 1][1] if i + 1 < len(sorted_intents) else 0.0
        margin = raw_score - next_score
        calibrated = _calibrate_confidence(raw_score, margin, num_samples)
        calibrated_predictions.append((intent, calibrated))
    
    # Re-sort by calibrated confidence
    calibrated_predictions.sort(key=lambda x: x[1], reverse=True)
    
    # Get results
    top_predictions = calibrated_predictions[:3]
    best_intent = top_predictions[0][0]
    confidence = top_predictions[0][1]
    alternatives = [intent for intent, _ in top_predictions[1:4]]
    
    print(f"[DEBUG] Intent prediction (DB): {best_intent}")
    print(f"[DEBUG]   Calibrated confidence: {confidence:.3f}")
    print(f"[DEBUG]   Top 3: {top_predictions}")
    
    return best_intent, confidence, alternatives, top_predictions


async def add_embedding_db(intent: str, embedding: List[float]) -> bool:
    """
    Add a confirmed embedding to the PostgreSQL database.
    Called when user confirms intent (learning loop).
    """
    if intent not in INTENTS:
        print(f"[ERROR] Unknown intent: {intent}")
        return False
    
    db = await get_db()
    success = await db.add_embedding(intent, embedding)
    
    if success:
        stats = await db.get_intent_stats()
        print(f"[INFO] Added embedding to {intent}, now has {stats.get(intent, 0)} samples")
    
    return success


async def add_embeddings_batch_db(intent: str, embeddings: List[List[float]]) -> int:
    """
    Add multiple embeddings to an intent at once.
    """
    if intent not in INTENTS:
        print(f"[ERROR] Unknown intent: {intent}")
        return 0
    
    db = await get_db()
    count = await db.add_embeddings_batch(intent, embeddings)
    
    stats = await db.get_intent_stats()
    print(f"[INFO] Added {count} embeddings to {intent}, now has {stats.get(intent, 0)} samples")
    
    return count


async def get_db_stats_async() -> dict:
    """Get statistics about the intent database."""
    db = await get_db()
    return await db.get_intent_stats()


def get_available_intents() -> List[str]:
    """Get list of available intents."""
    return INTENTS.copy()


async def clear_intent_db(intent: str) -> bool:
    """Clear all embeddings for an intent."""
    db = await get_db()
    count = await db.clear_intent_embeddings(intent)
    return count > 0
