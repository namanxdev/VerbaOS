"""
User and notification management for Patient-Caretaker system.
Uses PostgreSQL database with asyncpg for persistence.
"""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from app.services.postgres_db import get_db, PostgresDB

router = APIRouter(prefix="/api/users", tags=["Users"])


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
    
    db = await get_db()
    user_id = str(uuid.uuid4())[:8]
    
    try:
        result = await db.create_user(user_id, user.name, user.role)
        return UserResponse(
            id=result["id"],
            name=result["name"],
            role=result["role"],
            created_at=result["created_at"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Get user information by ID."""
    db = await get_db()
    user = await db.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.get("/")
async def list_users(role: Optional[str] = None):
    """List all users, optionally filtered by role."""
    db = await get_db()
    users = await db.list_users(role)
    return {"users": users}


# =============================================================================
# PATIENT-CARETAKER LINKING
# =============================================================================

@router.post("/patients/{patient_id}/link-caretaker")
async def link_caretaker_to_patient(patient_id: str, link: LinkCaretaker):
    """
    Link a caretaker to a patient.
    Both patient and caretaker must exist.
    """
    db = await get_db()
    
    # Verify patient exists
    patient = await db.get_user(patient_id)
    if not patient or patient.get("role") != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify caretaker exists
    caretaker = await db.get_user(link.caretaker_id)
    if not caretaker or caretaker.get("role") != "caretaker":
        raise HTTPException(status_code=404, detail="Caretaker not found")
    
    # Create link
    success = await db.link_patient_caretaker(patient_id, link.caretaker_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to link")
    
    # Refresh user data
    patient = await db.get_user(patient_id)
    caretaker = await db.get_user(link.caretaker_id)
    
    return {
        "status": "ok",
        "message": f"Linked caretaker {caretaker['name']} to patient {patient['name']}",
        "patient": patient,
        "caretaker": caretaker
    }


@router.delete("/patients/{patient_id}/unlink-caretaker/{caretaker_id}")
async def unlink_caretaker_from_patient(patient_id: str, caretaker_id: str):
    """Remove a caretaker from a patient."""
    db = await get_db()
    
    # Verify both exist
    patient = await db.get_user(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    caretaker = await db.get_user(caretaker_id)
    if not caretaker:
        raise HTTPException(status_code=404, detail="Caretaker not found")
    
    success = await db.unlink_patient_caretaker(patient_id, caretaker_id)
    
    return {"status": "ok", "message": "Unlinked successfully"}


@router.get("/patients/{patient_id}/caretakers")
async def get_patient_caretakers(patient_id: str):
    """Get all caretakers for a patient."""
    db = await get_db()
    
    patient = await db.get_user(patient_id)
    if not patient or patient.get("role") != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")
    
    caretakers = await db.get_patient_caretakers(patient_id)
    
    return {"patient": patient, "caretakers": caretakers}


@router.get("/caretakers/{caretaker_id}/patients")
async def get_caretaker_patients(caretaker_id: str):
    """Get all patients for a caretaker."""
    db = await get_db()
    
    caretaker = await db.get_user(caretaker_id)
    if not caretaker or caretaker.get("role") != "caretaker":
        raise HTTPException(status_code=404, detail="Caretaker not found")
    
    patients = await db.get_caretaker_patients(caretaker_id)
    
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
    db = await get_db()
    
    patient = await db.get_user(notification.patient_id)
    if not patient or patient.get("role") != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")
    
    notif_id = str(uuid.uuid4())[:8]
    caretaker_ids = patient.get("caretakers", [])
    
    notif_data = await db.create_notification(
        notif_id=notif_id,
        patient_id=notification.patient_id,
        intent=notification.intent,
        message=notification.message,
        confidence=notification.confidence,
        transcription=notification.transcription,
        caretaker_ids=caretaker_ids
    )
    
    return {
        "status": "ok",
        "notification_id": notif_id,
        "sent_to_caretakers": len(caretaker_ids),
        "notification": notif_data
    }


@router.get("/caretakers/{caretaker_id}/notifications")
async def get_caretaker_notifications(
    caretaker_id: str, 
    unread_only: bool = False,
    limit: int = 50
):
    """Get all notifications for a caretaker from their patients."""
    db = await get_db()
    
    caretaker = await db.get_user(caretaker_id)
    if not caretaker or caretaker.get("role") != "caretaker":
        raise HTTPException(status_code=404, detail="Caretaker not found")
    
    notifications, total, unread = await db.get_caretaker_notifications(
        caretaker_id, unread_only, limit
    )
    
    return {
        "notifications": notifications,
        "total": total,
        "unread": unread
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, caretaker_id: str):
    """Mark a notification as read by a caretaker."""
    db = await get_db()
    
    success = await db.mark_notification_read(notification_id, caretaker_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"status": "ok", "message": "Marked as read"}


@router.get("/patients/{patient_id}/notifications")
async def get_patient_notifications(patient_id: str, limit: int = 20):
    """Get notification history for a patient (their own requests)."""
    db = await get_db()
    
    patient = await db.get_user(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    notifications = await db.get_patient_notifications(patient_id, limit)
    
    return {
        "notifications": notifications,
        "total": len(notifications)
    }
