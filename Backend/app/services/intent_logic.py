"""
Intent detection and business logic service.
Optimized for stroke/aphasia patients with impaired speech.
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
    "PAIN": ["Confirm Pain", "Where?", "Cancel"],
    "BATHROOM": ["Confirm Bathroom", "Cancel"],
    "TIRED": ["Confirm Rest", "Cancel"],
    "COLD": ["Confirm Cold", "Cancel"],
    "HOT": ["Confirm Hot", "Cancel"],
    "UNKNOWN": ["Repeat", "Cancel"],
}

# =============================================================================
# PHONETIC ENCODING FOR APHASIA SPEECH
# =============================================================================
# Soundex-like encoding optimized for common aphasia speech patterns

def _aphasia_soundex(word: str) -> str:
    """
    Custom Soundex variant for aphasia speech patterns.
    Handles common speech impairments:
    - Consonant cluster reduction (str -> t)
    - Final consonant deletion (help -> hel)
    - Vowel simplification
    - Sound substitutions (th -> d/f)
    """
    if not word:
        return ""
    
    word = word.lower().strip()
    
    # Keep first letter
    first = word[0] if word else ""
    
    # Encoding map (similar sounds -> same code)
    # Optimized for aphasia substitution patterns
    encoding = {
        'b': '1', 'f': '1', 'p': '1', 'v': '1',  # Labials
        'c': '2', 'g': '2', 'j': '2', 'k': '2', 'q': '2', 's': '2', 'x': '2', 'z': '2',  # Gutturals/sibilants
        'd': '3', 't': '3', 'n': '3',  # Dentals (common aphasia confusion)
        'l': '4',  # Lateral
        'm': '5',  # Nasal labial
        'r': '6',  # Rhotic
        'w': '7', 'h': '7',  # Glides (often dropped in aphasia)
        'y': '8',  # Palatal
    }
    
    # Encode remaining characters
    code = first
    prev = encoding.get(first, '0')
    
    for char in word[1:]:
        curr = encoding.get(char, '0')
        if curr != '0' and curr != prev:
            code += curr
        prev = curr
    
    # Pad or truncate to 4 characters
    code = code[:4].ljust(4, '0')
    return code


def _phonetic_distance(word1: str, word2: str) -> float:
    """
    Calculate phonetic similarity between two words.
    Returns 0-1 where 1 is identical.
    """
    code1 = _aphasia_soundex(word1)
    code2 = _aphasia_soundex(word2)
    
    if code1 == code2:
        return 1.0
    
    # Count matching positions
    matches = sum(c1 == c2 for c1, c2 in zip(code1, code2))
    return matches / 4.0


# =============================================================================
# INTENT KEYWORDS WITH PHONETIC VARIANTS
# =============================================================================
# Each intent has canonical words + phonetic approximations common in aphasia

INTENT_PHONETIC_MAP = {
    "HELP": {
        "canonical": ["help", "help me", "need help", "assist", "please"],
        "aphasia_variants": [
            "hep", "elp", "hel", "he", "ep",  # Consonant deletion
            "hup", "halp", "hulp",  # Vowel substitution
            "hehp", "hehlp",  # Syllable repetition
            "pwease", "pease", "pees",  # "please" variants
        ]
    },
    "WATER": {
        "canonical": ["water", "thirsty", "drink", "want water"],
        "aphasia_variants": [
            "wawa", "wa-wa", "wata", "wah", "waw",  # Common simplifications
            "thir", "thirs", "dink", "dwink",
            "wotter", "wader", "wodder",
        ]
    },
    "YES": {
        "canonical": ["yes", "yeah", "yep", "okay", "ok", "sure"],
        "aphasia_variants": [
            "ya", "ye", "yah", "yeh", "uh huh", "mmhmm",
            "yesh", "yeth",  # Lisp variants
            "kay", "ohay",
        ]
    },
    "NO": {
        "canonical": ["no", "nope", "stop", "don't", "wait"],
        "aphasia_variants": [
            "na", "nah", "nuh", "uh uh", "mm mm",
            "noh", "naw", "doh",
            "top", "sop",  # 'stop' variants
        ]
    },
    "PAIN": {
        "canonical": ["pain", "hurt", "hurts", "ow", "ouch", "sore"],
        "aphasia_variants": [
            "pane", "pai", "pah", "pa",
            "hut", "huh", "oww", "ouw", "ah", "aah",
            "sor", "soah",
        ]
    },
    "EMERGENCY": {
        "canonical": ["emergency", "urgent", "help now", "doctor", "nurse"],
        "aphasia_variants": [
            "emergee", "emerguh", "mergency",
            "urgen", "doct", "docta", "nurs", "nurss",
            "quick", "quik", "now", "nao",
        ]
    },
    "BATHROOM": {
        "canonical": ["bathroom", "toilet", "potty", "pee", "restroom"],
        "aphasia_variants": [
            "bathoom", "bafroom", "baffoom", "toile", "toileh",
            "pott", "pee pee", "wee", "weewee",
        ]
    },
    "TIRED": {
        "canonical": ["tired", "sleepy", "sleep", "rest", "exhausted"],
        "aphasia_variants": [
            "tire", "tir", "seepy", "seep", "res", "napnap",
        ]
    },
    "COLD": {
        "canonical": ["cold", "freezing", "chilly", "blanket"],
        "aphasia_variants": [
            "col", "coh", "cowd", "freez", "blankie", "bwanket",
        ]
    },
    "HOT": {
        "canonical": ["hot", "warm", "sweating", "fan"],
        "aphasia_variants": [
            "hah", "hoh", "wam", "sweat", "fahn",
        ]
    },
}

# Legacy keyword mapping (kept for backward compatibility)
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
    
    # Pain-related
    "pain": "PAIN",
    "hurt": "PAIN",
    "hurts": "PAIN",
    "hurting": "PAIN",
    "ache": "PAIN",
    "sore": "PAIN",
    "ouch": "PAIN",
    "ow": "PAIN",
    
    # Bathroom-related
    "bathroom": "BATHROOM",
    "toilet": "BATHROOM",
    "potty": "BATHROOM",
    "pee": "BATHROOM",
    "restroom": "BATHROOM",
    
    # Tired/Sleep-related
    "tired": "TIRED",
    "sleepy": "TIRED",
    "sleep": "TIRED",
    "rest": "TIRED",
    "nap": "TIRED",
    "exhausted": "TIRED",
    "bed": "TIRED",
    
    # Temperature - Cold
    "cold": "COLD",
    "freezing": "COLD",
    "chilly": "COLD",
    "blanket": "COLD",
    
    # Temperature - Hot
    "hot": "HOT",
    "warm": "HOT",
    "sweating": "HOT",
    "sweaty": "HOT",
    "fan": "HOT",
}

# Fuzzy patterns for garbled wav2vec2 output
# These patterns match common misrecognitions
FUZZY_PATTERNS = [
    # HELP patterns (wav2vec2 often outputs "ALPE", "ULPE", "PE", etc.)
    (r'\b(alpe|ulpe|elpe|alp|ulp|elp)\b', "HELP", 0.70),
    (r'\b(i\s*pe|il\s*pe|you\s*pe|yo\s*pe)\b', "HELP", 0.65),
    (r'\bpe\b.*\bpe\b.*\bpe\b', "HELP", 0.60),  # Multiple "PE" sounds
    (r'\b(help|elp|halp|hep)\b', "HELP", 0.85),
    
    # CARE patterns
    (r'\bcare\b', "HELP", 0.80),
    
    # WATER patterns
    (r'\b(water|wata|wate|wat|wawa)\b', "WATER", 0.80),
    (r'\b(thirsty|thirst|thirs)\b', "WATER", 0.75),
    
    # EMERGENCY patterns
    (r'\b(emergency|emergenc|emergen|mergency)\b', "EMERGENCY", 0.85),
    (r'\b(urgent|urgen)\b', "EMERGENCY", 0.80),
    
    # PAIN patterns - separate from emergency for clarity
    (r'\b(pain|pane|pai|pah)\b', "PAIN", 0.75),
    (r'\b(hurt|hurts|hort|hut)\b', "PAIN", 0.75),
    (r'\b(ow+|ouch|ah+)\b', "PAIN", 0.65),
    
    # YES patterns
    (r'^(yes|yeah|yep|yup|ya)$', "YES", 0.85),
    (r'\b(yes|yeah)\b', "YES", 0.75),
    (r'^(ok|okay|kay)$', "YES", 0.80),
    (r'\b(uh\s*huh|mm\s*hmm)\b', "YES", 0.70),
    
    # NO patterns
    (r'^(no|nope|nah)$', "NO", 0.85),
    (r'\b(no|nope)\b', "NO", 0.75),
    (r'\b(uh\s*uh|mm\s*mm)\b', "NO", 0.70),
    
    # BATHROOM patterns
    (r'\b(bathroom|bathoom|bafroom)\b', "BATHROOM", 0.80),
    (r'\b(toilet|toile)\b', "BATHROOM", 0.80),
    (r'\b(potty|pott|pee|wee)\b', "BATHROOM", 0.75),
    
    # TIRED patterns
    (r'\b(tired|tire|tir)\b', "TIRED", 0.80),
    (r'\b(sleep|sleepy|seep)\b', "TIRED", 0.75),
    
    # COLD patterns
    (r'\b(cold|col|coh|cowd)\b', "COLD", 0.80),
    (r'\b(blanket|blankie)\b', "COLD", 0.75),
    
    # HOT patterns
    (r'\b(hot|hah|hoh)\b', "HOT", 0.80),
    (r'\b(warm|wam)\b', "HOT", 0.75),
]


def _phonetic_intent_match(word: str) -> tuple[str, float]:
    """
    Match a word to intents using phonetic similarity.
    Handles aphasia speech patterns.
    """
    best_intent = None
    best_score = 0.0
    
    for intent, variants in INTENT_PHONETIC_MAP.items():
        # Check canonical words
        for canonical in variants["canonical"]:
            if word == canonical:
                return intent, 0.95
            score = _phonetic_distance(word, canonical)
            if score > best_score:
                best_score = score
                best_intent = intent
        
        # Check aphasia variants (slightly lower confidence)
        for variant in variants["aphasia_variants"]:
            if word == variant:
                return intent, 0.85
            score = _phonetic_distance(word, variant) * 0.9  # 10% penalty for variant match
            if score > best_score:
                best_score = score
                best_intent = intent
    
    return best_intent, best_score


def detect_intent_from_transcription(transcription: str) -> tuple[str, float]:
    """
    Detect intent from transcription text using multi-stage matching.
    Optimized for garbled/impaired speech from aphasia patients.
    
    Matching stages (in order of confidence):
    1. Exact word match in keyword dictionary (0.90)
    2. Phonetic matching for aphasia variants (0.75-0.90)
    3. Partial keyword match (0.70)
    4. Fuzzy regex patterns (0.60-0.85)
    5. Repetitive syllable analysis (0.50)
    
    Args:
        transcription: Text transcription from speech
        
    Returns:
        tuple: (intent, confidence)
    """
    if not transcription:
        return "UNKNOWN", 0.0
    
    text = transcription.lower().strip()
    words = text.split()
    
    print(f"[DEBUG] Analyzing transcription: '{text}'")
    
    # -------------------------------------------------------------------------
    # Stage 1: Exact word match (highest confidence)
    # -------------------------------------------------------------------------
    for word in words:
        if word in INTENT_KEYWORDS:
            intent = INTENT_KEYWORDS[word]
            print(f"[DEBUG] Stage 1 - Exact match: '{word}' -> {intent}")
            return intent, 0.90
    
    # -------------------------------------------------------------------------
    # Stage 2: Phonetic matching for aphasia speech patterns
    # -------------------------------------------------------------------------
    phonetic_candidates = []
    for word in words:
        intent, score = _phonetic_intent_match(word)
        if intent and score >= 0.6:  # Threshold for phonetic match
            phonetic_candidates.append((intent, score, word))
    
    if phonetic_candidates:
        # Sort by score and take best
        phonetic_candidates.sort(key=lambda x: x[1], reverse=True)
        best_intent, best_score, matched_word = phonetic_candidates[0]
        print(f"[DEBUG] Stage 2 - Phonetic match: '{matched_word}' -> {best_intent} ({best_score:.2f})")
        return best_intent, best_score
    
    # -------------------------------------------------------------------------
    # Stage 3: Partial keyword match
    # -------------------------------------------------------------------------
    for keyword, intent in INTENT_KEYWORDS.items():
        if keyword in text:
            print(f"[DEBUG] Stage 3 - Partial match: '{keyword}' in text -> {intent}")
            return intent, 0.70
    
    # -------------------------------------------------------------------------
    # Stage 4: Fuzzy regex patterns for garbled transcriptions
    # -------------------------------------------------------------------------
    for pattern, intent, confidence in FUZZY_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"[DEBUG] Stage 4 - Fuzzy pattern: '{pattern}' -> {intent} ({confidence})")
            return intent, confidence
    
    # -------------------------------------------------------------------------
    # Stage 5: Repetitive syllable analysis (common in aphasia)
    # -------------------------------------------------------------------------
    # If we see repeated patterns like "PE PE PE", it might be "HELP"
    if len(words) >= 2:
        # Count repeated short syllables
        short_words = [w for w in words if len(w) <= 3]
        
        if len(short_words) >= len(words) * 0.5:  # Majority short syllables
            # Check if they sound similar (aphasia repetition)
            if len(short_words) >= 2:
                first_code = _aphasia_soundex(short_words[0])
                similar_count = sum(1 for w in short_words[1:] if _aphasia_soundex(w) == first_code)
                
                if similar_count >= len(short_words) * 0.4:
                    # Repetitive similar sounds - likely attempting "HELP"
                    print(f"[DEBUG] Stage 5 - Repetitive syllables detected: {short_words}")
                    return "HELP", 0.50
    
    # -------------------------------------------------------------------------
    # No match found
    # -------------------------------------------------------------------------
    print(f"[DEBUG] No intent match found for: '{text}'")
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
