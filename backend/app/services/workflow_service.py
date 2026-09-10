import datetime
import json
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.schemas import (
    Batch, BatchStatus, WorkflowEvent, Dispute, DisputeStatus,
    Handoff, UserRole, Alert, AlertSeverity,
)
from app.services.audit_service import create_audit_entry


# ──────────────────────────────────────────────
#  Valid state transitions
# ──────────────────────────────────────────────

VALID_TRANSITIONS = {
    BatchStatus.ACTIVE.value: [BatchStatus.EXPIRED.value, BatchStatus.RETURN_REQUESTED.value],
    BatchStatus.EXPIRED.value: [BatchStatus.RETURN_REQUESTED.value],
    BatchStatus.RETURN_REQUESTED.value: [BatchStatus.PICKUP_CONFIRMED.value],
    BatchStatus.PICKUP_CONFIRMED.value: [BatchStatus.RECEIVED_BY_DISTRIBUTOR.value],
    BatchStatus.RECEIVED_BY_DISTRIBUTOR.value: [
        BatchStatus.DISPUTED.value,
        BatchStatus.RECEIVED_BY_MANUFACTURER.value,
    ],
    BatchStatus.DISPUTED.value: [BatchStatus.RECEIVED_BY_MANUFACTURER.value],
    BatchStatus.RECEIVED_BY_MANUFACTURER.value: [BatchStatus.DESTRUCTION_SCHEDULED.value],
    BatchStatus.DESTRUCTION_SCHEDULED.value: [BatchStatus.DESTROYED.value],
    BatchStatus.DESTROYED.value: [BatchStatus.CERTIFICATE_VERIFIED.value],
    BatchStatus.CERTIFICATE_VERIFIED.value: [BatchStatus.CLOSED.value],
}


def _get_status_value(status) -> str:
    """Extract string value from either an enum or a string."""
    return status.value if hasattr(status, "value") else str(status)


def validate_transition(current_status: str, target_status: str) -> bool:
    """Check if a transition from current_status to target_status is valid."""
    current = _get_status_value(current_status) if hasattr(current_status, "value") else current_status
    target = _get_status_value(target_status) if hasattr(target_status, "value") else target_status
    allowed = VALID_TRANSITIONS.get(current, [])
    return target in allowed


def transition_state(
    db: Session,
    batch: Batch,
    target_status: str,
    actor_id: int,
    event_type: str,
    event_data: Optional[dict] = None,
    background_tasks: Optional[BackgroundTasks] = None,
) -> WorkflowEvent:
    """
    Execute a state transition on a batch.
    - Validates the transition
    - Updates batch status
    - Creates a WorkflowEvent
    - Creates an AuditLog entry
    - Optionally triggers the Moderator AI
    """
    current = _get_status_value(batch.current_status)
    target = _get_status_value(target_status) if hasattr(target_status, "value") else target_status

    if not validate_transition(current, target):
        raise ValueError(
            f"Invalid state transition: {current} → {target}. "
            f"Allowed transitions from {current}: {VALID_TRANSITIONS.get(current, [])}"
        )

    from_status = current
    batch.current_status = target

    # Create workflow event
    workflow_event = WorkflowEvent(
        batch_id=batch.id,
        actor_id=actor_id,
        event_type=event_type,
        from_status=from_status,
        to_status=target,
        data=json.dumps(event_data or {}, default=str),
        created_at=datetime.datetime.utcnow(),
    )
    db.add(workflow_event)

    # Create audit log entry
    create_audit_entry(
        db=db,
        batch_id=batch.id,
        actor_id=actor_id,
        action=event_type,
        event_data={
            "from_status": from_status,
            "to_status": target,
            **(event_data or {}),
        },
    )

    db.flush()

    # Trigger Moderator AI if background_tasks is provided
    if background_tasks:
        try:
            from app.moderator.agent import run_moderator_analysis
            background_tasks.add_task(
                run_moderator_analysis,
                workflow_event_id=workflow_event.id,
                batch_id=batch.id,
                event_type=event_type,
                actor_id=actor_id,
            )
        except ImportError:
            pass

    return workflow_event


def handle_discrepancy(
    db: Session,
    batch: Batch,
    declared_qty: int,
    received_qty: int,
    actor_id: int,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Dispute:
    """
    Handle quantity discrepancy:
    - Transition to DISPUTED
    - Create Dispute record
    - Create Handoff record with discrepancy flag
    """
    # Transition to DISPUTED
    transition_state(
        db=db,
        batch=batch,
        target_status=BatchStatus.DISPUTED.value,
        actor_id=actor_id,
        event_type="DISCREPANCY_DETECTED",
        event_data={
            "declared_qty": declared_qty,
            "received_qty": received_qty,
            "discrepancy": declared_qty - received_qty,
        },
        background_tasks=background_tasks,
    )

    # Create dispute record
    dispute = Dispute(
        batch_id=batch.id,
        declared_qty=declared_qty,
        received_qty=received_qty,
        status=DisputeStatus.OPEN,
    )
    db.add(dispute)

    # Create handoff record with discrepancy flag
    handoff = Handoff(
        batch_id=batch.id,
        from_role=UserRole.PHARMACY,
        to_role=UserRole.DISTRIBUTOR,
        received_quantity=received_qty,
        discrepancy_flag=True,
    )
    db.add(handoff)

    # Create alert
    alert = Alert(
        batch_id=batch.id,
        severity=AlertSeverity.HIGH,
        title="Quantity Discrepancy Detected",
        description=f"Declared: {declared_qty}, Received: {received_qty}. "
                    f"Discrepancy of {declared_qty - received_qty} units.",
    )
    db.add(alert)

    return dispute
