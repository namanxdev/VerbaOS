"""
Embedding-based intent classification using advanced similarity techniques.
No text conversion needed - works directly with HuBERT embeddings.

Optimized for stroke/aphasia patients with varied speech patterns:
- Weighted K-Nearest Neighbors (KNN) with distance weighting
- Centroid + nearest neighbor hybrid scoring
- Confidence calibration for realistic uncertainty estimates
- Minimum sample thresholds for robust predictions
"""

import json
import os
import numpy as np
from pathlib import Path
from typing import Optional

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
MIN_SAMPLES_FOR_PREDICTION = 2  # Minimum samples per intent before we trust it
K_NEIGHBORS = 5  # Number of nearest neighbors to consider
CONFIDENCE_THRESHOLD = 0.65  # Below this, mark as uncertain
HIGH_CONFIDENCE_THRESHOLD = 0.80  # Above this, high confidence
SIMILARITY_MARGIN = 0.05  # Minimum margin between top-2 for confident prediction

# In-memory intent database (embeddings per intent)
_intent_db: dict[str, list[list[float]]] = {intent: [] for intent in INTENTS}

# Cached centroids for faster prediction
_intent_centroids: dict[str, Optional[np.ndarray]] = {intent: None for intent in INTENTS}

# File path for persistence
DB_FILE = Path(__file__).parent.parent.parent / "intent_embeddings.json"


def _load_db():
    """Load intent database from file."""
    global _intent_db
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r") as f:
                loaded = json.load(f)
                # Merge with INTENTS (in case new intents added)
                for intent in INTENTS:
                    _intent_db[intent] = loaded.get(intent, [])
            print(f"[INFO] Loaded intent DB with {sum(len(v) for v in _intent_db.values())} embeddings")
            _recompute_centroids()
        except Exception as e:
            print(f"[WARNING] Could not load intent DB: {e}")


def _save_db():
    """Save intent database to file."""
    try:
        with open(DB_FILE, "w") as f:
            json.dump(_intent_db, f)
        print(f"[INFO] Saved intent DB")
    except Exception as e:
        print(f"[ERROR] Could not save intent DB: {e}")


def _recompute_centroids():
    """Recompute centroid vectors for all intents with samples."""
    global _intent_centroids
    for intent, samples in _intent_db.items():
        if len(samples) >= MIN_SAMPLES_FOR_PREDICTION:
            _intent_centroids[intent] = np.mean(np.array(samples), axis=0)
        else:
            _intent_centroids[intent] = None
    print(f"[INFO] Recomputed centroids for {sum(1 for c in _intent_centroids.values() if c is not None)} intents")


# Load on import
_load_db()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _get_top_k_similarities(embedding: np.ndarray, samples: list[list[float]], k: int) -> list[float]:
    """Get top-k cosine similarities for an embedding against samples."""
    if not samples:
        return []
    
    similarities = [
        cosine_similarity(embedding, np.array(sample))
        for sample in samples
    ]
    similarities.sort(reverse=True)
    return similarities[:k]


def _weighted_knn_score(top_k_sims: list[float]) -> float:
    """
    Calculate weighted KNN score with distance-based weighting.
    Closer neighbors (higher similarity) get more weight.
    """
    if not top_k_sims:
        return 0.0
    
    # Use squared similarities as weights (emphasize closer neighbors)
    weights = [s ** 2 for s in top_k_sims]
    total_weight = sum(weights)
    
    if total_weight == 0:
        return 0.0
    
    weighted_score = sum(s * w for s, w in zip(top_k_sims, weights)) / total_weight
    return weighted_score


def _calibrate_confidence(raw_score: float, margin: float, num_samples: int) -> float:
    """
    Calibrate confidence score for more realistic uncertainty estimates.
    
    Args:
        raw_score: Raw similarity score (0-1)
        margin: Difference between top-1 and top-2 scores
        num_samples: Number of training samples for this intent
        
    Returns:
        Calibrated confidence score
    """
    # Base confidence from raw score
    confidence = raw_score
    
    # Penalize if margin is too small (ambiguous between intents)
    if margin < SIMILARITY_MARGIN:
        confidence *= 0.8  # 20% penalty for ambiguous cases
    
    # Penalize if too few training samples
    if num_samples < 5:
        confidence *= 0.85  # 15% penalty for limited training data
    elif num_samples < 10:
        confidence *= 0.95  # 5% penalty for moderate training data
    
    # Ensure confidence stays in valid range
    return max(0.0, min(1.0, confidence))


def predict_intent(embedding: list[float]) -> tuple[str, float, list[str]]:
    """
    Predict intent using advanced similarity techniques optimized for aphasia speech.
    
    Uses a hybrid approach:
    1. Centroid similarity for intents with enough samples
    2. Weighted KNN for fine-grained matching
    3. Confidence calibration based on margin and sample count
    
    Args:
        embedding: 768-dimensional HuBERT embedding
        
    Returns:
        tuple: (best_intent, confidence, alternatives)
    """
    embedding_arr = np.array(embedding)
    
    scores = {}
    knn_details = {}  # Store detailed scoring info
    
    for intent, samples in _intent_db.items():
        if len(samples) < MIN_SAMPLES_FOR_PREDICTION:
            continue
        
        # Method 1: Centroid similarity (fast, good for well-clustered data)
        centroid = _intent_centroids.get(intent)
        centroid_score = 0.0
        if centroid is not None:
            centroid_score = cosine_similarity(embedding_arr, centroid)
        
        # Method 2: Weighted KNN (better for varied speech patterns)
        top_k = _get_top_k_similarities(embedding_arr, samples, K_NEIGHBORS)
        knn_score = _weighted_knn_score(top_k)
        
        # Method 3: Max similarity (best single match)
        max_score = max(top_k) if top_k else 0.0
        
        # Combine scores: weighted average favoring KNN for varied speech
        # KNN is better for aphasia because speech patterns vary significantly
        combined_score = (
            0.3 * centroid_score +  # General cluster direction
            0.5 * knn_score +       # Weighted nearest neighbors (most important)
            0.2 * max_score         # Best single match
        )
        
        scores[intent] = combined_score
        knn_details[intent] = {
            "centroid": centroid_score,
            "knn": knn_score,
            "max": max_score,
            "num_samples": len(samples)
        }
    
    if not scores:
        # No samples stored yet - return unknown with suggestions
        print("[WARNING] No trained intents in database - classification unavailable")
        return "UNKNOWN", 0.0, INTENTS[:3]
    
    # Sort by score
    sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    best_intent, best_score = sorted_intents[0]
    second_score = sorted_intents[1][1] if len(sorted_intents) > 1 else 0.0
    
    # Calculate margin between top-2 predictions
    margin = best_score - second_score
    
    # Calibrate confidence
    num_samples = len(_intent_db.get(best_intent, []))
    confidence = _calibrate_confidence(best_score, margin, num_samples)
    
    # Get alternatives (next 2 best)
    alternatives = [intent for intent, _ in sorted_intents[1:4]]
    
    # Debug logging
    details = knn_details.get(best_intent, {})
    print(f"[DEBUG] Intent prediction: {best_intent}")
    print(f"[DEBUG]   Raw score: {best_score:.3f}, Calibrated: {confidence:.3f}")
    print(f"[DEBUG]   Centroid: {details.get('centroid', 0):.3f}, KNN: {details.get('knn', 0):.3f}, Max: {details.get('max', 0):.3f}")
    print(f"[DEBUG]   Margin: {margin:.3f}, Samples: {num_samples}")
    print(f"[DEBUG]   Alternatives: {alternatives}")
    
    return best_intent, confidence, alternatives


def predict_intent_with_details(embedding: list[float]) -> dict:
    """
    Predict intent with detailed scoring breakdown.
    Useful for debugging and understanding model behavior.
    
    Returns:
        dict with intent, confidence, alternatives, and per-intent scores
    """
    embedding_arr = np.array(embedding)
    
    all_scores = {}
    
    for intent, samples in _intent_db.items():
        if len(samples) < MIN_SAMPLES_FOR_PREDICTION:
            all_scores[intent] = {
                "score": 0.0,
                "num_samples": len(samples),
                "status": "insufficient_samples"
            }
            continue
        
        centroid = _intent_centroids.get(intent)
        centroid_score = cosine_similarity(embedding_arr, centroid) if centroid is not None else 0.0
        
        top_k = _get_top_k_similarities(embedding_arr, samples, K_NEIGHBORS)
        knn_score = _weighted_knn_score(top_k)
        max_score = max(top_k) if top_k else 0.0
        
        combined = 0.3 * centroid_score + 0.5 * knn_score + 0.2 * max_score
        
        all_scores[intent] = {
            "score": combined,
            "centroid_score": centroid_score,
            "knn_score": knn_score,
            "max_score": max_score,
            "num_samples": len(samples),
            "status": "active"
        }
    
    intent, confidence, alternatives = predict_intent(embedding)
    
    return {
        "intent": intent,
        "confidence": confidence,
        "alternatives": alternatives,
        "all_scores": all_scores
    }


def add_embedding(intent: str, embedding: list[float]) -> bool:
    """
    Add a confirmed embedding to the intent database.
    Called when user confirms intent (learning loop).
    
    Args:
        intent: The confirmed intent
        embedding: The 768-d embedding to store
        
    Returns:
        bool: Success
    """
    if intent not in INTENTS:
        print(f"[ERROR] Unknown intent: {intent}")
        return False
    
    _intent_db[intent].append(embedding)
    _save_db()
    _recompute_centroids()  # Update centroids after adding new sample
    
    print(f"[INFO] Added embedding to {intent}, now has {len(_intent_db[intent])} samples")
    return True


def add_embeddings_batch(intent: str, embeddings: list[list[float]]) -> int:
    """
    Add multiple embeddings to an intent at once.
    More efficient than calling add_embedding repeatedly.
    
    Args:
        intent: The intent to add embeddings to
        embeddings: List of 768-d embeddings
        
    Returns:
        int: Number of embeddings added
    """
    if intent not in INTENTS:
        print(f"[ERROR] Unknown intent: {intent}")
        return 0
    
    _intent_db[intent].extend(embeddings)
    _save_db()
    _recompute_centroids()
    
    print(f"[INFO] Added {len(embeddings)} embeddings to {intent}, now has {len(_intent_db[intent])} samples")
    return len(embeddings)


def get_db_stats() -> dict:
    """Get statistics about the intent database."""
    return {
        intent: len(samples) 
        for intent, samples in _intent_db.items()
    }


def get_available_intents() -> list[str]:
    """Get list of available intents."""
    return INTENTS.copy()


def clear_intent(intent: str) -> bool:
    """Clear all embeddings for an intent."""
    if intent in _intent_db:
        _intent_db[intent] = []
        _save_db()
        return True
    return False
