from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.schemas import (
    Batch, BatchStatus, User, UserRole, Dispute, DisputeStatus,
    DisputeResponse, DisputeResolveRequest,
)
from app.services.workflow_service import transition_state
from app.services.notification_service import notify_by_role

router = APIRouter(prefix="/disputes", tags=["Disputes"])


@router.get("/", response_model=list[DisputeResponse])
def list_disputes(db: Session = Depends(get_db)):
    """List all disputes."""
    disputes = db.query(Dispute).all()
    return [DisputeResponse.model_validate(d) for d in disputes]


@router.get("/{dispute_id}", response_model=DisputeResponse)
def get_dispute(dispute_id: int, db: Session = Depends(get_db)):
    """Get a single dispute by ID."""
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return DisputeResponse.model_validate(dispute)


@router.post("/{dispute_id}/resolve")
def resolve_dispute(
    dispute_id: int,
    req: DisputeResolveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DISTRIBUTOR, UserRole.MANUFACTURER, UserRole.REGULATOR)),
):
    """
    Resolve a dispute. Resumes the workflow by transitioning
    the batch from DISPUTED → RECEIVED_BY_MANUFACTURER.
    """
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    if dispute.status == DisputeStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Dispute already resolved")

    batch = db.query(Batch).filter(Batch.id == dispute.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    current_status = batch.current_status
    if hasattr(current_status, "value"):
        current_status = current_status.value

    if current_status != BatchStatus.DISPUTED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Batch is in state {current_status}, not DISPUTED."
        )

    # Resolve the dispute
    dispute.status = DisputeStatus.RESOLVED
    dispute.resolution_notes = req.resolution_notes

    # Resume workflow: DISPUTED → RECEIVED_BY_MANUFACTURER
    try:
        transition_state(
            db=db,
            batch=batch,
            target_status=BatchStatus.RECEIVED_BY_MANUFACTURER.value,
            actor_id=current_user.id,
            event_type="DISPUTE_RESOLVED",
            event_data={
                "dispute_id": dispute.id,
                "resolution_notes": req.resolution_notes,
                "declared_qty": dispute.declared_qty,
                "received_qty": dispute.received_qty,
            },
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    batch.current_location = "Manufacturer Warehouse"

    notify_by_role(
        db=db,
        roles=["PHARMACY", "DISTRIBUTOR", "MANUFACTURER"],
        title="Dispute Resolved",
        message=f"Dispute #{dispute.id} for Batch #{batch.batch_number} has been resolved. Forwarded to manufacturer.",
    )

    db.commit()

    return {
        "status": "resolved",
        "message": "Dispute resolved. Batch forwarded to manufacturer.",
        "batch_status": BatchStatus.RECEIVED_BY_MANUFACTURER.value,
    }
