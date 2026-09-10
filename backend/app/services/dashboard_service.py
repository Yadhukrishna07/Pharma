import json
import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.schemas import (
    Batch, BatchStatus, Medicine, User, UserRole, ReturnRequest,
    Handoff, Dispute, DisputeStatus, DestructionRecord, Certificate,
    WorkflowEvent, ModeratorEvent, Alert, AlertSeverity, AuditLog,
)
from app.services.audit_service import verify_audit_chain


def _format_event_time(dt: datetime.datetime) -> str:
    """Format datetime into human-friendly time string (e.g. 10:42 or 10:42 AM)."""
    if not dt:
        return "N/A"
    return dt.strftime("%H:%M")


def get_target_batch(db: Session, batch_number: str = "BATCH-001") -> Optional[Batch]:
    """Retrieve the primary operational batch."""
    batch = db.query(Batch).filter(Batch.batch_number == batch_number).first()
    if not batch:
        batch = db.query(Batch).first()
    return batch


def get_recent_workflow_events(db: Session, batch_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve recent workflow events with human readable metadata."""
    events = (
        db.query(WorkflowEvent)
        .filter(WorkflowEvent.batch_id == batch_id)
        .order_by(WorkflowEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for e in events:
        actor = db.query(User).filter(User.id == e.actor_id).first()
        actor_name = actor.organization_name if actor else "System"
        actor_role = actor.role.value if actor and hasattr(actor.role, "value") else (str(actor.role) if actor else "SYSTEM")
        
        parsed_data = {}
        if e.data:
            try:
                parsed_data = json.loads(e.data)
            except Exception:
                parsed_data = {"raw": e.data}

        result.append({
            "id": e.id,
            "event_type": e.event_type,
            "from_status": e.from_status,
            "to_status": e.to_status,
            "actor_id": e.actor_id,
            "actor_name": actor_name,
            "actor_role": actor_role,
            "data": parsed_data,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "time_display": _format_event_time(e.created_at),
        })
    return result


def get_latest_moderator_insight(db: Session, batch_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve latest AI moderator insight from stored moderator_events."""
    mod = (
        db.query(ModeratorEvent)
        .filter(ModeratorEvent.batch_id == batch_id)
        .order_by(ModeratorEvent.id.desc())
        .first()
    )
    if not mod:
        return None

    return {
        "id": mod.id,
        "workflow_event_id": mod.workflow_event_id,
        "risk_level": mod.risk_level,
        "analysis": mod.analysis,
        "recommended_action": mod.recommended_action,
        "message": mod.message,
    }


def compute_workflow_progress(status_str: str) -> Dict[str, str]:
    """Compute progress states for standard stages."""
    order = {
        "ACTIVE": 0,
        "EXPIRED": 1,
        "RETURN_REQUESTED": 2,
        "PICKUP_CONFIRMED": 3,
        "RECEIVED_BY_DISTRIBUTOR": 4,
        "DISPUTED": 4,
        "RECEIVED_BY_MANUFACTURER": 5,
        "DESTRUCTION_SCHEDULED": 6,
        "DESTROYED": 7,
        "CERTIFICATE_VERIFIED": 8,
        "CLOSED": 9,
    }
    cur_val = order.get(status_str, 1)

    stage_thresholds = {
        "return": 2,
        "pickup": 3,
        "distributor_receipt": 4,
        "manufacturer_receipt": 5,
        "destruction": 7,
        "certificate": 8,
    }

    progress = {}
    for stage, thresh in stage_thresholds.items():
        if cur_val > thresh:
            progress[stage] = "COMPLETED"
        elif cur_val == thresh:
            progress[stage] = "CURRENT" if status_str != "DISPUTED" else "DISPUTED"
        else:
            progress[stage] = "PENDING"
    return progress


def get_pharmacy_dashboard(db: Session, user: Optional[User] = None) -> Dict[str, Any]:
    """Dashboard aggregation for PHARMACY role."""
    batch = get_target_batch(db)
    if not batch:
        return {"error": "No batch found"}

    status = batch.current_status.value if hasattr(batch.current_status, "value") else str(batch.current_status)
    medicine_name = batch.medicine.name if batch.medicine else "Augmentin Duo 625mg"

    # Latest return request
    ret = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.batch_id == batch.id)
        .order_by(ReturnRequest.id.desc())
        .first()
    )

    return_status = ret.status if ret else "NOT_INITIATED"
    declared_quantity = ret.declared_quantity if ret else batch.quantity

    # Recent activity
    recent_events = get_recent_workflow_events(db, batch.id, limit=5)

    # Next action
    if status == "EXPIRED":
        next_action = "Initiate Reverse Chain Return Request for Expired Inventory"
    elif status == "RETURN_REQUESTED":
        next_action = "Awaiting BlueDart Logistics physical pickup confirmation"
    elif status == "PICKUP_CONFIRMED":
        next_action = "Batch in transit — awaiting distributor warehouse receipt & verification"
    elif status == "RECEIVED_BY_DISTRIBUTOR":
        next_action = "Batch received at distributor warehouse — proceeding to manufacturer"
    elif status == "DISPUTED":
        next_action = "Dispute active at distributor — awaiting quantity resolution"
    elif status == "RECEIVED_BY_MANUFACTURER":
        next_action = "Batch safely received at Sun Pharma Laboratories quarantine"
    elif status == "DESTRUCTION_SCHEDULED":
        next_action = "Destruction scheduled at BioClean Biomedical Waste Facility"
    elif status == "DESTROYED":
        next_action = "Destruction completed — awaiting CDSCO regulatory certificate verification"
    elif status in ("CERTIFICATE_VERIFIED", "CLOSED"):
        next_action = "Batch compliance lifecycle CLOSED and cryptographically sealed"
    else:
        next_action = "Monitor batch status"

    # Moderator insight
    moderator_insight = get_latest_moderator_insight(db, batch.id)

    # Alerts
    alerts = (
        db.query(Alert)
        .filter(Alert.batch_id == batch.id)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "role": "PHARMACY",
        "organization_name": user.organization_name if user else "MedPlus Central Indiranagar",
        "batch": {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "medicine_name": medicine_name,
            "quantity": batch.quantity,
            "expiry_date": str(batch.expiry_date),
            "current_status": status,
            "current_location": batch.current_location or "Pharmacy Shelf",
            "reverse_chain_flag": batch.reverse_chain_flag,
            "destruction_status": batch.destruction_status,
        },
        "return_request": {
            "id": ret.id if ret else None,
            "status": return_status,
            "declared_quantity": declared_quantity,
            "distributor_id": ret.distributor_id if ret else 3,
        } if ret else None,
        "return_status": return_status,
        "progress": compute_workflow_progress(status),
        "next_action": next_action,
        "recent_activity": recent_events,
        "moderator_insight": moderator_insight,
        "alerts": [
            {
                "id": a.id,
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "title": a.title,
                "description": a.description,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "time_display": _format_event_time(a.created_at),
            }
            for a in alerts
        ],
    }


def get_distributor_dashboard(db: Session, user: Optional[User] = None) -> Dict[str, Any]:
    """Dashboard aggregation for DISTRIBUTOR role."""
    batch = get_target_batch(db)
    if not batch:
        return {"error": "No batch found"}

    status = batch.current_status.value if hasattr(batch.current_status, "value") else str(batch.current_status)
    medicine_name = batch.medicine.name if batch.medicine else "Augmentin Duo 625mg"

    # Latest return request
    ret = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.batch_id == batch.id)
        .order_by(ReturnRequest.id.desc())
        .first()
    )

    # Check for dispute
    dispute = (
        db.query(Dispute)
        .filter(Dispute.batch_id == batch.id)
        .order_by(Dispute.id.desc())
        .first()
    )

    # Pickup state
    pickup_state = "PENDING"
    if status in [
        "PICKUP_CONFIRMED", "RECEIVED_BY_DISTRIBUTOR", "DISPUTED",
        "RECEIVED_BY_MANUFACTURER", "DESTRUCTION_SCHEDULED",
        "DESTROYED", "CERTIFICATE_VERIFIED", "CLOSED"
    ]:
        pickup_state = "CONFIRMED"

    # Receipt state
    receipt_state = "AWAITING"
    if status in ["RECEIVED_BY_DISTRIBUTOR", "RECEIVED_BY_MANUFACTURER", "DESTRUCTION_SCHEDULED", "DESTROYED", "CERTIFICATE_VERIFIED", "CLOSED"]:
        receipt_state = "RECEIVED"
    elif status == "DISPUTED":
        receipt_state = "DISPUTED"

    expected_quantity = ret.declared_quantity if ret else 100
    received_quantity = None
    if dispute:
        received_quantity = dispute.received_qty
    elif receipt_state == "RECEIVED":
        received_quantity = expected_quantity

    # Next action
    if not ret or (ret.status == "PENDING" and status == "RETURN_REQUESTED"):
        next_action = "Confirm physical pickup at MedPlus Central Indiranagar"
    elif status == "PICKUP_CONFIRMED":
        next_action = "Receive and verify inventory count at BlueDart warehouse"
    elif status == "DISPUTED":
        next_action = "Resolve open quantity discrepancy (100 declared vs 95 received)"
    elif status == "RECEIVED_BY_DISTRIBUTOR":
        next_action = "Forward verified batch to Sun Pharma Laboratories"
    else:
        next_action = "Batch successfully transferred to Manufacturer"

    recent_events = get_recent_workflow_events(db, batch.id, limit=5)
    moderator_insight = get_latest_moderator_insight(db, batch.id)

    return {
        "role": "DISTRIBUTOR",
        "organization_name": user.organization_name if user else "BlueDart Pharma Logistics",
        "batch": {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "medicine_name": medicine_name,
            "quantity": batch.quantity,
            "expiry_date": str(batch.expiry_date),
            "current_status": status,
            "current_location": batch.current_location or "In Transit",
        },
        "incoming_return": {
            "id": ret.id if ret else None,
            "status": ret.status if ret else "NONE",
            "declared_quantity": expected_quantity,
        } if ret else None,
        "expected_quantity": expected_quantity,
        "received_quantity": received_quantity,
        "pickup_state": pickup_state,
        "receipt_state": receipt_state,
        "dispute": {
            "id": dispute.id,
            "status": dispute.status.value if hasattr(dispute.status, "value") else str(dispute.status),
            "declared_qty": dispute.declared_qty,
            "received_qty": dispute.received_qty,
            "variance": dispute.declared_qty - dispute.received_qty,
            "resolution_notes": dispute.resolution_notes,
        } if dispute else None,
        "has_discrepancy": dispute is not None,
        "next_action": next_action,
        "progress": compute_workflow_progress(status),
        "recent_activity": recent_events,
        "moderator_insight": moderator_insight,
    }


def get_manufacturer_dashboard(db: Session, user: Optional[User] = None) -> Dict[str, Any]:
    """Dashboard aggregation for MANUFACTURER role."""
    batch = get_target_batch(db)
    if not batch:
        return {"error": "No batch found"}

    status = batch.current_status.value if hasattr(batch.current_status, "value") else str(batch.current_status)
    medicine_name = batch.medicine.name if batch.medicine else "Augmentin Duo 625mg"

    # Manufacturer receipt
    mfg_receipt_state = "PENDING"
    if status in [
        "RECEIVED_BY_MANUFACTURER", "DESTRUCTION_SCHEDULED",
        "DESTROYED", "CERTIFICATE_VERIFIED", "CLOSED"
    ]:
        mfg_receipt_state = "CONFIRMED"

    # Destruction scheduling state
    destruction_scheduling_state = "UNSCHEDULED"
    if status in ["DESTRUCTION_SCHEDULED", "DESTROYED", "CERTIFICATE_VERIFIED", "CLOSED"]:
        destruction_scheduling_state = "SCHEDULED"

    # Current quantity (reflecting dispute resolution if received was 95)
    dispute = db.query(Dispute).filter(Dispute.batch_id == batch.id).first()
    current_quantity = dispute.received_qty if dispute else batch.quantity

    # Next action
    if status in ["RETURN_REQUESTED", "PICKUP_CONFIRMED"]:
        next_action = "Awaiting distributor reverse logistics transit"
    elif status == "DISPUTED":
        next_action = "Awaiting distributor discrepancy resolution before intake"
    elif status == "RECEIVED_BY_DISTRIBUTOR":
        next_action = "Confirm receipt into quarantine at Sun Pharma Laboratories"
    elif status == "RECEIVED_BY_MANUFACTURER":
        next_action = "Schedule batch destruction with BioClean Biomedical Waste Facility"
    elif status == "DESTRUCTION_SCHEDULED":
        next_action = "Batch dispatched to BioClean facility — awaiting destruction"
    elif status == "DESTROYED":
        next_action = "Incineration complete — awaiting regulatory certificate verification"
    elif status in ["CERTIFICATE_VERIFIED", "CLOSED"]:
        next_action = "Reverse supply chain cycle complete and verified"
    else:
        next_action = "Monitor reverse supply chain intake"

    recent_events = get_recent_workflow_events(db, batch.id, limit=5)
    moderator_insight = get_latest_moderator_insight(db, batch.id)

    return {
        "role": "MANUFACTURER",
        "organization_name": user.organization_name if user else "Sun Pharma Laboratories",
        "batch": {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "medicine_name": medicine_name,
            "quantity": current_quantity,
            "current_status": status,
            "current_location": batch.current_location or "Manufacturer Facility",
        },
        "manufacturer_receipt_state": mfg_receipt_state,
        "destruction_scheduling_state": destruction_scheduling_state,
        "facility_name": "BioClean Biomedical Waste Facility",
        "facility_id": 5,
        "next_action": next_action,
        "progress": compute_workflow_progress(status),
        "recent_activity": recent_events,
        "moderator_insight": moderator_insight,
    }


def get_facility_dashboard(db: Session, user: Optional[User] = None) -> Dict[str, Any]:
    """Dashboard aggregation for FACILITY role."""
    batch = get_target_batch(db)
    if not batch:
        return {"error": "No batch found"}

    status = batch.current_status.value if hasattr(batch.current_status, "value") else str(batch.current_status)
    medicine_name = batch.medicine.name if batch.medicine else "Augmentin Duo 625mg"

    # Destruction record
    destruction_rec = (
        db.query(DestructionRecord)
        .filter(DestructionRecord.batch_id == batch.id)
        .order_by(DestructionRecord.id.desc())
        .first()
    )

    # Certificate
    cert = (
        db.query(Certificate)
        .filter(Certificate.batch_id == batch.id)
        .order_by(Certificate.id.desc())
        .first()
    )

    dispute = db.query(Dispute).filter(Dispute.batch_id == batch.id).first()
    qty_to_destroy = dispute.received_qty if dispute else (destruction_rec.quantity_destroyed if destruction_rec else batch.quantity)

    # Destruction status
    destruction_status = "PENDING"
    if status in ["DESTROYED", "CERTIFICATE_VERIFIED", "CLOSED"] or destruction_rec:
        destruction_status = "DESTROYED"

    # Certificate status
    certificate_status = "NOT_ISSUED"
    if cert:
        if cert.is_verified or status in ["CERTIFICATE_VERIFIED", "CLOSED"]:
            certificate_status = "CERTIFICATE_VERIFIED_CLOSED"
        else:
            certificate_status = "ISSUED_AWAITING_VERIFICATION"

    # Next action
    if status in ["RETURN_REQUESTED", "PICKUP_CONFIRMED", "RECEIVED_BY_DISTRIBUTOR", "DISPUTED", "RECEIVED_BY_MANUFACTURER"]:
        next_action = "Awaiting formal destruction scheduling from Sun Pharma"
    elif status == "DESTRUCTION_SCHEDULED":
        next_action = f"Record high-temperature incineration destruction ({qty_to_destroy} packs)"
    elif status == "DESTROYED" and not cert:
        next_action = "Generate and issue signed Destruction Certificate for CDSCO Regulator"
    elif cert and not cert.is_verified:
        next_action = f"Certificate #{cert.certificate_number} issued — awaiting CDSCO verification"
    elif status in ["CERTIFICATE_VERIFIED", "CLOSED"]:
        next_action = "Certificate verified by CDSCO Regulator — Compliance lifecycle CLOSED"
    else:
        next_action = "Monitor biomedical waste destruction operations"

    recent_events = get_recent_workflow_events(db, batch.id, limit=5)
    moderator_insight = get_latest_moderator_insight(db, batch.id)

    return {
        "role": "FACILITY",
        "organization_name": user.organization_name if user else "BioClean Biomedical Waste Facility",
        "batch": {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "medicine_name": medicine_name,
            "quantity_to_destroy": qty_to_destroy,
            "current_status": status,
            "current_location": batch.current_location or "BioClean Facility",
            "scheduled_status": "SCHEDULED" if status in ["DESTRUCTION_SCHEDULED", "DESTROYED", "CERTIFICATE_VERIFIED", "CLOSED"] else "PENDING",
            "scheduled_date": str(datetime.date.today()),
            "destruction_status": destruction_status,
        },
        "destruction_record": {
            "id": destruction_rec.id,
            "quantity_destroyed": destruction_rec.quantity_destroyed,
            "timestamp": destruction_rec.timestamp.isoformat() if destruction_rec.timestamp else None,
        } if destruction_rec else None,
        "certificate_status": certificate_status,
        "certificate": {
            "id": cert.id,
            "certificate_number": cert.certificate_number,
            "quantity": cert.quantity,
            "issued_date": str(cert.issued_date),
            "is_verified": cert.is_verified,
        } if cert else None,
        "next_action": next_action,
        "progress": compute_workflow_progress(status),
        "recent_activity": recent_events,
        "moderator_insight": moderator_insight,
    }


def get_regulator_dashboard(db: Session, user: Optional[User] = None) -> Dict[str, Any]:
    """Dashboard aggregation for REGULATOR role."""
    batch = get_target_batch(db)
    if not batch:
        return {"error": "No batch found"}

    status = batch.current_status.value if hasattr(batch.current_status, "value") else str(batch.current_status)
    medicine_name = batch.medicine.name if batch.medicine else "Augmentin Duo 625mg"

    # Metric counts across all active returns
    active_returns_count = (
        db.query(Batch)
        .filter(Batch.current_status.in_([
            BatchStatus.RETURN_REQUESTED,
            BatchStatus.PICKUP_CONFIRMED,
            BatchStatus.RECEIVED_BY_DISTRIBUTOR,
            BatchStatus.DISPUTED,
            BatchStatus.RECEIVED_BY_MANUFACTURER,
        ]))
        .count()
    )

    pending_destruction_count = (
        db.query(Batch)
        .filter(Batch.current_status == BatchStatus.DESTRUCTION_SCHEDULED)
        .count()
    )

    verified_destruction_count = (
        db.query(Batch)
        .filter(Batch.current_status.in_([
            BatchStatus.CERTIFICATE_VERIFIED,
            BatchStatus.CLOSED,
        ]))
        .count()
    )

    critical_fraud_alerts_count = (
        db.query(Alert)
        .filter(Alert.severity == AlertSeverity.CRITICAL, Alert.is_acknowledged == False)
        .count()
    )

    # Full LIVE workflow timeline from PostgreSQL
    timeline_events = (
        db.query(WorkflowEvent)
        .filter(WorkflowEvent.batch_id == batch.id)
        .order_by(WorkflowEvent.created_at.asc())
        .all()
    )

    timeline_list = []
    for e in timeline_events:
        actor = db.query(User).filter(User.id == e.actor_id).first()
        actor_name = actor.organization_name if actor else "System"
        actor_role = actor.role.value if actor and hasattr(actor.role, "value") else (str(actor.role) if actor else "SYSTEM")
        parsed_data = {}
        if e.data:
            try:
                parsed_data = json.loads(e.data)
            except Exception:
                parsed_data = {"raw": e.data}

        timeline_list.append({
            "id": e.id,
            "event_type": e.event_type,
            "from_status": e.from_status,
            "to_status": e.to_status,
            "actor_id": e.actor_id,
            "actor_name": actor_name,
            "actor_role": actor_role,
            "data": parsed_data,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "time_display": _format_event_time(e.created_at),
        })

    # Alerts (including CRITICAL RE-ENTRY)
    alerts = (
        db.query(Alert)
        .filter(Alert.batch_id == batch.id)
        .order_by(Alert.created_at.desc())
        .all()
    )

    # Certificates
    certificates = (
        db.query(Certificate)
        .filter(Certificate.batch_id == batch.id)
        .order_by(Certificate.id.desc())
        .all()
    )

    # Latest moderator event
    moderator_insight = get_latest_moderator_insight(db, batch.id)

    # Derived recommended action
    if status == "DESTROYED" and certificates and not certificates[0].is_verified:
        recommended_action = f"Verify destruction certificate #{certificates[0].certificate_number} to formalize compliance closure."
    elif any(a.severity == AlertSeverity.CRITICAL and not a.is_acknowledged for a in alerts):
        recommended_action = "CRITICAL: Investigate re-entry fraud alert immediately. Dispatch enforcement inspector."
    elif status == "DISPUTED":
        recommended_action = "Review quantity variance between MedPlus Central and BlueDart Logistics."
    elif status in ["CERTIFICATE_VERIFIED", "CLOSED"]:
        recommended_action = "Lifecycle successfully closed. Maintain tamper-evident cryptographic log."
    else:
        recommended_action = moderator_insight.get("recommended_action") if moderator_insight else "Supervise reverse supply chain custody handoffs."

    # Audit chain verification status
    audit_verification = verify_audit_chain(db)

    return {
        "role": "REGULATOR",
        "organization_name": user.organization_name if user else "CDSCO Regulator",
        "batch": {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "medicine_name": medicine_name,
            "quantity": batch.quantity,
            "current_status": status,
            "current_location": batch.current_location or "Under Regulatory Oversight",
            "reverse_chain_flag": batch.reverse_chain_flag,
            "destruction_status": batch.destruction_status,
        },
        "summary_cards": {
            "active_returns": active_returns_count,
            "pending_destruction": pending_destruction_count,
            "verified_destruction": verified_destruction_count,
            "critical_fraud_alerts": critical_fraud_alerts_count,
        },
        "timeline": timeline_list,
        "alerts": [
            {
                "id": a.id,
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "title": a.title,
                "description": a.description,
                "is_acknowledged": a.is_acknowledged,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "time_display": _format_event_time(a.created_at),
            }
            for a in alerts
        ],
        "certificates": [
            {
                "id": c.id,
                "certificate_number": c.certificate_number,
                "quantity": c.quantity,
                "issued_date": str(c.issued_date),
                "is_verified": c.is_verified,
            }
            for c in certificates
        ],
        "moderator_insight": moderator_insight,
        "recommended_action": recommended_action,
        "audit_verification": audit_verification,
        "progress": compute_workflow_progress(status),
        "recent_activity": get_recent_workflow_events(db, batch.id, limit=5),
    }
