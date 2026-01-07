"""
Business logic and external service integrations.
"""

from .azure_ml import call_azure_ml, process_ml_response
from .intent_logic import (
    detect_intent_from_transcription,
    determine_status_and_action,
    get_ui_options,
)
from .logger import log_request, get_recent_logs

__all__ = [
    "call_azure_ml",
    "process_ml_response",
    "detect_intent_from_transcription",
    "determine_status_and_action",
    "get_ui_options",
    "log_request",
    "get_recent_logs",
]
