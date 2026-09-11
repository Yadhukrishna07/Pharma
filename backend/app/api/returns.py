import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_roles, require_role
from app.models.schemas import (
    Batch, BatchStatus, User, UserRole, ReturnRequest,
    Handoff, ReturnRequestCreate, ReturnRequestResponse,
    PickupConfirmRequest, ReceiveRequest, BatchResponse,
    HandoffResponse,
)
from app.services.workflow_service import transition_state, handle_discrepancy
from app.services.telegram_service import (
    notify_return_created,
    notify_return_approved,
    notify_return_rejected,
    notify_pickup_completed,
    notify_return_received,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/returns", tags=["Returns"])



@router.post("/", response_model=ReturnRequestResponse)
def create_return_request(
    req: ReturnRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("PHARMACY")),
):
    """
    Create a return request. PHARMACY only.
    - Validates batch exists and is in EXPIRED or ACTIVE status
    - Validates declared quantity is positive and within batch total
    - Validates distributor exists and has DISTRIBUTOR role
    - Checks for existing active return requests on this batch
    - Transitions batch to RETURN_REQUESTED
    - Persists the ReturnRequest record
    """
    # 1. Validate batch existence
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # 2. Validate batch status (must be EXPIRED or ACTIVE to initiate return)
    current_status = batch.current_status.value if hasattr(batch.current_status, "value") else str(batch.current_status)
    if current_status not in [BatchStatus.EXPIRED.value, BatchStatus.ACTIVE.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot initiate return for batch with status '{current_status}'. Batch must be in EXPIRED or ACTIVE status.",
        )

    # 3. Validate declared quantity
    if req.declared_quantity <= 0:
        raise HTTPException(status_code=400, detail="Declared quantity must be greater than 0")
    if req.declared_quantity > batch.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Declared quantity ({req.declared_quantity}) exceeds total batch quantity ({batch.quantity})",
        )

    # 4. Validate distributor existence and role
    distributor = db.query(User).filter(User.id == req.distributor_id).first()
    if not distributor:
        raise HTTPException(status_code=400, detail=f"Distributor with ID {req.distributor_id} not found")
    dist_role = distributor.role.value if hasattr(distributor.role, "value") else str(distributor.role)
    if dist_role != UserRole.DISTRIBUTOR.value:
        raise HTTPException(
            status_code=400,
            detail=f"User with ID {req.distributor_id} ({distributor.organization_name}) is not a DISTRIBUTOR (role: {dist_role})",
        )

    # 5. Validate mandatory photo evidence
    if not req.evidence_id and not req.evidence_url:
        raise HTTPException(
            status_code=400,
            detail="Photo evidence is required for return submission.",
        )

    # 6. Check for existing active return request on this batch
    existing_return = db.query(ReturnRequest).filter(
        ReturnRequest.batch_id == req.batch_id,
        ReturnRequest.status.in_(["PENDING", "PICKED_UP", "RECEIVED", "DISPUTED"]),
    ).first()
    if existing_return:
        raise HTTPException(
            status_code=400,
            detail=f"A return request (ID: {existing_return.id}, status: {existing_return.status}) already exists for batch {batch.batch_number}",
        )

    # 7. Execute state transition
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
                "evidence_id": req.evidence_id,
                "evidence_url": req.evidence_url,
            },
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    batch.reverse_chain_flag = True

    # 8. Persist return request
    return_request = ReturnRequest(
        batch_id=req.batch_id,
        declared_quantity=req.declared_quantity,
        distributor_id=req.distributor_id,
        status="PENDING",
        evidence_id=req.evidence_id,
        evidence_url=req.evidence_url,
    )
    db.add(return_request)
    db.commit()
    db.refresh(return_request)

    # Telegram notification for Return Created (Event 2)
    try:
        med_name = batch.medicine.name if batch.medicine else "Unknown Medicine"
        pharmacy_name = current_user.organization_name or "Pharmacy"
        distributor_name = distributor.organization_name if distributor else "Distributor"
        status_val = batch.current_status.value if hasattr(batch.current_status, "value") else str(batch.current_status)
        notify_return_created(
            medicine_name=med_name,
            batch_number=batch.batch_number,
            quantity=return_request.declared_quantity,
            current_status=status_val,
            pharmacy_org=pharmacy_name,
            distributor_org=distributor_name,
            return_id=return_request.id,
        )
    except Exception as exc:
        logger.error("Failed to trigger return creation notification: %s", exc)

    return ReturnRequestResponse.model_validate(return_request)



@router.get("/", response_model=list[ReturnRequestResponse])
def list_returns(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("PHARMACY", "DISTRIBUTOR", "REGULATOR")),
):
    """List all return requests. PHARMACY, DISTRIBUTOR, REGULATOR only."""
    returns = db.query(ReturnRequest).all()
    return [ReturnRequestResponse.model_validate(r) for r in returns]


class ReturnRejectRequest(BaseModel):
    reason: Optional[str] = "Quality inspection criteria not satisfied"


@router.post("/{return_id}/approve")
def approve_return_request(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("DISTRIBUTOR")),
):
    """Distributor approves a return request. DISTRIBUTOR only."""
    ret = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")

    batch = db.query(Batch).filter(Batch.id == ret.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    ret.status = "APPROVED"
    db.commit()
    db.refresh(ret)

    # Telegram notification for Return Approved (Event 3)
    try:
        med_name = batch.medicine.name if batch.medicine else "Unknown Medicine"
        distributor_name = current_user.organization_name
        pharmacy_name = batch.current_location or "Pharmacy"
        notify_return_approved(
            medicine_name=med_name,
            batch_number=batch.batch_number,
            quantity=ret.declared_quantity,
            distributor_org=distributor_name,
            pharmacy_org=pharmacy_name,
            return_id=ret.id,
        )
    except Exception as exc:
        logger.error("Failed to trigger return approval notification: %s", exc)

    return {"status": "ok", "message": "Return request approved", "return_status": ret.status}


@router.post("/{return_id}/reject")
def reject_return_request(
    return_id: int,
    req: Optional[ReturnRejectRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("DISTRIBUTOR")),
):
    """Distributor rejects a return request. DISTRIBUTOR only."""
    ret = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")

    batch = db.query(Batch).filter(Batch.id == ret.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    reason = req.reason if req and req.reason else "Quality inspection criteria not satisfied"
    ret.status = "REJECTED"
    db.commit()
    db.refresh(ret)

    # Telegram notification for Return Rejected (Event 4)
    try:
        med_name = batch.medicine.name if batch.medicine else "Unknown Medicine"
        distributor_name = current_user.organization_name
        pharmacy_name = batch.current_location or "Pharmacy"
        notify_return_rejected(
            medicine_name=med_name,
            batch_number=batch.batch_number,
            quantity=ret.declared_quantity,
            distributor_org=distributor_name,
            pharmacy_org=pharmacy_name,
            reason=reason,
            return_id=ret.id,
        )
    except Exception as exc:
        logger.error("Failed to trigger return rejection notification: %s", exc)

    return {"status": "ok", "message": "Return request rejected", "return_status": ret.status, "reason": reason}



@router.post("/{return_id}/pickup")
def confirm_pickup(
    return_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("DISTRIBUTOR")),
):
    """Distributor confirms pickup. DISTRIBUTOR only. Transitions batch to PICKUP_CONFIRMED."""
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
    db.commit()

    # Telegram notification for Pickup Completed (Event 5)
    try:
        med_name = batch.medicine.name if batch.medicine else "Unknown Medicine"
        distributor_name = current_user.organization_name
        pharmacy_name = "Pharmacy Store"
        notify_pickup_completed(
            medicine_name=med_name,
            batch_number=batch.batch_number,
            quantity=ret.declared_quantity,
            distributor_org=distributor_name,
            pharmacy_org=pharmacy_name,
            return_id=ret.id,
        )
    except Exception as exc:
        logger.error("Failed to trigger pickup completion notification: %s", exc)

    return {"status": "ok", "message": "Pickup confirmed", "batch_status": BatchStatus.PICKUP_CONFIRMED.value}



@router.post("/{return_id}/receive")
def receive_return(
    return_id: int,
    req: ReceiveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("DISTRIBUTOR")),
):
    """
    Distributor receives the return. DISTRIBUTOR only.
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
        db.commit()

        # Telegram notification for Discrepant Return Received (Event 6A - Disputed)
        try:
            med_name = batch.medicine.name if batch.medicine else "Unknown Medicine"
            notify_return_received(
                medicine_name=med_name,
                batch_number=batch.batch_number,
                declared_qty=declared_qty,
                received_qty=received_qty,
                status="DISPUTED",
                distributor_org=current_user.organization_name,
                is_disputed=True,
                return_id=ret.id,
            )
        except Exception as exc:
            logger.error("Failed to trigger return receipt notification: %s", exc)

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
        db.commit()

        # Telegram notification for Return Received (Event 6A - Received)
        try:
            med_name = batch.medicine.name if batch.medicine else "Unknown Medicine"
            notify_return_received(
                medicine_name=med_name,
                batch_number=batch.batch_number,
                declared_qty=declared_qty,
                received_qty=received_qty,
                status="RECEIVED_BY_DISTRIBUTOR",
                distributor_org=current_user.organization_name,
                is_disputed=False,
                return_id=ret.id,
            )
        except Exception as exc:
            logger.error("Failed to trigger return receipt notification: %s", exc)

        return {
            "status": "received",
            "message": f"Quantities match ({received_qty}). Received successfully.",
            "batch_status": BatchStatus.RECEIVED_BY_DISTRIBUTOR.value,
        }

