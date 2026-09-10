"""
Seed script for the PharmMedian demo dataset.
Creates one batch and all required user roles.

Usage:
    cd backend
    python seed.py
"""

import datetime
import sys
import os

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app.models.schemas import (
    User, UserRole, Medicine, Batch, BatchStatus, WorkflowEvent,
)
from app.auth import hash_password
from app.services.audit_service import create_audit_entry


def seed():
    """Create all tables and seed the demo dataset."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_user = db.query(User).first()
        if existing_user:
            print("Database already seeded. Skipping.")
            return

        # ── Users ──
        pharmacy1 = User(
            username="medplus",
            email="medplus@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.PHARMACY,
            organization_name="MedPlus Central Indiranagar",
        )
        pharmacy2 = User(
            username="pharmacyb",
            email="pharmacyb@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.PHARMACY,
            organization_name="Pharmacy B",
        )
        distributor = User(
            username="bluedart",
            email="bluedart@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.DISTRIBUTOR,
            organization_name="BlueDart Pharma Logistics",
        )
        manufacturer = User(
            username="sunpharma",
            email="sunpharma@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.MANUFACTURER,
            organization_name="Sun Pharma Laboratories",
        )
        facility = User(
            username="bioclean",
            email="bioclean@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.FACILITY,
            organization_name="BioClean Biomedical Waste Facility",
        )
        regulator = User(
            username="cdsco",
            email="cdsco@pharmamedian.com",
            hashed_password=hash_password("password123"),
            role=UserRole.REGULATOR,
            organization_name="CDSCO Regulator",
        )

        db.add_all([pharmacy1, pharmacy2, distributor, manufacturer, facility, regulator])
        db.flush()

        # ── Medicine ──
        medicine = Medicine(
            name="Augmentin Duo 625mg",
            manufacturer_id=manufacturer.id,
        )
        db.add(medicine)
        db.flush()

        # ── Batch ──
        batch = Batch(
            batch_number="BATCH-001",
            medicine_id=medicine.id,
            quantity=100,
            expiry_date=datetime.date(2026, 11, 9),
            current_status=BatchStatus.EXPIRED,
            current_location="MedPlus Central Indiranagar",
            reverse_chain_flag=False,
            destruction_status=None,
        )
        db.add(batch)
        db.flush()

        # ── Initial workflow event ──
        event = WorkflowEvent(
            batch_id=batch.id,
            actor_id=pharmacy1.id,
            event_type="BATCH_EXPIRED",
            from_status=BatchStatus.ACTIVE.value,
            to_status=BatchStatus.EXPIRED.value,
            data='{"reason": "Batch expired on shelf", "expiry_date": "2026-11-09"}',
            created_at=datetime.datetime.utcnow(),
        )
        db.add(event)
        db.flush()

        # ── Initial audit log entry ──
        create_audit_entry(
            db=db,
            batch_id=batch.id,
            actor_id=pharmacy1.id,
            action="BATCH_EXPIRED",
            event_data={
                "from_status": "ACTIVE",
                "to_status": "EXPIRED",
                "reason": "Batch expired on shelf",
            },
        )

        db.commit()
        print("=" * 60)
        print("  PharmMedian — Database Seeded Successfully!")
        print("=" * 60)
        print()
        print("  Users created:")
        print(f"    Pharmacy 1:    medplus / password123     (ID: {pharmacy1.id})")
        print(f"    Pharmacy 2:    pharmacyb / password123   (ID: {pharmacy2.id})")
        print(f"    Distributor:   bluedart / password123    (ID: {distributor.id})")
        print(f"    Manufacturer:  sunpharma / password123   (ID: {manufacturer.id})")
        print(f"    Facility:      bioclean / password123    (ID: {facility.id})")
        print(f"    Regulator:     cdsco / password123       (ID: {regulator.id})")
        print()
        print("  Batch created:")
        print(f"    BATCH-001 — Augmentin Duo 625mg")
        print(f"    Quantity: 100, Expiry: 2026-11-09, Status: EXPIRED")
        print()
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
