from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_roles, require_role
from app.models.schemas import (
    Batch, User, Medicine, WorkflowEvent, ModeratorEvent,
    BatchResponse, BatchScanRequest, BatchScanResponse,
    WorkflowEventResponse, ModeratorEventResponse,
)
from app.services.fraud_service import check_reentry_fraud

router = APIRouter(prefix="/batches", tags=["Batches"])


def _batch_to_response(batch: Batch) -> BatchResponse:
    """Convert a Batch ORM object to a BatchResponse, including medicine name."""
    return BatchResponse(
        id=batch.id,
        batch_number=batch.batch_number,
        medicine_name=batch.medicine.name if batch.medicine else None,
        quantity=batch.quantity,
        expiry_date=batch.expiry_date,
        current_status=batch.current_status.value if hasattr(batch.current_status, 'value') else batch.current_status,
        current_location=batch.current_location,
        reverse_chain_flag=batch.reverse_chain_flag,
        destruction_status=batch.destruction_status,
    )


@router.get("", response_model=list[BatchResponse])
@router.get("/", response_model=list[BatchResponse])
def list_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all batches. Requires any authenticated user."""
    batches = db.query(Batch).all()
    return [_batch_to_response(b) for b in batches]


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single batch by ID. Requires any authenticated user."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return _batch_to_response(batch)


@router.post("/scan", response_model=BatchScanResponse)
def scan_batch(
    req: BatchScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("PHARMACY", "REGULATOR")),
):
    """
    Scan a batch by batch_number.
    - Queries database for the batch
    - Checks for re-entry fraud
    - Returns batch info and fraud status
    """
    batch = db.query(Batch).filter(Batch.batch_number == req.batch_number).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {req.batch_number} not found")

    # Run fraud check
    fraud_result = check_reentry_fraud(
        db=db,
        batch=batch,
        actor_id=current_user.id,
        location=req.location or current_user.organization_name,
        background_tasks=background_tasks,
    )

    db.commit()

    return BatchScanResponse(
        batch=_batch_to_response(batch),
        fraud_detected=fraud_result["fraud_detected"],
        alert=fraud_result["alert"],
        message=fraud_result["message"],
    )


@router.get("/{batch_id}/timeline", response_model=list[WorkflowEventResponse])
def get_batch_timeline(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full workflow event timeline for a batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    events = (
        db.query(WorkflowEvent)
        .filter(WorkflowEvent.batch_id == batch_id)
        .order_by(WorkflowEvent.created_at.asc())
        .all()
    )

    result = []
    for e in events:
        actor = db.query(User).filter(User.id == e.actor_id).first()
        resp = WorkflowEventResponse(
            id=e.id,
            batch_id=e.batch_id,
            actor_id=e.actor_id,
            event_type=e.event_type,
            from_status=e.from_status,
            to_status=e.to_status,
            data=e.data,
            created_at=e.created_at,
            actor_name=actor.organization_name if actor else None,
            actor_role=actor.role.value if actor else None,
        )
        result.append(resp)

    return result


@router.get("/{batch_id}/moderator-events", response_model=list[ModeratorEventResponse])
def get_moderator_events(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("REGULATOR", "MANUFACTURER")),
):
    """Get AI moderator analysis events for a batch. REGULATOR and MANUFACTURER only."""
    events = (
        db.query(ModeratorEvent)
        .filter(ModeratorEvent.batch_id == batch_id)
        .all()
    )
    return [ModeratorEventResponse.model_validate(e) for e in events]
