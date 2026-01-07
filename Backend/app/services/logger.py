"""
Request logging service (in-memory, can be replaced with database).
"""

from datetime import datetime
from typing import Optional

# In-memory log storage
_request_logs: list[dict] = []
MAX_LOGS = 1000


def log_request(
    intent: str,
    confidence: float,
    status: str,
    latency_ms: int,
    error: Optional[str] = None
) -> None:
    """
    Log a request for audit purposes.
    
    Note: This stores in-memory. Replace with database for production.
    DO NOT store raw audio by default (privacy).
    
    Args:
        intent: Detected intent
        confidence: Confidence score
        status: Processing status
        latency_ms: Request latency in milliseconds
        error: Optional error message
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "intent": intent,
        "confidence": confidence,
        "status": status,
        "latency_ms": latency_ms,
    }
    
    if error:
        log_entry["error"] = error
    
    _request_logs.append(log_entry)
    
    # Keep only last MAX_LOGS entries
    if len(_request_logs) > MAX_LOGS:
        _request_logs.pop(0)


def get_recent_logs(limit: int = 100) -> list[dict]:
    """
    Get recent request logs.
    
    Args:
        limit: Maximum number of logs to return
        
    Returns:
        list: Recent log entries
    """
    return _request_logs[-limit:]


def clear_logs() -> None:
    """Clear all logs."""
    _request_logs.clear()
