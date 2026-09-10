import requests
import json
import time
import os
import sys

BASE_URL = "http://127.0.0.1:8000"

def reset_db():
    print("Resetting database for fresh test run...")
    from app.database import engine, SessionLocal, Base
    from app.models.schemas import (
        User, UserRole, Medicine, Batch, BatchStatus, WorkflowEvent,
    )
    from app.auth import hash_password
    from app.services.audit_service import create_audit_entry

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
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
        organization_name="BioClean Waste Facility",
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

    medicine = Medicine(
        name="Augmentin Duo 625mg",
        manufacturer_id=manufacturer.id,
    )
    db.add(medicine)
    db.flush()

    batch = Batch(
        batch_number="BATCH-001",
        medicine_id=medicine.id,
        quantity=100,
        expiry_date=time.strftime("%Y-%m-%d"),
        current_status=BatchStatus.EXPIRED,
        current_location="MedPlus Central Indiranagar",
        reverse_chain_flag=False,
        destruction_status=None,
    )
    db.add(batch)
    db.flush()

    event = WorkflowEvent(
        batch_id=batch.id,
        actor_id=pharmacy1.id,
        event_type="BATCH_EXPIRED",
        from_status=BatchStatus.ACTIVE.value,
        to_status=BatchStatus.EXPIRED.value,
        data='{"reason": "Batch expired on shelf"}',
    )
    db.add(event)
    db.flush()

    create_audit_entry(
        db=db,
        batch_id=batch.id,
        actor_id=pharmacy1.id,
        action="BATCH_EXPIRED",
        event_data={"from_status": "ACTIVE", "to_status": "EXPIRED"},
    )
    db.commit()
    db.close()
    print("[OK] Database reset and seeded.")

def run_tests():
    reset_db()
    print("==================================================")
    print(" Starting E2E Verification Tests for Pharmamedian")
    print("==================================================")

    # 1. Login as Pharmacy
    print("\n1. Testing Login as Pharmacy (medplus)...")
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": "medplus", "password": "password123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    pharmacy_token = res.json()["access_token"]
    pharmacy_headers = {"Authorization": f"Bearer {pharmacy_token}"}
    print("[OK] Pharmacy login successful!")

    # 2. Get BATCH-001 ID
    res = requests.get(f"{BASE_URL}/batches/", headers=pharmacy_headers)
    assert res.status_code == 200
    batches = res.json()
    batch_1 = [b for b in batches if b["batch_number"] == "BATCH-001"][0]
    batch_id = batch_1["id"]
    print(f"[OK] Found BATCH-001 (ID: {batch_id}, Current Status: {batch_1['current_status']})")

    # Get Distributor ID
    res = requests.post(f"{BASE_URL}/auth/switch-role", json={"role": "DISTRIBUTOR"})
    distributor_id = res.json()["user"]["id"]
    distributor_token = res.json()["access_token"]
    distributor_headers = {"Authorization": f"Bearer {distributor_token}"}

    # Get Manufacturer ID
    res = requests.post(f"{BASE_URL}/auth/switch-role", json={"role": "MANUFACTURER"})
    manufacturer_token = res.json()["access_token"]
    manufacturer_headers = {"Authorization": f"Bearer {manufacturer_token}"}

    # Get Facility ID
    res = requests.post(f"{BASE_URL}/auth/switch-role", json={"role": "FACILITY"})
    facility_id = res.json()["user"]["id"]
    facility_token = res.json()["access_token"]
    facility_headers = {"Authorization": f"Bearer {facility_token}"}

    # Get Regulator Token
    res = requests.post(f"{BASE_URL}/auth/switch-role", json={"role": "REGULATOR"})
    regulator_token = res.json()["access_token"]
    regulator_headers = {"Authorization": f"Bearer {regulator_token}"}

    # 3. Create Return Request (EXPIRED -> RETURN_REQUESTED)
    print("\n2. Creating Return Request (Declared Qty: 100)...")
    res = requests.post(
        f"{BASE_URL}/returns/",
        json={"batch_id": batch_id, "declared_quantity": 100, "distributor_id": distributor_id},
        headers=pharmacy_headers
    )
    assert res.status_code == 200, f"Return failed: {res.text}"
    return_id = res.json()["id"]
    print(f"[OK] Return request created (ID: {return_id})")

    # 4. Confirm Pickup (RETURN_REQUESTED -> PICKUP_CONFIRMED)
    print("\n3. Confirming Pickup by Distributor...")
    res = requests.post(
        f"{BASE_URL}/returns/{return_id}/pickup",
        headers=distributor_headers
    )
    assert res.status_code == 200, f"Pickup failed: {res.text}"
    print("[OK] Pickup confirmed!")

    # 5. Receive Return with discrepancy (95 received vs 100 declared -> DISPUTED)
    print("\n4. Receiving Return with Discrepancy (Received: 95 vs Declared: 100)...")
    res = requests.post(
        f"{BASE_URL}/returns/{return_id}/receive",
        json={"batch_id": batch_id, "received_quantity": 95},
        headers=distributor_headers
    )
    assert res.status_code == 200, f"Receive failed: {res.text}"
    res_data = res.json()
    assert res_data["status"] == "disputed"
    dispute_id = res_data["dispute_id"]
    print(f"[OK] Quantity discrepancy detected -> State set to DISPUTED (Dispute ID: {dispute_id})")

    # 6. Verify Handoff fails while DISPUTED
    print("\n5. Verifying Manufacturer Handoff is blocked while DISPUTED...")
    res = requests.post(
        f"{BASE_URL}/destruction/handoff",
        json={"batch_id": batch_id, "from_role": "DISTRIBUTOR", "to_role": "MANUFACTURER", "received_quantity": 95},
        headers=manufacturer_headers
    )
    assert res.status_code == 400, f"Expected 400 error, got {res.status_code}: {res.text}"
    print("[OK] Manufacturer handoff correctly blocked during open dispute!")

    # 7. Resolve Dispute (DISPUTED -> RECEIVED_BY_MANUFACTURER)
    print("\n6. Resolving Dispute...")
    res = requests.post(
        f"{BASE_URL}/disputes/{dispute_id}/resolve",
        json={"resolution_notes": "Distributor and Pharmacy verified 5 units damaged in transit."},
        headers=distributor_headers
    )
    assert res.status_code == 200, f"Resolve failed: {res.text}"
    print("[OK] Dispute resolved! Batch transitioned to RECEIVED_BY_MANUFACTURER")

    # 8. Schedule Destruction (RECEIVED_BY_MANUFACTURER -> DESTRUCTION_SCHEDULED)
    print("\n7. Scheduling Destruction...")
    res = requests.post(
        f"{BASE_URL}/destruction/schedule",
        json={"batch_id": batch_id, "facility_id": facility_id},
        headers=manufacturer_headers
    )
    assert res.status_code == 200, f"Schedule failed: {res.text}"
    print("[OK] Destruction scheduled at BioClean Waste Facility!")

    # 9. Record Destruction (DESTRUCTION_SCHEDULED -> DESTROYED)
    print("\n8. Recording Destruction at Facility...")
    res = requests.post(
        f"{BASE_URL}/destruction/record",
        json={"batch_id": batch_id, "quantity_destroyed": 95},
        headers=facility_headers
    )
    assert res.status_code == 200, f"Record destruction failed: {res.text}"
    print("[OK] Destruction recorded -> Batch state set to DESTROYED")

    # 10. Create Certificate
    print("\n9. Issuing Destruction Certificate...")
    cert_num = f"CERT-2026-{int(time.time())}"
    res = requests.post(
        f"{BASE_URL}/certificates/",
        json={"certificate_number": cert_num, "batch_id": batch_id, "quantity": 95},
        headers=facility_headers
    )
    assert res.status_code == 200, f"Create cert failed: {res.text}"
    cert_id = res.json()["id"]
    print(f"[OK] Destruction Certificate issued (ID: {cert_id}, Cert No: {cert_num})")

    # 11. Verify Certificate by Regulator (DESTROYED -> CERTIFICATE_VERIFIED -> CLOSED)
    print("\n10. Regulator Verifying Certificate & Closing Lifecycle...")
    res = requests.post(
        f"{BASE_URL}/certificates/{cert_id}/verify",
        headers=regulator_headers
    )
    assert res.status_code == 200, f"Verify cert failed: {res.text}"
    assert res.json()["batch_status"] == "CLOSED"
    print("[OK] Certificate verified! Batch state set to CLOSED")

    # 12. Test Re-entry Fraud Scan (Scanning CLOSED batch at Pharmacy B)
    print("\n11. Testing Re-entry Fraud Scan at Pharmacy B...")
    res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "pharmacyb", "password": "password123"}
    )
    pharmacy_b_token = res.json()["access_token"]
    pharmacy_b_headers = {"Authorization": f"Bearer {pharmacy_b_token}"}

    res = requests.post(
        f"{BASE_URL}/batches/scan",
        json={"batch_number": "BATCH-001", "location": "Pharmacy B Downtown"},
        headers=pharmacy_b_headers
    )
    assert res.status_code == 200, f"Scan failed: {res.text}"
    scan_data = res.json()
    assert scan_data["fraud_detected"] == True, f"Fraud not detected! {scan_data}"
    print("[OK] CRITICAL REENTRY_FRAUD_EVENT successfully detected and logged!")
    print(f"   Alert text: {scan_data['alert']}")

    # 13. Verify Audit Chain Integrity
    print("\n12. Verifying SHA-256 Audit Chain Integrity...")
    res = requests.post(f"{BASE_URL}/audit/verify", headers=regulator_headers)
    assert res.status_code == 200, f"Audit verify request failed with {res.status_code}: {res.text}"
    audit_data = res.json()
    assert audit_data["is_valid"] == True, f"Audit chain invalid: {audit_data}"
    print(f"[OK] Audit chain verification PASSED! Total records verified: {audit_data['verified_records']}")

    # 14. Verify Notifications
    print("\n13. Checking Notifications for Regulator...")
    res = requests.get(f"{BASE_URL}/auth/notifications", headers=regulator_headers)
    assert res.status_code == 200
    notifs = res.json()
    print(f"[OK] Regulator received {len(notifs)} real DB notifications.")

    print("\n==================================================")
    print(" ALL E2E VERIFICATION TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
