"""
Seed script for the PharmMedian demo dataset.
Creates the primary batch BATCH-001 and all required user roles.
Supports:
  python seed.py --fresh    -> Reset BATCH-001 to EXPIRED (ready for live step-by-step test)
  python seed.py --history  -> Populate complete realistic Day 1-11 lifecycle in PostgreSQL

Usage:
    cd backend
    python seed.py --fresh
    python seed.py --history
"""

import datetime
import json
import sys
import os
import argparse

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app.models.schemas import (
    User, UserRole, Medicine, Batch, BatchStatus, WorkflowEvent,
    ReturnRequest, Handoff, Dispute, DisputeStatus, DestructionRecord,
    Certificate, Alert, AlertSeverity, ModeratorEvent, AuditLog,
)
from app.auth import hash_password
from app.services.audit_service import create_audit_entry


def ensure_users_and_medicine(db):
    """Ensure standard roles and medicine exist."""
    users = {
        "medplus": User(
            username="medplus",
            email="medplus@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.PHARMACY,
            organization_name="MedPlus Central Indiranagar",
        ),
        "pharmacyb": User(
            username="pharmacyb",
            email="pharmacyb@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.PHARMACY,
            organization_name="Pharmacy B",
        ),
        "bluedart": User(
            username="bluedart",
            email="bluedart@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.DISTRIBUTOR,
            organization_name="BlueDart Pharma Logistics",
        ),
        "sunpharma": User(
            username="sunpharma",
            email="sunpharma@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.MANUFACTURER,
            organization_name="Sun Pharma Laboratories",
        ),
        "bioclean": User(
            username="bioclean",
            email="bioclean@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.FACILITY,
            organization_name="BioClean Biomedical Waste Facility",
        ),
        "cdsco": User(
            username="cdsco",
            email="cdsco@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.REGULATOR,
            organization_name="CDSCO Regulator",
        ),
    }

    user_map = {}
    for username, user_obj in users.items():
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            db.add(user_obj)
            db.flush()
            user_map[username] = user_obj
        else:
            user_map[username] = existing

    # Ensure Medicine exists
    med = db.query(Medicine).filter(Medicine.name == "Augmentin Duo 625mg").first()
    if not med:
        med = Medicine(
            name="Augmentin Duo 625mg",
            manufacturer_id=user_map["sunpharma"].id,
        )
        db.add(med)
        db.flush()

    # Ensure Batch exists
    batch = db.query(Batch).filter(Batch.batch_number == "BATCH-001").first()
    if not batch:
        batch = Batch(
            batch_number="BATCH-001",
            medicine_id=med.id,
            quantity=100,
            expiry_date=datetime.date(2026, 11, 9),
            current_status=BatchStatus.EXPIRED,
            current_location="MedPlus Central Indiranagar",
            reverse_chain_flag=False,
            destruction_status=None,
        )
        db.add(batch)
        db.flush()

    db.commit()
    return user_map, med, batch


def reset_batch_workflow(db, mode: str = "fresh"):
    """
    Cleanly reset BATCH-001 workflow.
    mode='fresh': Batch is EXPIRED at Pharmacy (ready for interactive testing)
    mode='history': Batch has Day 1-11 completed history with Day 11 re-entry fraud
    """
    user_map, med, batch = ensure_users_and_medicine(db)

    # 1. Clear existing related records and any stray test batches
    db.query(ModeratorEvent).delete()
    db.query(WorkflowEvent).delete()
    db.query(AuditLog).delete()
    db.query(Alert).delete()
    db.query(Dispute).delete()
    db.query(Handoff).delete()
    db.query(DestructionRecord).delete()
    db.query(Certificate).delete()
    db.query(ReturnRequest).delete()
    db.query(Batch).filter(Batch.batch_number != "BATCH-001").delete()
    db.commit()

    pharmacy = user_map["medplus"]
    pharmacy_b = user_map["pharmacyb"]
    distributor = user_map["bluedart"]
    manufacturer = user_map["sunpharma"]
    facility = user_map["bioclean"]
    regulator = user_map["cdsco"]

    now = datetime.datetime.utcnow()

    if mode == "fresh":
        # Reset batch status
        batch.current_status = BatchStatus.EXPIRED
        batch.quantity = 100
        batch.current_location = "MedPlus Central Indiranagar"
        batch.reverse_chain_flag = False
        batch.destruction_status = None
        db.commit()

        # Day 1 event
        event = WorkflowEvent(
            batch_id=batch.id,
            actor_id=pharmacy.id,
            event_type="BATCH_EXPIRED",
            from_status=BatchStatus.ACTIVE.value,
            to_status=BatchStatus.EXPIRED.value,
            data=json.dumps({"reason": "Batch expired on shelf", "quantity": 100, "expiry_date": "2026-11-09"}),
            created_at=now - datetime.timedelta(days=1),
        )
        db.add(event)
        create_audit_entry(
            db=db,
            batch_id=batch.id,
            actor_id=pharmacy.id,
            action="BATCH_EXPIRED",
            event_data={"from_status": "ACTIVE", "to_status": "EXPIRED", "reason": "Batch expired on shelf"},
            timestamp=now - datetime.timedelta(days=1),
        )
        db.commit()
        return {"status": "BATCH-001 reset to EXPIRED (100 packs) at MedPlus Central"}

    elif mode == "history":
        # Build complete Day 1 through Day 11 timeline
        t0 = now - datetime.timedelta(days=11)

        # Helper to step time
        def dt(day_offset, hour=10, minute=0):
            return t0 + datetime.timedelta(days=day_offset, hours=hour, minutes=minute)

        # Day 1: Expiry detected
        t_day1 = dt(1, 9, 30)
        e1 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=pharmacy.id,
            event_type="BATCH_EXPIRED",
            from_status=BatchStatus.ACTIVE.value,
            to_status=BatchStatus.EXPIRED.value,
            data=json.dumps({"reason": "Batch expired on shelf", "quantity": 100}),
            created_at=t_day1,
        )
        db.add(e1)
        db.flush()
        create_audit_entry(db, batch.id, pharmacy.id, "BATCH_EXPIRED", {"from_status": "ACTIVE", "to_status": "EXPIRED"}, timestamp=t_day1)

        # Day 2: Return requested (100 packs)
        t_day2 = dt(2, 10, 42)
        ret = ReturnRequest(
            batch_id=batch.id,
            declared_quantity=100,
            distributor_id=distributor.id,
            status="PICKED_UP",
            evidence_id="EV-SEED-001",
            evidence_url="/uploads/evidence/evidence_BATCH-001_demo.jpg",
        )
        db.add(ret)
        db.flush()
        e2 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=pharmacy.id,
            event_type="RETURN_REQUESTED",
            from_status=BatchStatus.EXPIRED.value,
            to_status=BatchStatus.RETURN_REQUESTED.value,
            data=json.dumps({"declared_quantity": 100, "distributor": distributor.organization_name}),
            created_at=t_day2,
        )
        db.add(e2)
        db.flush()
        create_audit_entry(db, batch.id, pharmacy.id, "RETURN_REQUESTED", {"declared_quantity": 100}, timestamp=t_day2)

        # Day 3: Pickup confirmed
        t_day3 = dt(3, 11, 15)
        e3 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=distributor.id,
            event_type="PICKUP_CONFIRMED",
            from_status=BatchStatus.RETURN_REQUESTED.value,
            to_status=BatchStatus.PICKUP_CONFIRMED.value,
            data=json.dumps({"picked_up_from": pharmacy.organization_name, "quantity": 100}),
            created_at=t_day3,
        )
        db.add(e3)
        db.flush()
        create_audit_entry(db, batch.id, distributor.id, "PICKUP_CONFIRMED", {"carrier": "BlueDart Pharma Logistics"}, timestamp=t_day3)

        # Day 4: Distributor received (95 packs) + Quantity discrepancy detected
        t_day4 = dt(4, 12, 8)
        ret.status = "DISPUTED"
        e4 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=distributor.id,
            event_type="RECEIVED_BY_DISTRIBUTOR",
            from_status=BatchStatus.PICKUP_CONFIRMED.value,
            to_status=BatchStatus.RECEIVED_BY_DISTRIBUTOR.value,
            data=json.dumps({"declared_qty": 100, "received_qty": 95}),
            created_at=t_day4,
        )
        db.add(e4)
        db.flush()
        create_audit_entry(db, batch.id, distributor.id, "RECEIVED_BY_DISTRIBUTOR", {"declared_qty": 100, "received_qty": 95}, timestamp=t_day4)

        t_day4_b = dt(4, 12, 10)
        e4_b = WorkflowEvent(
            batch_id=batch.id,
            actor_id=distributor.id,
            event_type="DISCREPANCY_DETECTED",
            from_status=BatchStatus.RECEIVED_BY_DISTRIBUTOR.value,
            to_status=BatchStatus.DISPUTED.value,
            data=json.dumps({"declared_qty": 100, "received_qty": 95, "discrepancy": 5}),
            created_at=t_day4_b,
        )
        db.add(e4_b)
        db.flush()
        create_audit_entry(db, batch.id, distributor.id, "DISCREPANCY_DETECTED", {"variance": -5}, timestamp=t_day4_b)

        # Dispute record & Alert & AI Moderator Event
        dispute = Dispute(
            batch_id=batch.id,
            declared_qty=100,
            received_qty=95,
            status=DisputeStatus.RESOLVED,
            resolution_notes="Discrepancy verified: 5 units damaged in transit and discarded per SOP.",
        )
        db.add(dispute)
        db.flush()

        alert1 = Alert(
            batch_id=batch.id,
            severity=AlertSeverity.HIGH,
            title="Quantity Discrepancy Detected",
            description="Declared: 100, Received: 95. Discrepancy of 5 units.",
            is_acknowledged=True,
            created_at=t_day4_b,
        )
        db.add(alert1)
        db.flush()

        mod1 = ModeratorEvent(
            workflow_event_id=e4_b.id,
            batch_id=batch.id,
            risk_level="HIGH",
            analysis="Quantity discrepancy detected: 100 declared vs 95 received at distributor intake.",
            recommended_action="Inspect physical seal and verify transit damage report.",
            message="Quantity discrepancy detected: 100 declared vs 95 received.",
        )
        db.add(mod1)
        db.flush()

        # Day 5: Dispute resolved
        t_day5 = dt(5, 14, 0)
        e5 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=distributor.id,
            event_type="DISPUTE_RESOLVED",
            from_status=BatchStatus.DISPUTED.value,
            to_status=BatchStatus.RECEIVED_BY_MANUFACTURER.value,
            data=json.dumps({
                "dispute_id": dispute.id,
                "declared_qty": 100,
                "received_qty": 95,
                "resolution_notes": dispute.resolution_notes,
            }),
            created_at=t_day5,
        )
        db.add(e5)
        db.flush()
        create_audit_entry(db, batch.id, distributor.id, "DISPUTE_RESOLVED", {"resolution": dispute.resolution_notes}, timestamp=t_day5)

        # Day 6: Manufacturer received 95 packs
        t_day6 = dt(6, 13, 20)
        e6 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=manufacturer.id,
            event_type="MANUFACTURER_RECEIVED",
            from_status=BatchStatus.RECEIVED_BY_MANUFACTURER.value,
            to_status=BatchStatus.RECEIVED_BY_MANUFACTURER.value,
            data=json.dumps({"quantity": 95, "warehouse": "Sun Pharma Quarantine Bay 4"}),
            created_at=t_day6,
        )
        db.add(e6)
        db.flush()
        create_audit_entry(db, batch.id, manufacturer.id, "MANUFACTURER_RECEIVED", {"quantity": 95}, timestamp=t_day6)

        # Day 7: Destruction scheduled
        t_day7 = dt(7, 10, 15)
        e7 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=manufacturer.id,
            event_type="DESTRUCTION_SCHEDULED",
            from_status=BatchStatus.RECEIVED_BY_MANUFACTURER.value,
            to_status=BatchStatus.DESTRUCTION_SCHEDULED.value,
            data=json.dumps({"facility_name": facility.organization_name, "quantity": 95}),
            created_at=t_day7,
        )
        db.add(e7)
        db.flush()
        create_audit_entry(db, batch.id, manufacturer.id, "DESTRUCTION_SCHEDULED", {"facility": facility.organization_name}, timestamp=t_day7)

        # Day 8: 95 packs destroyed
        t_day8 = dt(8, 15, 5)
        dest_rec = DestructionRecord(
            batch_id=batch.id,
            facility_id=facility.id,
            quantity_destroyed=95,
            timestamp=t_day8,
        )
        db.add(dest_rec)
        db.flush()

        e8 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=facility.id,
            event_type="DESTRUCTION_RECORDED",
            from_status=BatchStatus.DESTRUCTION_SCHEDULED.value,
            to_status=BatchStatus.DESTROYED.value,
            data=json.dumps({"quantity_destroyed": 95, "method": "High-temperature incineration 1100°C"}),
            created_at=t_day8,
        )
        db.add(e8)
        db.flush()
        create_audit_entry(db, batch.id, facility.id, "DESTRUCTION_RECORDED", {"quantity": 95}, timestamp=t_day8)

        mod2 = ModeratorEvent(
            workflow_event_id=e8.id,
            batch_id=batch.id,
            risk_level="LOW",
            analysis="Thermal oxidation complete. Physical batch destroyed per CPCB biomedical guidelines.",
            recommended_action="Await formal certificate upload and CDSCO verification.",
            message="Batch destruction verified. Compliance closure is pending certificate verification.",
        )
        db.add(mod2)
        db.flush()

        # Day 9: Certificate uploaded
        t_day9 = dt(9, 11, 0)
        cert = Certificate(
            certificate_number="CERT-884921",
            batch_id=batch.id,
            facility_id=facility.id,
            quantity=95,
            issued_date=t_day9.date(),
            is_verified=True,
        )
        db.add(cert)
        db.flush()

        # Day 10: Certificate verified & Compliance CLOSED
        t_day10_a = dt(10, 16, 2)
        e10_a = WorkflowEvent(
            batch_id=batch.id,
            actor_id=regulator.id,
            event_type="CERTIFICATE_VERIFIED",
            from_status=BatchStatus.DESTROYED.value,
            to_status=BatchStatus.CERTIFICATE_VERIFIED.value,
            data=json.dumps({"certificate_number": "CERT-884921", "quantity": 95}),
            created_at=t_day10_a,
        )
        db.add(e10_a)
        db.flush()
        create_audit_entry(db, batch.id, regulator.id, "CERTIFICATE_VERIFIED", {"certificate_number": "CERT-884921"}, timestamp=t_day10_a)

        t_day10_b = dt(10, 16, 5)
        e10_b = WorkflowEvent(
            batch_id=batch.id,
            actor_id=regulator.id,
            event_type="BATCH_CLOSED",
            from_status=BatchStatus.CERTIFICATE_VERIFIED.value,
            to_status=BatchStatus.CLOSED.value,
            data=json.dumps({"certificate_number": "CERT-884921", "verified_by": "CDSCO Regulator"}),
            created_at=t_day10_b,
        )
        db.add(e10_b)
        db.flush()
        create_audit_entry(db, batch.id, regulator.id, "BATCH_CLOSED", {"compliance": "CLOSED"}, timestamp=t_day10_b)

        # Update batch state to CLOSED
        batch.current_status = BatchStatus.CLOSED
        batch.quantity = 95
        batch.destruction_status = "DESTROYED"
        batch.current_location = "Closed — Regulatory Verified"
        batch.reverse_chain_flag = True
        db.commit()

        # Day 11: Pharmacy B scans BATCH-001 -> CRITICAL RE-ENTRY
        t_day11 = dt(11, 16, 30)
        alert_reentry = Alert(
            batch_id=batch.id,
            severity=AlertSeverity.CRITICAL,
            title="REENTRY_FRAUD_EVENT",
            description="CRITICAL: Re-entry fraud detected for batch BATCH-001. Batch status is CLOSED / DESTROYED but was scanned at location: Pharmacy B.",
            is_acknowledged=False,
            created_at=t_day11,
        )
        db.add(alert_reentry)
        db.flush()

        e11 = WorkflowEvent(
            batch_id=batch.id,
            actor_id=pharmacy_b.id,
            event_type="REENTRY_FRAUD_SCAN",
            from_status=BatchStatus.CLOSED.value,
            to_status=BatchStatus.CLOSED.value,
            data=json.dumps({
                "scan_location": "Pharmacy B",
                "fraud_type": "REENTRY_FRAUD_EVENT",
                "batch_current_status": "CLOSED",
                "batch_destruction_status": "DESTROYED",
            }),
            created_at=t_day11,
        )
        db.add(e11)
        db.flush()
        create_audit_entry(
            db, batch.id, pharmacy_b.id, "REENTRY_FRAUD_SCAN",
            {"scan_location": "Pharmacy B", "fraud_type": "REENTRY_FRAUD_EVENT"},
            timestamp=t_day11
        )

        mod3 = ModeratorEvent(
            workflow_event_id=e11.id,
            batch_id=batch.id,
            risk_level="CRITICAL",
            analysis="Previously destroyed and closed BATCH-001 scanned at Pharmacy B shelf. High probability of counterfeit duplication or diverted stock.",
            recommended_action="Quarantine physical package immediately. Dispatch CDSCO state enforcement inspector.",
            message="CRITICAL: Previously destroyed BATCH-001 detected at another pharmacy.",
        )
        db.add(mod3)
        db.commit()

        return {"status": "BATCH-001 populated with Day 1-11 realistic operational history and Day 11 re-entry scan!"}


def seed():
    """Main seed entrypoint."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--fresh", action="store_true", help="Seed with fresh EXPIRED batch")
        parser.add_argument("--history", action="store_true", help="Seed with full Day 1-11 history")
        args, _ = parser.parse_known_args()

        if args.history:
            res = reset_batch_workflow(db, mode="history")
            print(f"[OK] Seeded in HISTORY mode: {res}")
        else:
            res = reset_batch_workflow(db, mode="fresh")
            print(f"[OK] Seeded in FRESH mode: {res}")

    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
