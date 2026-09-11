import logging
import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_roles, require_role
from app.models.schemas import (
    Batch, BatchStatus, User, Certificate,
    CertificateCreateRequest, CertificateResponse,
)
from app.services.workflow_service import transition_state
from app.services.telegram_service import notify_disposal_closure_completed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certificates", tags=["Certificates"])



@router.post("", response_model=CertificateResponse)
@router.post("/", response_model=CertificateResponse)
def create_certificate(
    req: CertificateCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("FACILITY")),
):
    """
    Facility generates a destruction certificate. FACILITY only.
    Does NOT change batch status — awaits regulator verification.
    """
    batch = db.query(Batch).filter(Batch.id == req.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Check that batch is in DESTROYED state
    current_status = batch.current_status
    if hasattr(current_status, "value"):
        current_status = current_status.value
    if current_status != BatchStatus.DESTROYED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Batch must be in DESTROYED state to generate certificate. Current: {current_status}",
        )

    # Check for existing certificate
    existing = db.query(Certificate).filter(
        Certificate.certificate_number == req.certificate_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Certificate number already exists")

    certificate = Certificate(
        certificate_number=req.certificate_number,
        batch_id=req.batch_id,
        facility_id=current_user.id,
        quantity=req.quantity,
        issued_date=datetime.date.today(),
        is_verified=False,
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)

    return CertificateResponse.model_validate(certificate)


@router.get("", response_model=list[CertificateResponse])
@router.get("/", response_model=list[CertificateResponse])
def list_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all certificates. Any authenticated user."""
    certs = db.query(Certificate).all()
    return [CertificateResponse.model_validate(c) for c in certs]


@router.get("/{cert_id}", response_model=CertificateResponse)
def get_certificate(
    cert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single certificate. Any authenticated user."""
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return CertificateResponse.model_validate(cert)


@router.post("/{cert_id}/verify")
def verify_certificate(
    cert_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("REGULATOR")),
):
    """
    Regulator verifies a destruction certificate. REGULATOR only.
    Transitions batch: DESTROYED → CERTIFICATE_VERIFIED → CLOSED.
    """
    cert = db.query(Certificate).filter(Certificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if cert.is_verified:
        raise HTTPException(status_code=400, detail="Certificate already verified")

    batch = db.query(Batch).filter(Batch.id == cert.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Transition to CERTIFICATE_VERIFIED
    try:
        transition_state(
            db=db,
            batch=batch,
            target_status=BatchStatus.CERTIFICATE_VERIFIED.value,
            actor_id=current_user.id,
            event_type="CERTIFICATE_VERIFIED",
            event_data={
                "certificate_id": cert.id,
                "certificate_number": cert.certificate_number,
                "quantity": cert.quantity,
            },
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Transition to CLOSED
    try:
        transition_state(
            db=db,
            batch=batch,
            target_status=BatchStatus.CLOSED.value,
            actor_id=current_user.id,
            event_type="BATCH_CLOSED",
            event_data={
                "certificate_number": cert.certificate_number,
                "verified_by": current_user.organization_name,
            },
            background_tasks=background_tasks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cert.is_verified = True
    batch.current_location = "Closed — Regulatory Verified"
    db.commit()

    # Telegram notification for Disposal & Batch Closure Verified (Event 6B)
    try:
        med_name = batch.medicine.name if batch.medicine else "Unknown Medicine"
        facility_user = db.query(User).filter(User.id == cert.facility_id).first()
        facility_name = facility_user.organization_name if facility_user else "Disposal Facility"
        verifier_name = current_user.organization_name or "CDSCO Regulator"
        notify_disposal_closure_completed(
            medicine_name=med_name,
            batch_number=batch.batch_number,
            quantity=cert.quantity,
            certificate_number=cert.certificate_number,
            verifier_org=verifier_name,
            facility_org=facility_name,
        )
    except Exception as exc:
        logger.error("Failed to trigger disposal closure notification: %s", exc)

    return {
        "status": "verified",
        "message": "Certificate verified. Batch lifecycle closed.",
        "batch_status": BatchStatus.CLOSED.value,
    }

