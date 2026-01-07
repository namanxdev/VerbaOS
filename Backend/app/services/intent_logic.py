"""
Intent detection and business logic service.
"""

import re
from ..config import settings

# UI options per intent
UI_OPTIONS = {
    "HELP": ["Confirm Help", "Cancel"],
    "EMERGENCY": ["Cancel Emergency"],
    "WATER": ["Confirm Water", "Cancel"],
    "YES": ["OK"],
    "NO": ["OK"],
    "UNKNOWN": ["Repeat", "Cancel"],
}

# Intent keywords mapping (for transcription-based detection)
# More keywords = better matching
INTENT_KEYWORDS = {
    # Help-related
    "help": "HELP",
    "please": "HELP",
    "need": "HELP",
    "assist": "HELP",
    "assistance": "HELP",
    "helpme": "HELP",
    "help me": "HELP",
    "i need": "HELP",
    "call": "HELP",
    "someone": "HELP",
    "nurse": "HELP",
    "doctor": "HELP",
    
    # Emergency-related
    "emergency": "EMERGENCY",
    "urgent": "EMERGENCY",
    "danger": "EMERGENCY",
    "pain": "EMERGENCY",
    "hurt": "EMERGENCY",
    "hurts": "EMERGENCY",
    "fall": "EMERGENCY",
    "fallen": "EMERGENCY",
    "fell": "EMERGENCY",
    "chest": "EMERGENCY",
    "breathe": "EMERGENCY",
    "cant breathe": "EMERGENCY",
    "can't breathe": "EMERGENCY",
    "dying": "EMERGENCY",
    "severe": "EMERGENCY",
    
    # Water-related
    "water": "WATER",
    "thirsty": "WATER",
    "drink": "WATER",
    "thirst": "WATER",
    "beverage": "WATER",
    "juice": "WATER",
    "tea": "WATER",
    "coffee": "WATER",
    
    # Yes/No
    "yes": "YES",
    "yeah": "YES",
    "yep": "YES",
    "yup": "YES",
    "okay": "YES",
    "ok": "YES",
    "sure": "YES",
    "correct": "YES",
    "right": "YES",
    "affirmative": "YES",
    "no": "NO",
    "nope": "NO",
    "nah": "NO",
    "cancel": "NO",
    "stop": "NO",
    "dont": "NO",
    "don't": "NO",
    "negative": "NO",
    
    # Care-related (maps to HELP)
    "care": "HELP",
    "caregiver": "HELP",
}

# Fuzzy patterns for garbled wav2vec2 output
# These patterns match common misrecognitions
FUZZY_PATTERNS = [
    # HELP patterns (wav2vec2 often outputs "ALPE", "ULPE", "PE", etc.)
    (r'\b(alpe|ulpe|elpe|alp|ulp|elp)\b', "HELP", 0.70),
    (r'\b(i\s*pe|il\s*pe|you\s*pe|yo\s*pe)\b', "HELP", 0.65),
    (r'\bpe\b.*\bpe\b.*\bpe\b', "HELP", 0.60),  # Multiple "PE" sounds
    (r'\b(help|elp|halp)\b', "HELP", 0.85),
    
    # CARE patterns
    (r'\bcare\b', "HELP", 0.80),
    
    # WATER patterns
    (r'\b(water|wata|wate|wat)\b', "WATER", 0.80),
    (r'\b(thirsty|thirst|thirs)\b', "WATER", 0.75),
    
    # EMERGENCY patterns
    (r'\b(emergency|emergenc|emergen)\b', "EMERGENCY", 0.85),
    (r'\b(pain|pane|pai)\b', "EMERGENCY", 0.70),
    (r'\b(hurt|hurts|hort)\b', "EMERGENCY", 0.70),
    
    # YES patterns
    (r'^(yes|yeah|yep|yup|ya)$', "YES", 0.85),
    (r'\b(yes|yeah)\b', "YES", 0.75),
    
    # NO patterns
    (r'^(no|nope|nah)$', "NO", 0.85),
    (r'\b(no|nope)\b', "NO", 0.75),
]


def detect_intent_from_transcription(transcription: str) -> tuple[str, float]:
    """
    Detect intent from transcription text using keyword and fuzzy pattern matching.
    
    Args:
        transcription: Text transcription from speech
        
    Returns:
        tuple: (intent, confidence)
    """
    if not transcription:
        return "UNKNOWN", 0.0
    
    text = transcription.lower().strip()
    words = text.split()
    
    # Step 1: Check for exact word matches (highest confidence)
    for word in words:
        if word in INTENT_KEYWORDS:
            intent = INTENT_KEYWORDS[word]
            return intent, 0.85
    
    # Step 2: Check for partial keyword matches
    for keyword, intent in INTENT_KEYWORDS.items():
        if keyword in text:
            return intent, 0.75
    
    # Step 3: Try fuzzy pattern matching for garbled transcriptions
    for pattern, intent, confidence in FUZZY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"[DEBUG] Fuzzy match: '{pattern}' -> {intent} ({confidence})")
            return intent, confidence
    
    # Step 4: Check if text is mostly repetitive sounds (common in garbled output)
    # If we see repeated patterns like "PE PE PE", it might be "HELP"
    if len(words) >= 3:
        # Count repeated short syllables
        short_words = [w for w in words if len(w) <= 3]
        if len(short_words) >= len(words) * 0.6:
            # Mostly short syllables - likely garbled "HELP"
            return "HELP", 0.50
    
    return "UNKNOWN", 0.3


def determine_status_and_action(intent: str, confidence: float) -> tuple[str, str]:
    """
    Apply business logic to determine status and next action.
    
    Business rules:
    - Emergency with high confidence (>0.8) triggers immediately
    - confidence >= 0.75: confirmed
    - 0.4 <= confidence < 0.75: needs_confirmation
    - confidence < 0.4: uncertain
    
    Args:
        intent: Detected intent
        confidence: Confidence score
        
    Returns:
        tuple: (status, next_action)
    """
    # Emergency with high confidence triggers immediately
    if intent == "EMERGENCY" and confidence > 0.8:
        return "auto_triggered", "trigger_alert"
    
    # High confidence - confirmed
    if confidence >= settings.CONFIDENCE_CONFIRMED:
        if intent in ["YES", "NO"]:
            return "confirmed", "resolve_confirmation"
        return "confirmed", "await_user_confirmation"
    
    # Medium confidence - needs confirmation
    if confidence >= settings.CONFIDENCE_NEEDS_CONFIRMATION:
        return "needs_confirmation", "show_options"
    
    # Low confidence - uncertain
    return "uncertain", "ask_repeat"


def get_ui_options(intent: str, status: str) -> list[str]:
    """
    Get UI button options based on intent and status.
    
    Frontend must render these buttons exactly as provided.
    
    Args:
        intent: Detected intent
        status: Processing status
        
    Returns:
        list: UI button options
    """
    if status == "uncertain":
        return UI_OPTIONS.get("UNKNOWN", ["Repeat", "Cancel"])
    
    return UI_OPTIONS.get(intent, ["OK", "Cancel"])
