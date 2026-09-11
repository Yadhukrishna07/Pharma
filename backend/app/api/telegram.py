import html
import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models.schemas import User, Batch, BatchStatus, Medicine, compute_expiry_status
from app.services.telegram_service import (
    send_telegram_message,
    notify_medicine_approaching_expiry,
)

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/test")
def test_telegram_endpoint(
    current_user: User = Depends(get_current_user),
):
    """
    Protected test endpoint to verify Telegram Bot notifications.
    Requires any authenticated user.
    Sends a test message and returns success status without exposing credentials.
    """
    role_str = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    test_msg = (
        f"🧪 <b>PHARMAMED TELEGRAM BOT TEST</b>\n\n"
        f"✅ <b>Status:</b> Telegram service connection verified.\n"
        f"👤 <b>Triggered By:</b> {html.escape(current_user.organization_name)} ({html.escape(role_str)})\n"
        f"⏰ <b>Timestamp:</b> {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    success = send_telegram_message(test_msg)
    if success:
        return {
            "status": "success",
            "message": "Test Telegram message sent successfully.",
        }
    else:
        return {
            "status": "error",
            "message": "Failed to dispatch Telegram message. Check backend logs for details.",
        }


@router.post("/check-expiry")
def check_expiry_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Protected manual check endpoint to scan existing batches approaching expiry
    and send Telegram notifications (Event 1).
    Requires any authenticated user.
    """
    today = datetime.date.today()
    threshold = today + datetime.timedelta(days=90)

    batches = db.query(Batch).all()
    notified = []

    for b in batches:
        # Check if approaching expiry (within 90 days) or already expired
        status_val = b.current_status.value if hasattr(b.current_status, "value") else str(b.current_status)
        
        # We check batches that are either expiring within 90 days or marked EXPIRED
        is_approaching = b.expiry_date <= threshold
        
        if is_approaching:
            days_left = (b.expiry_date - today).days
            med_name = b.medicine.name if b.medicine else "Unknown Medicine"
            loc_name = b.current_location or current_user.organization_name

            sent = notify_medicine_approaching_expiry(
                medicine_name=med_name,
                batch_number=b.batch_number,
                quantity=b.quantity,
                expiry_date=str(b.expiry_date),
                days_remaining=days_left,
                current_status=status_val,
                organization_name=loc_name,
            )

            notified.append({
                "batch_id": b.id,
                "batch_number": b.batch_number,
                "medicine_name": med_name,
                "expiry_date": str(b.expiry_date),
                "days_remaining": days_left,
                "notification_sent": sent,
            })

    return {
        "status": "completed",
        "batches_scanned": len(batches),
        "notifications_triggered": len(notified),
        "details": notified,
    }
