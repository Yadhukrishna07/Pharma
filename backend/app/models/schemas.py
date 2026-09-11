import enum
import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text, ForeignKey, Enum, Float, UniqueConstraint
)
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from app.database import Base


# ──────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────

class UserRole(str, enum.Enum):
    PHARMACY = "PHARMACY"
    DISTRIBUTOR = "DISTRIBUTOR"
    MANUFACTURER = "MANUFACTURER"
    FACILITY = "FACILITY"
    REGULATOR = "REGULATOR"


class BatchStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    PICKUP_CONFIRMED = "PICKUP_CONFIRMED"
    RECEIVED_BY_DISTRIBUTOR = "RECEIVED_BY_DISTRIBUTOR"
    DISPUTED = "DISPUTED"
    RECEIVED_BY_MANUFACTURER = "RECEIVED_BY_MANUFACTURER"
    DESTRUCTION_SCHEDULED = "DESTRUCTION_SCHEDULED"
    DESTROYED = "DESTROYED"
    CERTIFICATE_VERIFIED = "CERTIFICATE_VERIFIED"
    CLOSED = "CLOSED"


class DisputeStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ──────────────────────────────────────────────
#  Utility: Expiry Status
# ──────────────────────────────────────────────

def compute_expiry_status(expiry_date: datetime.date) -> str:
    """
    Derive a human-readable expiry label from a stored date.
    Completely independent of the batch workflow current_status.
      EXPIRED      — expiry_date < today
      EXPIRING_SOON — today <= expiry_date <= today + 90 days
      ACTIVE       — expiry_date > today + 90 days
    """
    today = datetime.date.today()
    if expiry_date < today:
        return "EXPIRED"
    if expiry_date <= today + datetime.timedelta(days=90):
        return "EXPIRING_SOON"
    return "ACTIVE"


# ──────────────────────────────────────────────
#  SQLAlchemy ORM Models
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    organization_name = Column(String(255), nullable=False)

    notifications = relationship("Notification", back_populates="user")


class Medicine(Base):
    __tablename__ = "medicines"

    # ── Core identifier (backward-compat: name == brand_name) ──
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    manufacturer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # ── Pharmaceutical detail fields (all nullable for backward compat) ──
    brand_name = Column(String(255), nullable=True)
    generic_name = Column(String(255), nullable=True)
    strength = Column(String(100), nullable=True)
    dosage_form = Column(String(100), nullable=True)
    route_of_administration = Column(String(100), nullable=True)
    composition = Column(Text, nullable=True)
    pack_size = Column(String(50), nullable=True)
    storage_conditions = Column(String(255), nullable=True)
    mrp = Column(Float, nullable=True)
    prescription_required = Column(Boolean, default=False, nullable=True)
    manufacturing_date = Column(Date, nullable=True)

    manufacturer = relationship("User")
    batches = relationship("Batch", back_populates="medicine")


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(100), unique=True, nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    expiry_date = Column(Date, nullable=False)
    current_status = Column(Enum(BatchStatus), nullable=False, default=BatchStatus.ACTIVE)
    current_location = Column(String(255), nullable=True)
    reverse_chain_flag = Column(Boolean, default=False)
    destruction_status = Column(String(50), nullable=True)

    medicine = relationship("Medicine", back_populates="batches")
    return_requests = relationship("ReturnRequest", back_populates="batch")
    handoffs = relationship("Handoff", back_populates="batch")
    disputes = relationship("Dispute", back_populates="batch")
    destruction_records = relationship("DestructionRecord", back_populates="batch")
    certificates = relationship("Certificate", back_populates="batch")
    workflow_events = relationship("WorkflowEvent", back_populates="batch", order_by="WorkflowEvent.created_at")
    alerts = relationship("Alert", back_populates="batch")


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    declared_quantity = Column(Integer, nullable=False)
    distributor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    evidence_id = Column(String(100), nullable=True)
    evidence_url = Column(String(255), nullable=True)

    batch = relationship("Batch", back_populates="return_requests")
    distributor = relationship("User")


class Handoff(Base):
    __tablename__ = "handoffs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    from_role = Column(Enum(UserRole), nullable=False)
    to_role = Column(Enum(UserRole), nullable=False)
    received_quantity = Column(Integer, nullable=True)
    discrepancy_flag = Column(Boolean, default=False)

    batch = relationship("Batch", back_populates="handoffs")


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    declared_qty = Column(Integer, nullable=False)
    received_qty = Column(Integer, nullable=False)
    status = Column(Enum(DisputeStatus), nullable=False, default=DisputeStatus.OPEN)
    resolution_notes = Column(Text, nullable=True)

    batch = relationship("Batch", back_populates="disputes")


class DestructionRecord(Base):
    __tablename__ = "destruction_records"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    facility_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity_destroyed = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    batch = relationship("Batch", back_populates="destruction_records")
    facility = relationship("User")


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    certificate_number = Column(String(100), unique=True, nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    facility_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    issued_date = Column(Date, default=datetime.date.today)
    is_verified = Column(Boolean, default=False)

    batch = relationship("Batch", back_populates="certificates")
    facility = relationship("User")


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    batch = relationship("Batch", back_populates="workflow_events")
    actor = relationship("User")
    moderator_event = relationship("ModeratorEvent", back_populates="workflow_event", uselist=False)


class ModeratorEvent(Base):
    __tablename__ = "moderator_events"

    id = Column(Integer, primary_key=True, index=True)
    workflow_event_id = Column(Integer, ForeignKey("workflow_events.id"), unique=True, nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    risk_level = Column(String(20), nullable=False)
    analysis = Column(Text, nullable=True)
    recommended_action = Column(Text, nullable=True)
    message = Column(Text, nullable=True)

    workflow_event = relationship("WorkflowEvent", back_populates="moderator_event")
    batch = relationship("Batch")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    batch = relationship("Batch", back_populates="alerts")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    read_status = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    event_data = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False)

    batch = relationship("Batch")
    actor = relationship("User")


# ──────────────────────────────────────────────
#  Pydantic Schemas — Auth
# ──────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole
    organization_name: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    organization_name: str

    model_config = {"from_attributes": True}


class RoleSwitchRequest(BaseModel):
    role: UserRole


# ──────────────────────────────────────────────
#  Pydantic Schemas — Batches
# ──────────────────────────────────────────────

class BatchResponse(BaseModel):
    id: int
    batch_number: str
    medicine_name: Optional[str] = None
    quantity: int
    expiry_date: datetime.date
    # Derived from expiry_date at API time — NOT the workflow current_status
    expiry_status: str = "ACTIVE"
    current_status: str
    current_location: Optional[str] = None
    reverse_chain_flag: bool
    destruction_status: Optional[str] = None
    # Medicine detail fields (populated when available)
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None

    model_config = {"from_attributes": True}


class BatchScanRequest(BaseModel):
    batch_number: str
    location: Optional[str] = None
    actor_role: Optional[str] = None


class BatchScanResponse(BaseModel):
    batch: BatchResponse
    fraud_detected: bool = False
    alert: Optional[str] = None
    message: str = ""


# ──────────────────────────────────────────────
#  Pydantic Schemas — Returns
# ──────────────────────────────────────────────

class ReturnRequestCreate(BaseModel):
    batch_id: int = Field(..., gt=0, description="ID of the batch being returned")
    declared_quantity: int = Field(..., gt=0, description="Declared quantity to return (must be > 0)")
    distributor_id: int = Field(..., gt=0, description="ID of the designated distributor")
    evidence_id: Optional[str] = Field(None, description="ID of the uploaded photo evidence")
    evidence_url: Optional[str] = Field(None, description="URL of the uploaded photo evidence")


class ReturnRequestResponse(BaseModel):
    id: int
    batch_id: int
    declared_quantity: int
    distributor_id: int
    status: str
    evidence_id: Optional[str] = None
    evidence_url: Optional[str] = None
    batch: Optional[BatchResponse] = None

    model_config = {"from_attributes": True}


class PickupConfirmRequest(BaseModel):
    batch_id: int


class ReceiveRequest(BaseModel):
    batch_id: int
    received_quantity: int


# ──────────────────────────────────────────────
#  Pydantic Schemas — Disputes
# ──────────────────────────────────────────────

class DisputeResponse(BaseModel):
    id: int
    batch_id: int
    declared_qty: int
    received_qty: int
    status: str
    resolution_notes: Optional[str] = None

    model_config = {"from_attributes": True}


class DisputeResolveRequest(BaseModel):
    resolution_notes: str


# ──────────────────────────────────────────────
#  Pydantic Schemas — Destruction
# ──────────────────────────────────────────────

class DestructionScheduleRequest(BaseModel):
    batch_id: int
    facility_id: int


class DestructionRecordCreate(BaseModel):
    batch_id: int
    quantity_destroyed: int


class DestructionRecordResponse(BaseModel):
    id: int
    batch_id: int
    facility_id: int
    quantity_destroyed: int
    timestamp: datetime.datetime

    model_config = {"from_attributes": True}


class HandoffRequest(BaseModel):
    batch_id: int
    from_role: UserRole
    to_role: UserRole
    received_quantity: Optional[int] = None


class HandoffResponse(BaseModel):
    id: int
    batch_id: int
    from_role: str
    to_role: str
    received_quantity: Optional[int] = None
    discrepancy_flag: bool

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Pydantic Schemas — Certificates
# ──────────────────────────────────────────────

class CertificateCreateRequest(BaseModel):
    certificate_number: str
    batch_id: int
    quantity: int


class CertificateResponse(BaseModel):
    id: int
    certificate_number: str
    batch_id: int
    facility_id: int
    quantity: int
    issued_date: datetime.date
    is_verified: bool

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Pydantic Schemas — Workflow & Timeline
# ──────────────────────────────────────────────

class WorkflowEventResponse(BaseModel):
    id: int
    batch_id: int
    actor_id: int
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    data: Optional[str] = None
    created_at: datetime.datetime
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None

    model_config = {"from_attributes": True}


class ModeratorEventResponse(BaseModel):
    id: int
    workflow_event_id: int
    batch_id: int
    risk_level: str
    analysis: Optional[str] = None
    recommended_action: Optional[str] = None
    message: Optional[str] = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Pydantic Schemas — Alerts
# ──────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    batch_id: int
    severity: str
    title: str
    description: Optional[str] = None
    is_acknowledged: bool
    created_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Pydantic Schemas — Notifications
# ──────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: Optional[str] = None
    read_status: bool
    created_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  Pydantic Schemas — Audit
# ──────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: int
    batch_id: int
    actor_id: int
    action: str
    event_data: Optional[str] = None
    timestamp: datetime.datetime
    previous_hash: str
    current_hash: str

    model_config = {"from_attributes": True}


class AuditVerifyResponse(BaseModel):
    is_valid: bool
    total_records: int
    verified_records: int
    first_invalid_index: Optional[int] = None
    message: str


# ──────────────────────────────────────────────
#  Pydantic Schemas — Moderator AI
# ──────────────────────────────────────────────

class ModeratorAnalysis(BaseModel):
    risk_level: str = Field(description="LOW | MEDIUM | HIGH | CRITICAL")
    event_type: str = Field(description="EXPIRY | RETURN | DISCREPANCY | DELAY | REENTRY | DESTRUCTION | OTHER")
    analysis: str = Field(description="Concise technical risk explanation")
    recommended_action: str = Field(description="Clear operational next step")
    message: str = Field(description="Stakeholder notification prose")
    recipients: List[str] = Field(description="List of recipient roles")


# ──────────────────────────────────────────────
#  Pydantic Schemas — Dashboard Stats
# ──────────────────────────────────────────────

class DashboardStats(BaseModel):
    active_returns: int = 0
    pending_destruction: int = 0
    verified_destruction: int = 0
    critical_fraud_alerts: int = 0


# ──────────────────────────────────────────────
#  Pydantic Schemas — Medicines
# ──────────────────────────────────────────────

class MedicineCreateRequest(BaseModel):
    """Payload for MANUFACTURER to register a new drug batch."""
    # Required core pharmaceutical identifiers
    brand_name: str = Field(..., min_length=1, description="Proprietary/trade name")
    generic_name: str = Field(..., min_length=1, description="INN / generic drug name")
    strength: str = Field(..., min_length=1, description="e.g. '625mg', '500mg/5mL'")
    dosage_form: str = Field(..., min_length=1, description="e.g. 'Tablet', 'Capsule', 'Syrup'")

    # Required batch traceability fields
    batch_number: str = Field(..., min_length=1, description="Unique batch identifier (e.g. MFG-2026-001)")
    manufacturing_date: datetime.date = Field(..., description="Date of manufacture")
    expiry_date: datetime.date = Field(..., description="Expiry date — must be after manufacturing_date")
    quantity: int = Field(..., gt=0, description="Number of packs/units in batch")

    # Optional supplementary fields
    route_of_administration: Optional[str] = Field(None, description="e.g. 'Oral', 'Intravenous'")
    composition: Optional[str] = Field(None, description="Active ingredients list")
    pack_size: Optional[str] = Field(None, description="e.g. '10 tablets/blister'")
    storage_conditions: Optional[str] = Field(None, description="e.g. 'Store below 25°C'")
    mrp: Optional[float] = Field(None, gt=0, description="Maximum Retail Price (INR)")
    prescription_required: bool = Field(False, description="Rx-only or OTC")


class MedicineResponse(BaseModel):
    """Full medicine record including linked batches."""
    id: int
    name: str
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    route_of_administration: Optional[str] = None
    composition: Optional[str] = None
    pack_size: Optional[str] = None
    storage_conditions: Optional[str] = None
    mrp: Optional[float] = None
    prescription_required: bool = False
    manufacturing_date: Optional[datetime.date] = None
    manufacturer_id: int
    manufacturer_name: Optional[str] = None
    batches: List[BatchResponse] = []

    model_config = {"from_attributes": True}
