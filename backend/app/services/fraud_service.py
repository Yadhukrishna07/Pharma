import datetime
import json
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.schemas import (
    Batch, BatchStatus, WorkflowEvent, Alert, AlertSeverity,
)
from app.services.audit_service import create_audit_entry


def check_reentry_fraud(
    db: Session,
    batch: Batch,
    actor_id: int,
    location: Optional[str] = None,
    background_tasks: Optional[BackgroundTasks] = None,
) -> dict:
    """
    On POST /batches/scan, check if a batch that was DESTROYED or CLOSED
    is being scanned again (re-entry fraud).

    Returns:
        dict with keys: fraud_detected (bool), alert (str or None), message (str)
    """
    current_status = batch.current_status
    if hasattr(current_status, "value"):
        current_status = current_status.value

    destruction_status = batch.destruction_status

    is_fraud = False
    alert_msg = None

    # Check for re-entry: batch was destroyed/closed and scanned at a new location
    if current_status in (BatchStatus.DESTROYED.value, BatchStatus.CLOSED.value,
                          BatchStatus.CERTIFICATE_VERIFIED.value):
        is_fraud = True
        alert_msg = (
            f"CRITICAL: Re-entry fraud detected for batch {batch.batch_number}. "
            f"Batch status is {current_status} but was scanned "
            f"at location: {location or 'unknown'}."
        )
    elif destruction_status == "DESTROYED":
        is_fraud = True
        alert_msg = (
            f"CRITICAL: Batch {batch.batch_number} has destruction_status=DESTROYED "
            f"but was scanned at location: {location or 'unknown'}. "
            "Possible counterfeit or re-entry."
        )

    if is_fraud:
        # Do NOT change state back to ACTIVE — leave as-is

        # Create CRITICAL alert
        alert = Alert(
            batch_id=batch.id,
            severity=AlertSeverity.CRITICAL,
            title="REENTRY_FRAUD_EVENT",
            description=alert_msg,
        )
        db.add(alert)

        # Log SCAN workflow event
        workflow_event = WorkflowEvent(
            batch_id=batch.id,
            actor_id=actor_id,
            event_type="REENTRY_FRAUD_SCAN",
            from_status=current_status,
            to_status=current_status,  # No state change!
            data=json.dumps({
                "scan_location": location,
                "fraud_type": "REENTRY_FRAUD_EVENT",
                "batch_destruction_status": destruction_status,
                "batch_current_status": current_status,
            }, default=str),
            created_at=datetime.datetime.utcnow(),
        )
        db.add(workflow_event)

        # Create audit entry
        create_audit_entry(
            db=db,
            batch_id=batch.id,
            actor_id=actor_id,
            action="REENTRY_FRAUD_SCAN",
            event_data={
                "scan_location": location,
                "fraud_type": "REENTRY_FRAUD_EVENT",
                "current_status": current_status,
            },
        )

        db.flush()

        # Trigger Moderator AI
        if background_tasks:
            try:
                from app.moderator.agent import run_moderator_analysis
                background_tasks.add_task(
                    run_moderator_analysis,
                    workflow_event_id=workflow_event.id,
                    batch_id=batch.id,
                    event_type="REENTRY_FRAUD_SCAN",
                    actor_id=actor_id,
                )
            except ImportError:
                pass

        return {
            "fraud_detected": True,
            "alert": alert_msg,
            "message": "Re-entry fraud detected. Authorities have been notified.",
        }

    # Normal scan — log event but no fraud
    workflow_event = WorkflowEvent(
        batch_id=batch.id,
        actor_id=actor_id,
        event_type="SCAN",
        from_status=current_status,
        to_status=current_status,
        data=json.dumps({"scan_location": location}, default=str),
        created_at=datetime.datetime.utcnow(),
    )
    db.add(workflow_event)

    create_audit_entry(
        db=db,
        batch_id=batch.id,
        actor_id=actor_id,
        action="SCAN",
        event_data={"scan_location": location, "status": current_status},
    )

    return {
        "fraud_detected": False,
        "alert": None,
        "message": f"Batch {batch.batch_number} scanned successfully. Status: {current_status}.",
    }
