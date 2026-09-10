from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_roles, require_role
from app.models.schemas import (
    Batch, BatchStatus, User, Dispute, DisputeStatus,
    DisputeResponse, DisputeResolveRequest,
)
from app.services.workflow_service import transition_state

router = APIRouter(prefix="/disputes", tags=["Disputes"])


class DisputeCreateRequest(BaseModel):
    batch_id: int
    declared_qty: int
    received_qty: int
    reason: Optional[str] = None


@router.post("", response_model=DisputeResponse)
@router.post("/", response_model=DisputeResponse)
def create_dispute(
    req: DisputeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("DISTRIBUTOR", "MANUFACTURER")),
):
    """Create a dispute. DISTRIBUTOR or MANUFACTURER only."""
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    dispute = Dispute(
        batch_id=req.batch_id,
        declared_qty=req.declared_qty,
        received_qty=req.received_qty,
        status=DisputeStatus.OPEN,
        resolution_notes=req.reason,
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return DisputeResponse.model_validate(dispute)


@router.get("", response_model=list[DisputeResponse])
@router.get("/", response_model=list[DisputeResponse])
def list_disputes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("DISTRIBUTOR", "MANUFACTURER", "REGULATOR")),
):
    """List all disputes. DISTRIBUTOR, MANUFACTURER, REGULATOR only."""
    disputes = db.query(Dispute).all()
    return [DisputeResponse.model_validate(d) for d in disputes]


@router.get("/{dispute_id}", response_model=DisputeResponse)
def get_dispute(
    dispute_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("DISTRIBUTOR", "MANUFACTURER", "REGULATOR")),
):
    """Get a single dispute. DISTRIBUTOR, MANUFACTURER, REGULATOR only."""
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
    current_user: User = Depends(require_roles("DISTRIBUTOR", "REGULATOR", "MANUFACTURER")),
):
    """
    Resolve a dispute. DISTRIBUTOR, REGULATOR (and MANUFACTURER). Resumes the workflow by transitioning
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
    db.commit()

    return {
        "status": "resolved",
        "message": "Dispute resolved. Batch forwarded to manufacturer.",
        "batch_status": BatchStatus.RECEIVED_BY_MANUFACTURER.value,
    }
