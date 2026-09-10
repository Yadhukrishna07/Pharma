from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.schemas import (
    Batch, BatchStatus, User, UserRole,
    DestructionRecord, Handoff,
    DestructionScheduleRequest, DestructionRecordCreate,
    DestructionRecordResponse, HandoffRequest, HandoffResponse,
)
from app.services.workflow_service import transition_state
from app.services.notification_service import notify_by_role

router = APIRouter(prefix="/destruction", tags=["Destruction"])


@router.post("/handoff", response_model=HandoffResponse)
def manufacturer_handoff(
    req: HandoffRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MANUFACTURER)),
):
    """
    Manufacturer confirms handoff to the next stage.
    If batch is DISPUTED, rejects with 400 (dispute must be resolved via /disputes/{id}/resolve first).
    If batch is RECEIVED_BY_DISTRIBUTOR, transitions to RECEIVED_BY_MANUFACTURER.
    """
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    current_status = batch.current_status
    if hasattr(current_status, "value"):
        current_status = current_status.value

    if current_status == BatchStatus.DISPUTED.value:
        raise HTTPException(
            status_code=400,
            detail="Batch is in DISPUTED state. Dispute must be resolved before manufacturer handoff.",
        )

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
                    "from_role": req.from_role.value if hasattr(req.from_role, "value") else str(req.from_role),
                    "to_role": req.to_role.value if hasattr(req.to_role, "value") else str(req.to_role),
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

    notify_by_role(
        db=db,
        roles=["DISTRIBUTOR", "REGULATOR"],
        title="Manufacturer Receipt Confirmed",
        message=f"Manufacturer has confirmed receipt of Batch #{batch.batch_number}.",
    )

    db.commit()
    db.refresh(handoff)

    return HandoffResponse.model_validate(handoff)


@router.post("/schedule")
def schedule_destruction(
    req: DestructionScheduleRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.MANUFACTURER)),
):
    """
    Manufacturer schedules destruction.
    Transitions batch to DESTRUCTION_SCHEDULED.
    Prerequisite: Batch must be in RECEIVED_BY_MANUFACTURER state.
    """
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    current_status = batch.current_status
    if hasattr(current_status, "value"):
        current_status = current_status.value

    if current_status != BatchStatus.RECEIVED_BY_MANUFACTURER.value:
        raise HTTPException(
            status_code=400,
            detail=f"Batch must be in RECEIVED_BY_MANUFACTURER state to schedule destruction. Current state: {current_status}",
        )

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

    notify_by_role(
        db=db,
        roles=["FACILITY"],
        title="Destruction Scheduled",
        message=f"Destruction for Batch #{batch.batch_number} scheduled at {facility.organization_name}.",
    )

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
    current_user: User = Depends(require_role(UserRole.FACILITY)),
):
    """
    Facility records destruction of a batch.
    Transitions batch to DESTROYED.
    Prerequisite: Batch must be in DESTRUCTION_SCHEDULED state.
    """
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    current_status = batch.current_status
    if hasattr(current_status, "value"):
        current_status = current_status.value

    if current_status != BatchStatus.DESTRUCTION_SCHEDULED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Batch must be in DESTRUCTION_SCHEDULED state to record destruction. Current state: {current_status}",
        )

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

    notify_by_role(
        db=db,
        roles=["MANUFACTURER", "REGULATOR"],
        title="Destruction Recorded",
        message=f"Facility recorded destruction of {req.quantity_destroyed} units for Batch #{batch.batch_number}.",
    )

    db.commit()
    db.refresh(record)

    return DestructionRecordResponse.model_validate(record)
