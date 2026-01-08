"""
User and notification management for Patient-Caretaker system.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["Users"])

# Data storage files
DATA_DIR = Path(__file__).parent.parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


# =============================================================================
# MODELS
# =============================================================================

class UserCreate(BaseModel):
    name: str
    role: str  # "patient" or "caretaker"
    
class UserResponse(BaseModel):
    id: str
    name: str
    role: str
    created_at: str
    
class LinkCaretaker(BaseModel):
    caretaker_id: str
    
class NotificationCreate(BaseModel):
    patient_id: str
    intent: str
    message: str
    confidence: float = 0.0
    transcription: str = ""

class NotificationResponse(BaseModel):
    id: str
    patient_id: str
    patient_name: str
    intent: str
    message: str
    confidence: float
    transcription: str
    timestamp: str
    read: bool


# =============================================================================
# DATA HELPERS
# =============================================================================

def _load_users() -> dict:
    """Load users database."""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"patients": {}, "caretakers": {}}

def _save_users(data: dict):
    """Save users database."""
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _load_notifications() -> list:
    """Load notifications database."""
    if NOTIFICATIONS_FILE.exists():
        try:
            with open(NOTIFICATIONS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def _save_notifications(data: list):
    """Save notifications database."""
    with open(NOTIFICATIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# =============================================================================
# USER ENDPOINTS
# =============================================================================

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    """
    Register a new user as either patient or caretaker.
    """
    if user.role not in ["patient", "caretaker"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'patient' or 'caretaker'"
        )
    
    users = _load_users()
    
    user_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    
    user_data = {
        "id": user_id,
        "name": user.name,
        "role": user.role,
        "created_at": timestamp,
        "caretakers": [] if user.role == "patient" else None,
        "patients": [] if user.role == "caretaker" else None,
    }
    
    if user.role == "patient":
        users["patients"][user_id] = user_data
    else:
        users["caretakers"][user_id] = user_data
    
    _save_users(users)
    
    return UserResponse(
        id=user_id,
        name=user.name,
        role=user.role,
        created_at=timestamp
    )


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Get user information by ID."""
    users = _load_users()
    
    # Check patients
    if user_id in users["patients"]:
        return users["patients"][user_id]
    
    # Check caretakers
    if user_id in users["caretakers"]:
        return users["caretakers"][user_id]
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.get("/")
async def list_users(role: Optional[str] = None):
    """List all users, optionally filtered by role."""
    users = _load_users()
    
    if role == "patient":
        return {"users": list(users["patients"].values())}
    elif role == "caretaker":
        return {"users": list(users["caretakers"].values())}
    else:
        all_users = list(users["patients"].values()) + list(users["caretakers"].values())
        return {"users": all_users}


# =============================================================================
# PATIENT-CARETAKER LINKING
# =============================================================================

@router.post("/patients/{patient_id}/link-caretaker")
async def link_caretaker_to_patient(patient_id: str, link: LinkCaretaker):
    """
    Link a caretaker to a patient.
    Both patient and caretaker must exist.
    """
    users = _load_users()
    
    if patient_id not in users["patients"]:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if link.caretaker_id not in users["caretakers"]:
        raise HTTPException(status_code=404, detail="Caretaker not found")
    
    patient = users["patients"][patient_id]
    caretaker = users["caretakers"][link.caretaker_id]
    
    # Add caretaker to patient's list
    if link.caretaker_id not in patient["caretakers"]:
        patient["caretakers"].append(link.caretaker_id)
    
    # Add patient to caretaker's list
    if patient_id not in caretaker["patients"]:
        caretaker["patients"].append(patient_id)
    
    _save_users(users)
    
    return {
        "status": "ok",
        "message": f"Linked caretaker {caretaker['name']} to patient {patient['name']}",
        "patient": patient,
        "caretaker": caretaker
    }


@router.delete("/patients/{patient_id}/unlink-caretaker/{caretaker_id}")
async def unlink_caretaker_from_patient(patient_id: str, caretaker_id: str):
    """Remove a caretaker from a patient."""
    users = _load_users()
    
    if patient_id not in users["patients"]:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if caretaker_id not in users["caretakers"]:
        raise HTTPException(status_code=404, detail="Caretaker not found")
    
    patient = users["patients"][patient_id]
    caretaker = users["caretakers"][caretaker_id]
    
    if caretaker_id in patient["caretakers"]:
        patient["caretakers"].remove(caretaker_id)
    
    if patient_id in caretaker["patients"]:
        caretaker["patients"].remove(patient_id)
    
    _save_users(users)
    
    return {"status": "ok", "message": "Unlinked successfully"}


@router.get("/patients/{patient_id}/caretakers")
async def get_patient_caretakers(patient_id: str):
    """Get all caretakers for a patient."""
    users = _load_users()
    
    if patient_id not in users["patients"]:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient = users["patients"][patient_id]
    caretaker_ids = patient.get("caretakers", [])
    
    caretakers = [
        users["caretakers"][cid] 
        for cid in caretaker_ids 
        if cid in users["caretakers"]
    ]
    
    return {"patient": patient, "caretakers": caretakers}


@router.get("/caretakers/{caretaker_id}/patients")
async def get_caretaker_patients(caretaker_id: str):
    """Get all patients for a caretaker."""
    users = _load_users()
    
    if caretaker_id not in users["caretakers"]:
        raise HTTPException(status_code=404, detail="Caretaker not found")
    
    caretaker = users["caretakers"][caretaker_id]
    patient_ids = caretaker.get("patients", [])
    
    patients = [
        users["patients"][pid] 
        for pid in patient_ids 
        if pid in users["patients"]
    ]
    
    return {"caretaker": caretaker, "patients": patients}


# =============================================================================
# NOTIFICATIONS
# =============================================================================

@router.post("/notifications")
async def send_notification(notification: NotificationCreate):
    """
    Send a notification from a patient to all their caretakers.
    Called when patient makes a request (e.g., asks for water).
    """
    users = _load_users()
    
    if notification.patient_id not in users["patients"]:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient = users["patients"][notification.patient_id]
    
    notif_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()
    
    notif_data = {
        "id": notif_id,
        "patient_id": notification.patient_id,
        "patient_name": patient["name"],
        "intent": notification.intent,
        "message": notification.message,
        "confidence": notification.confidence,
        "transcription": notification.transcription,
        "timestamp": timestamp,
        "read": False,
        "caretaker_ids": patient.get("caretakers", [])
    }
    
    notifications = _load_notifications()
    notifications.insert(0, notif_data)  # Newest first
    
    # Keep only last 500 notifications
    notifications = notifications[:500]
    
    _save_notifications(notifications)
    
    return {
        "status": "ok",
        "notification_id": notif_id,
        "sent_to_caretakers": len(patient.get("caretakers", [])),
        "notification": notif_data
    }


@router.get("/caretakers/{caretaker_id}/notifications")
async def get_caretaker_notifications(
    caretaker_id: str, 
    unread_only: bool = False,
    limit: int = 50
):
    """Get all notifications for a caretaker from their patients."""
    users = _load_users()
    
    if caretaker_id not in users["caretakers"]:
        raise HTTPException(status_code=404, detail="Caretaker not found")
    
    notifications = _load_notifications()
    
    # Filter notifications for this caretaker
    caretaker_notifs = [
        n for n in notifications 
        if caretaker_id in n.get("caretaker_ids", [])
    ]
    
    if unread_only:
        caretaker_notifs = [n for n in caretaker_notifs if not n.get("read", False)]
    
    return {
        "notifications": caretaker_notifs[:limit],
        "total": len(caretaker_notifs),
        "unread": len([n for n in caretaker_notifs if not n.get("read", False)])
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, caretaker_id: str):
    """Mark a notification as read by a caretaker."""
    notifications = _load_notifications()
    
    for notif in notifications:
        if notif["id"] == notification_id:
            notif["read"] = True
            _save_notifications(notifications)
            return {"status": "ok", "message": "Marked as read"}
    
    raise HTTPException(status_code=404, detail="Notification not found")


@router.get("/patients/{patient_id}/notifications")
async def get_patient_notifications(patient_id: str, limit: int = 20):
    """Get notification history for a patient (their own requests)."""
    users = _load_users()
    
    if patient_id not in users["patients"]:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    notifications = _load_notifications()
    
    patient_notifs = [
        n for n in notifications 
        if n.get("patient_id") == patient_id
    ]
    
    return {
        "notifications": patient_notifs[:limit],
        "total": len(patient_notifs)
    }
