from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models.schemas import (
    Batch, BatchStatus, User, UserRole,
    DestructionRecord, Handoff,
    DestructionScheduleRequest, DestructionRecordCreate,
    DestructionRecordResponse, HandoffRequest, HandoffResponse,
)
from app.services.workflow_service import transition_state

router = APIRouter(prefix="/destruction", tags=["Destruction"])


@router.post("/handoff", response_model=HandoffResponse)
def manufacturer_handoff(
    req: HandoffRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manufacturer confirms handoff to the next stage.
    If batch is RECEIVED_BY_DISTRIBUTOR or DISPUTED→resolved, transitions
    to RECEIVED_BY_MANUFACTURER.
    """
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    current_status = batch.current_status
    if hasattr(current_status, "value"):
        current_status = current_status.value

    # If not already at RECEIVED_BY_MANUFACTURER, transition
    if current_status != BatchStatus.RECEIVED_BY_MANUFACTURER.value:
        try:
            transition_state(
                db=db,
                batch=batch,
                target_status=BatchStatus.RECEIVED_BY_MANUFACTURER.value,
                actor_id=current_user.id,
                event_type="MANUFACTURER_RECEIVED",
                event_data={
                    "from_role": req.from_role.value,
                    "to_role": req.to_role.value,
                    "received_quantity": req.received_quantity,
                },
                background_tasks=background_tasks,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    handoff = Handoff(
        batch_id=req.batch_id,
        from_role=req.from_role,
        to_role=req.to_role,
        received_quantity=req.received_quantity,
        discrepancy_flag=False,
    )
    db.add(handoff)
    batch.current_location = "Manufacturer Facility"
    db.commit()
    db.refresh(handoff)

    return HandoffResponse.model_validate(handoff)


@router.post("/schedule")
def schedule_destruction(
    req: DestructionScheduleRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manufacturer schedules destruction.
    Transitions batch to DESTRUCTION_SCHEDULED.
    """
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    facility = db.query(User).filter(User.id == req.facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    try:
        transition_state(
            db=db,
            batch=batch,
            target_status=BatchStatus.DESTRUCTION_SCHEDULED.value,
            actor_id=current_user.id,
            event_type="DESTRUCTION_SCHEDULED",
            event_data={
                "facility_id": req.facility_id,
                "facility_name": facility.organization_name,
            },
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    batch.current_location = f"Scheduled — {facility.organization_name}"
    db.commit()

    return {
        "status": "scheduled",
        "message": f"Destruction scheduled at {facility.organization_name}",
        "batch_status": BatchStatus.DESTRUCTION_SCHEDULED.value,
    }


@router.post("/record", response_model=DestructionRecordResponse)
def record_destruction(
    req: DestructionRecordCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Facility records destruction of a batch.
    Transitions batch to DESTROYED.
    """
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    try:
        transition_state(
            db=db,
            batch=batch,
            target_status=BatchStatus.DESTROYED.value,
            actor_id=current_user.id,
            event_type="DESTRUCTION_RECORDED",
            event_data={
                "quantity_destroyed": req.quantity_destroyed,
                "facility_id": current_user.id,
            },
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    record = DestructionRecord(
        batch_id=req.batch_id,
        facility_id=current_user.id,
        quantity_destroyed=req.quantity_destroyed,
    )
    db.add(record)

    batch.destruction_status = "DESTROYED"
    batch.current_location = f"{current_user.organization_name} — Destroyed"
    db.commit()
    db.refresh(record)

    return DestructionRecordResponse.model_validate(record)
