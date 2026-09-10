from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models.schemas import (
    User, Batch, BatchStatus, AuditLog, Alert, AlertSeverity,
    AuditLogResponse, AuditVerifyResponse, AlertResponse, DashboardStats,
)
from app.services.audit_service import verify_audit_chain

router = APIRouter(tags=["Audit & Alerts"])


# ──────────────────────────────────────────────
#  Audit Endpoints
# ──────────────────────────────────────────────

@router.get("/audit/", response_model=list[AuditLogResponse])
def get_audit_log(db: Session = Depends(get_db)):
    """Get the full audit log ordered by timestamp."""
    records = db.query(AuditLog).order_by(AuditLog.timestamp.asc()).all()
    return [AuditLogResponse.model_validate(r) for r in records]


@router.post("/audit/verify", response_model=AuditVerifyResponse)
def verify_audit(db: Session = Depends(get_db)):
    """
    Verify the cryptographic hash chain integrity.
    Recalculates all hashes and flags any tampered records.
    """
    return verify_audit_chain(db)


# ──────────────────────────────────────────────
#  Alert Endpoints
# ──────────────────────────────────────────────

@router.get("/alerts/", response_model=list[AlertResponse])
def get_alerts(db: Session = Depends(get_db)):
    """Get all alerts ordered by most recent."""
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).all()
    return [AlertResponse.model_validate(a) for a in alerts]


@router.get("/alerts/critical", response_model=list[AlertResponse])
def get_critical_alerts(db: Session = Depends(get_db)):
    """Get only CRITICAL severity alerts."""
    alerts = (
        db.query(Alert)
        .filter(Alert.severity == AlertSeverity.CRITICAL)
        .order_by(Alert.created_at.desc())
        .all()
    )
    return [AlertResponse.model_validate(a) for a in alerts]


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_acknowledged = True
    db.commit()
    return {"status": "ok", "message": "Alert acknowledged"}


# ──────────────────────────────────────────────
#  Dashboard Stats
# ──────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get aggregated dashboard statistics for the regulator view."""
    active_returns = (
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

    pending_destruction = (
        db.query(Batch)
        .filter(Batch.current_status == BatchStatus.DESTRUCTION_SCHEDULED)
        .count()
    )

    verified_destruction = (
        db.query(Batch)
        .filter(Batch.current_status.in_([
            BatchStatus.CERTIFICATE_VERIFIED,
            BatchStatus.CLOSED,
        ]))
        .count()
    )

    critical_fraud_alerts = (
        db.query(Alert)
        .filter(Alert.severity == AlertSeverity.CRITICAL, Alert.is_acknowledged == False)
        .count()
    )

    return DashboardStats(
        active_returns=active_returns,
        pending_destruction=pending_destruction,
        verified_destruction=verified_destruction,
        critical_fraud_alerts=critical_fraud_alerts,
    )
