from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.schemas import (
    Batch, BatchStatus, User, UserRole, ReturnRequest,
    Handoff, ReturnRequestCreate, ReturnRequestResponse,
    PickupConfirmRequest, ReceiveRequest, BatchResponse,
    HandoffResponse,
)
from app.services.workflow_service import transition_state, handle_discrepancy
from app.services.notification_service import notify_by_role

router = APIRouter(prefix="/returns", tags=["Returns"])


@router.post("/", response_model=ReturnRequestResponse)
def create_return_request(
    req: ReturnRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PHARMACY)),
):
    """Create a return request. Transitions batch to RETURN_REQUESTED."""
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    try:
        transition_state(
            db=db,
            batch=batch,
            target_status=BatchStatus.RETURN_REQUESTED.value,
            actor_id=current_user.id,
            event_type="RETURN_REQUESTED",
            event_data={
                "declared_quantity": req.declared_quantity,
                "distributor_id": req.distributor_id,
            },
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    batch.reverse_chain_flag = True

    return_request = ReturnRequest(
        batch_id=req.batch_id,
        declared_quantity=req.declared_quantity,
        distributor_id=req.distributor_id,
        status="PENDING",
    )
    db.add(return_request)

    notify_by_role(
        db=db,
        roles=["DISTRIBUTOR"],
        title="New Return Request",
        message=f"Return request initiated for Batch #{batch.batch_number} (Declared Qty: {req.declared_quantity}).",
    )

    db.commit()
    db.refresh(return_request)

    return ReturnRequestResponse.model_validate(return_request)


@router.get("/", response_model=list[ReturnRequestResponse])
def list_returns(db: Session = Depends(get_db)):
    """List all return requests."""
    returns = db.query(ReturnRequest).all()
    return [ReturnRequestResponse.model_validate(r) for r in returns]


@router.post("/{return_id}/pickup")
def confirm_pickup(
    return_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DISTRIBUTOR)),
):
    """Distributor confirms pickup. Transitions batch to PICKUP_CONFIRMED."""
    ret = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")

    batch = db.query(Batch).filter(Batch.id == ret.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    try:
        transition_state(
            db=db,
            batch=batch,
            target_status=BatchStatus.PICKUP_CONFIRMED.value,
            actor_id=current_user.id,
            event_type="PICKUP_CONFIRMED",
            event_data={"return_request_id": return_id},
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ret.status = "PICKED_UP"
    batch.current_location = "In Transit — Distributor"

    notify_by_role(
        db=db,
        roles=["PHARMACY", "MANUFACTURER"],
        title="Pickup Confirmed",
        message=f"Distributor has confirmed pickup for Batch #{batch.batch_number}.",
    )

    db.commit()

    return {"status": "ok", "message": "Pickup confirmed", "batch_status": BatchStatus.PICKUP_CONFIRMED.value}


@router.post("/{return_id}/receive")
def receive_return(
    return_id: int,
    req: ReceiveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DISTRIBUTOR)),
):
    """
    Distributor receives the return.
    - If received_quantity != declared_quantity → DISPUTED + creates Dispute record.
    - If quantities match → RECEIVED_BY_DISTRIBUTOR.
    """
    ret = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")

    batch = db.query(Batch).filter(Batch.id == ret.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    declared_qty = ret.declared_quantity
    received_qty = req.received_quantity

    if received_qty != declared_qty:
        # Discrepancy detected
        try:
            # First transition to RECEIVED_BY_DISTRIBUTOR, then to DISPUTED
            transition_state(
                db=db,
                batch=batch,
                target_status=BatchStatus.RECEIVED_BY_DISTRIBUTOR.value,
                actor_id=current_user.id,
                event_type="RECEIVED_BY_DISTRIBUTOR",
                event_data={
                    "declared_qty": declared_qty,
                    "received_qty": received_qty,
                },
                background_tasks=background_tasks,
            )
            dispute = handle_discrepancy(
                db=db,
                batch=batch,
                declared_qty=declared_qty,
                received_qty=received_qty,
                actor_id=current_user.id,
                background_tasks=background_tasks,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        ret.status = "DISPUTED"
        batch.current_location = "Distributor Warehouse — Under Dispute"

        notify_by_role(
            db=db,
            roles=["PHARMACY", "MANUFACTURER", "REGULATOR"],
            title="Discrepancy Detected (Disputed)",
            message=f"Discrepancy for Batch #{batch.batch_number}: declared {declared_qty}, received {received_qty}. Batch marked DISPUTED.",
        )

        db.commit()

        return {
            "status": "disputed",
            "message": f"Discrepancy detected: declared {declared_qty}, received {received_qty}",
            "dispute_id": dispute.id,
            "batch_status": BatchStatus.DISPUTED.value,
        }
    else:
        # Quantities match
        try:
            transition_state(
                db=db,
                batch=batch,
                target_status=BatchStatus.RECEIVED_BY_DISTRIBUTOR.value,
                actor_id=current_user.id,
                event_type="RECEIVED_BY_DISTRIBUTOR",
                event_data={
                    "declared_qty": declared_qty,
                    "received_qty": received_qty,
                },
                background_tasks=background_tasks,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Record handoff without discrepancy
        handoff = Handoff(
            batch_id=batch.id,
            from_role=UserRole.PHARMACY,
            to_role=UserRole.DISTRIBUTOR,
            received_quantity=received_qty,
            discrepancy_flag=False,
        )
        db.add(handoff)

        ret.status = "RECEIVED"
        batch.current_location = "Distributor Warehouse"

        notify_by_role(
            db=db,
            roles=["MANUFACTURER"],
            title="Return Received by Distributor",
            message=f"Batch #{batch.batch_number} received at distributor warehouse with matching quantities.",
        )

        db.commit()

        return {
            "status": "received",
            "message": f"Quantities match ({received_qty}). Received successfully.",
            "batch_status": BatchStatus.RECEIVED_BY_DISTRIBUTOR.value,
        }
