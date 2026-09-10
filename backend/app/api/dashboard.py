from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_optional_current_user
from app.models.schemas import User, UserRole
from app.services.dashboard_service import (
    get_pharmacy_dashboard,
    get_distributor_dashboard,
    get_manufacturer_dashboard,
    get_facility_dashboard,
    get_regulator_dashboard,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class ResetRequest(BaseModel):
    mode: Optional[str] = "fresh"  # "fresh" or "history"


@router.get("/pharmacy")
def pharmacy_dashboard_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Real-time live dashboard for PHARMACY role."""
    return get_pharmacy_dashboard(db, current_user)


@router.get("/distributor")
def distributor_dashboard_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Real-time live dashboard for DISTRIBUTOR role."""
    return get_distributor_dashboard(db, current_user)


@router.get("/manufacturer")
def manufacturer_dashboard_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Real-time live dashboard for MANUFACTURER role."""
    return get_manufacturer_dashboard(db, current_user)


@router.get("/facility")
def facility_dashboard_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Real-time live dashboard for FACILITY role."""
    return get_facility_dashboard(db, current_user)


@router.get("/regulator")
def regulator_dashboard_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Real-time live dashboard for REGULATOR role."""
    return get_regulator_dashboard(db, current_user)


@router.get("/stats")
def dashboard_stats_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Summary metrics cards."""
    reg_dash = get_regulator_dashboard(db, current_user)
    return reg_dash.get("summary_cards", {})


@router.post("/reset")
def reset_demo_endpoint(
    req: Optional[ResetRequest] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Reset BATCH-001 to fresh state or populated sample history.
    Useful for demonstration and live workflow testing.
    """
    mode = req.mode if req else "fresh"
    from seed import reset_batch_workflow
    result = reset_batch_workflow(db, mode=mode)
    return {"status": "ok", "mode": mode, "details": result}


@router.get("/{role}")
def role_dashboard_fallback(
    role: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Dynamic role dashboard resolver."""
    role_norm = role.lower().strip()
    if role_norm == "pharmacy":
        return get_pharmacy_dashboard(db, current_user)
    elif role_norm == "distributor":
        return get_distributor_dashboard(db, current_user)
    elif role_norm == "manufacturer":
        return get_manufacturer_dashboard(db, current_user)
    elif role_norm == "facility":
        return get_facility_dashboard(db, current_user)
    elif role_norm == "regulator":
        return get_regulator_dashboard(db, current_user)
    else:
        raise HTTPException(status_code=404, detail=f"Dashboard for role '{role}' not found")
