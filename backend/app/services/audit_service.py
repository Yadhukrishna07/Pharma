import hashlib
import json
import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.schemas import AuditLog, AuditVerifyResponse


GENESIS_HASH = "0" * 64


def _get_previous_hash(db: Session) -> str:
    """Fetch the current_hash of the last audit_log record, or genesis hash."""
    last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    if last:
        return last.current_hash
    return GENESIS_HASH


def _compute_hash(previous_hash: str, event_data_json: str, timestamp: str, actor_id: str) -> str:
    """SHA-256( previous_hash + event_data_json + timestamp + actor_id )"""
    raw = f"{previous_hash}{event_data_json}{timestamp}{actor_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_audit_entry(
    db: Session,
    batch_id: int,
    actor_id: int,
    action: str,
    event_data: Optional[dict] = None,
    timestamp: Optional[datetime.datetime] = None,
) -> AuditLog:
    """
    Create a tamper-evident audit log entry with SHA-256 hash chaining.
    Must be called inside the same DB transaction as the state mutation.
    """
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()
    event_data_json = json.dumps(event_data or {}, sort_keys=True, default=str)
    previous_hash = _get_previous_hash(db)
    current_hash = _compute_hash(
        previous_hash,
        event_data_json,
        str(timestamp),
        str(actor_id),
    )

    entry = AuditLog(
        batch_id=batch_id,
        actor_id=actor_id,
        action=action,
        event_data=event_data_json,
        timestamp=timestamp,
        previous_hash=previous_hash,
        current_hash=current_hash,
    )
    db.add(entry)
    return entry


def verify_audit_chain(db: Session) -> AuditVerifyResponse:
    """
    Recalculate hashes sequentially and flag any index where
    current_hash != expected_hash.
    """
    records: List[AuditLog] = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not records:
        return AuditVerifyResponse(
            is_valid=True,
            total_records=0,
            verified_records=0,
            message="No audit records to verify.",
        )

    previous_hash = GENESIS_HASH
    for idx, record in enumerate(records):
        expected_hash = _compute_hash(
            previous_hash,
            record.event_data or "{}",
            str(record.timestamp),
            str(record.actor_id),
        )
        if record.current_hash != expected_hash:
            return AuditVerifyResponse(
                is_valid=False,
                total_records=len(records),
                verified_records=idx,
                first_invalid_index=idx,
                message=f"Hash mismatch at audit record index {idx} (ID={record.id}). "
                        f"Expected {expected_hash}, found {record.current_hash}. "
                        "The audit chain has been tampered with.",
            )
        if record.previous_hash != previous_hash:
            return AuditVerifyResponse(
                is_valid=False,
                total_records=len(records),
                verified_records=idx,
                first_invalid_index=idx,
                message=f"Previous hash mismatch at audit record index {idx} (ID={record.id}). "
                        "Chain linking is broken.",
            )
        previous_hash = record.current_hash

    return AuditVerifyResponse(
        is_valid=True,
        total_records=len(records),
        verified_records=len(records),
        message=f"All {len(records)} audit records verified. Cryptographic chain is intact.",
    )
