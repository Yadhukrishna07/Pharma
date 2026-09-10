"""
Comprehensive Backend Audit Test Suite
Tests all 25 aspects of the PharmMedian backend.
"""

import sys
import os
import json
import uuid
import datetime
import requests
import psycopg2
from sqlalchemy.orm import Session

# Setup backend path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.config import settings
from app.models.schemas import (
    User, UserRole, Medicine, Batch, BatchStatus, WorkflowEvent,
    ReturnRequest, Handoff, Dispute, DisputeStatus, DestructionRecord,
    Certificate, ModeratorEvent, Alert, AlertSeverity, Notification,
    AuditLog,
)
from app.services.audit_service import verify_audit_chain, create_audit_entry
from app.moderator.risk_engine import calculate_risk
from app.moderator.agent import _call_gemini

BASE_URL = "http://127.0.0.1:8000"

# User credentials from seed
USERS = {
    "PHARMACY": ("medplus", "password123"),
    "PHARMACY_B": ("pharmacyb", "password123"),
    "DISTRIBUTOR": ("bluedart", "password123"),
    "MANUFACTURER": ("sunpharma", "password123"),
    "FACILITY": ("bioclean", "password123"),
    "REGULATOR": ("cdsco", "password123"),
}

tokens = {}
results = {}

def log_test(category, name, passed, details=""):
    if category not in results:
        results[category] = []
    results[category].append({
        "name": name,
        "passed": passed,
        "details": details,
    })
    status_str = "PASS" if passed else "FAIL"
    safe_details = details.encode("ascii", errors="replace").decode("ascii")
    safe_name = name.encode("ascii", errors="replace").decode("ascii")
    print(f"[{status_str}] {category} :: {safe_name} - {safe_details}")


def authenticate_all():
    print("\n=== AUTHENTICATING USERS ===")
    for role_key, (username, password) in USERS.items():
        resp = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            tokens[role_key] = token
            log_test("Auth", f"Login {role_key}", True, f"Token obtained for {username}")
        else:
            log_test("Auth", f"Login {role_key}", False, f"Status {resp.status_code}: {resp.text}")


def test_auth_and_rbac():
    print("\n=== TESTING AUTH & RBAC MATRIX ===")
    # 1. Invalid login
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "medplus", "password": "wrongpassword"})
    log_test("Auth", "Invalid Password", resp.status_code == 401, f"Status: {resp.status_code}")

    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "nonexistent", "password": "password123"})
    log_test("Auth", "Non-existent User", resp.status_code == 401, f"Status: {resp.status_code}")

    # 2. No token on protected endpoint
    resp = requests.get(f"{BASE_URL}/batches")
    log_test("RBAC", "No Token to /batches", resp.status_code == 401, f"Status: {resp.status_code}")

    # 3. Invalid / malformed token
    resp = requests.get(f"{BASE_URL}/batches", headers={"Authorization": "Bearer invalid.token.payload"})
    log_test("RBAC", "Malformed Token", resp.status_code == 401, f"Status: {resp.status_code}")

    # 4. Role authorization:
    # Regulator endpoint accessed by Pharmacy
    resp = requests.get(f"{BASE_URL}/audit", headers={"Authorization": f"Bearer {tokens['PHARMACY']}"})
    log_test("RBAC", "Pharmacy accessing /audit (Regulator only)", resp.status_code == 403, f"Status: {resp.status_code}")

    # Facility accessing /returns/ POST (Pharmacy only)
    resp = requests.post(f"{BASE_URL}/returns/", headers={"Authorization": f"Bearer {tokens['FACILITY']}"}, json={"batch_id": 1, "declared_quantity": 10, "distributor_id": 3})
    log_test("RBAC", "Facility creating return (Pharmacy only)", resp.status_code == 403, f"Status: {resp.status_code}")

    # Pharmacy accessing /destruction/schedule (Manufacturer only)
    resp = requests.post(f"{BASE_URL}/destruction/schedule", headers={"Authorization": f"Bearer {tokens['PHARMACY']}"}, json={"batch_id": 1, "facility_id": 5})
    log_test("RBAC", "Pharmacy scheduling destruction (Manufacturer only)", resp.status_code == 403, f"Status: {resp.status_code}")

    # Pharmacy accessing /certificates/1/verify (Regulator only)
    resp = requests.post(f"{BASE_URL}/certificates/1/verify", headers={"Authorization": f"Bearer {tokens['PHARMACY']}"})
    log_test("RBAC", "Pharmacy verifying certificate (Regulator only)", resp.status_code == 403, f"Status: {resp.status_code}")


def test_notification_idor():
    print("\n=== TESTING NOTIFICATION IDOR & PERMISSIONS ===")
    db = SessionLocal()
    try:
        # Create a notification for Regulator (User 6)
        reg_user = db.query(User).filter(User.role == UserRole.REGULATOR).first()
        notif = Notification(user_id=reg_user.id, title="Test Regulator Notif", message="Private message", read_status=False)
        db.add(notif)
        db.commit()
        db.refresh(notif)
        notif_id = notif.id

        # Medplus (Pharmacy, User 1) attempts to mark Regulator's notification as read
        resp = requests.post(f"{BASE_URL}/auth/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {tokens['PHARMACY']}"})
        # Check if medplus was able to mark it read
        db.refresh(notif)
        if resp.status_code == 200 and notif.read_status == True:
            log_test("Security", "Notification IDOR Protection", False, f"VULNERABILITY: Pharmacy user 1 was able to mark Regulator user {reg_user.id}'s notification {notif_id} as read!")
        else:
            log_test("Security", "Notification IDOR Protection", True, f"Status: {resp.status_code}")
    finally:
        db.close()


def test_complete_batch_workflow():
    print("\n=== TESTING COMPLETE BATCH LIFECYCLE (BATCH-001 / Fresh Batch) ===")
    db = SessionLocal()
    try:
        # Create a dedicated test batch to test full cycle cleanly
        med = db.query(Medicine).first()
        batch_num = f"AUDIT-{uuid.uuid4().hex[:6].upper()}"
        batch = Batch(
            batch_number=batch_num,
            medicine_id=med.id,
            quantity=100,
            expiry_date=datetime.date.today() - datetime.timedelta(days=5),
            current_status=BatchStatus.EXPIRED,
            current_location="MedPlus Central Indiranagar",
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        test_batch_id = batch.id
        print(f"Created Test Batch ID: {test_batch_id} ({batch_num})")

        # 1. Invalid State Transition Attempt: Try scheduling destruction directly on EXPIRED batch
        resp = requests.post(
            f"{BASE_URL}/destruction/schedule",
            headers={"Authorization": f"Bearer {tokens['MANUFACTURER']}"},
            json={"batch_id": test_batch_id, "facility_id": 5}
        )
        log_test("Workflow", "Invalid Transition Rejection (EXPIRED -> DESTRUCTION_SCHEDULED)", resp.status_code == 400, f"Status: {resp.status_code}, Body: {resp.text}")

        # 2. Return creation validation: declared_qty > batch.quantity
        resp = requests.post(
            f"{BASE_URL}/returns/",
            headers={"Authorization": f"Bearer {tokens['PHARMACY']}"},
            json={"batch_id": test_batch_id, "declared_quantity": 200, "distributor_id": 3}
        )
        log_test("Workflow", "Return Validation (Qty > Total)", resp.status_code == 400, f"Status: {resp.status_code}")

        # 3. Return creation validation: invalid distributor role
        resp = requests.post(
            f"{BASE_URL}/returns/",
            headers={"Authorization": f"Bearer {tokens['PHARMACY']}"},
            json={"batch_id": test_batch_id, "declared_quantity": 100, "distributor_id": 1} # User 1 is Pharmacy
        )
        log_test("Workflow", "Return Validation (Distributor Role Check)", resp.status_code == 400, f"Status: {resp.status_code}")

        # 4. Valid Return Creation: EXPIRED -> RETURN_REQUESTED
        resp = requests.post(
            f"{BASE_URL}/returns/",
            headers={"Authorization": f"Bearer {tokens['PHARMACY']}"},
            json={"batch_id": test_batch_id, "declared_quantity": 100, "distributor_id": 3}
        )
        return_id = resp.json().get("id") if resp.status_code == 200 else None
        log_test("Workflow", "Step 1: EXPIRED -> RETURN_REQUESTED", resp.status_code == 200 and return_id is not None, f"Return ID: {return_id}")

        # Test duplicate return request on same batch
        resp_dup = requests.post(
            f"{BASE_URL}/returns/",
            headers={"Authorization": f"Bearer {tokens['PHARMACY']}"},
            json={"batch_id": test_batch_id, "declared_quantity": 100, "distributor_id": 3}
        )
        log_test("Workflow", "Duplicate Return Request Rejection", resp_dup.status_code == 400, f"Status: {resp_dup.status_code}")

        # 5. Distributor confirms pickup: RETURN_REQUESTED -> PICKUP_CONFIRMED
        resp = requests.post(
            f"{BASE_URL}/returns/{return_id}/pickup",
            headers={"Authorization": f"Bearer {tokens['DISTRIBUTOR']}"}
        )
        log_test("Workflow", "Step 2: RETURN_REQUESTED -> PICKUP_CONFIRMED", resp.status_code == 200, f"Status: {resp.status_code}")

        # 6. Distributor receives with discrepancy (100 declared, 95 received): PICKUP_CONFIRMED -> RECEIVED_BY_DISTRIBUTOR -> DISPUTED
        resp = requests.post(
            f"{BASE_URL}/returns/{return_id}/receive",
            headers={"Authorization": f"Bearer {tokens['DISTRIBUTOR']}"},
            json={"batch_id": test_batch_id, "received_quantity": 95}
        )
        dispute_id = resp.json().get("dispute_id") if resp.status_code == 200 else None
        log_test("Workflow", "Step 3: Discrepancy & Dispute Creation (100 vs 95)", resp.status_code == 200 and dispute_id is not None, f"Dispute ID: {dispute_id}")

        # 7. Resolve Dispute: DISPUTED -> RECEIVED_BY_MANUFACTURER
        resp = requests.post(
            f"{BASE_URL}/disputes/{dispute_id}/resolve",
            headers={"Authorization": f"Bearer {tokens['DISTRIBUTOR']}"},
            json={"resolution_notes": "5 units damaged in transit. Settled."}
        )
        log_test("Workflow", "Step 4: Dispute Resolution -> RECEIVED_BY_MANUFACTURER", resp.status_code == 200, f"Status: {resp.status_code}")

        # 8. Manufacturer Receive acknowledge
        resp = requests.post(
            f"{BASE_URL}/manufacturer/receive",
            headers={"Authorization": f"Bearer {tokens['MANUFACTURER']}"},
            json={"batch_id": test_batch_id, "notes": "Received 95 intact units"}
        )
        log_test("Workflow", "Step 5: Manufacturer Receipt Confirmation", resp.status_code == 200, f"Status: {resp.status_code}")

        # 9. Schedule Destruction: RECEIVED_BY_MANUFACTURER -> DESTRUCTION_SCHEDULED
        facility_user = db.query(User).filter(User.role == UserRole.FACILITY).first()
        resp = requests.post(
            f"{BASE_URL}/destruction/schedule",
            headers={"Authorization": f"Bearer {tokens['MANUFACTURER']}"},
            json={"batch_id": test_batch_id, "facility_id": facility_user.id}
        )
        log_test("Workflow", "Step 6: Schedule Destruction -> DESTRUCTION_SCHEDULED", resp.status_code == 200, f"Status: {resp.status_code}")

        # 10. Record Destruction: DESTRUCTION_SCHEDULED -> DESTROYED
        resp = requests.post(
            f"{BASE_URL}/destruction/record",
            headers={"Authorization": f"Bearer {tokens['FACILITY']}"},
            json={"batch_id": test_batch_id, "quantity_destroyed": 95}
        )
        log_test("Workflow", "Step 7: Record Destruction -> DESTROYED", resp.status_code == 200, f"Status: {resp.status_code}")

        # 11. Generate Certificate (FACILITY)
        cert_num = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        resp = requests.post(
            f"{BASE_URL}/certificates",
            headers={"Authorization": f"Bearer {tokens['FACILITY']}"},
            json={"batch_id": test_batch_id, "certificate_number": cert_num, "quantity": 95}
        )
        cert_id = resp.json().get("id") if resp.status_code == 200 else None
        log_test("Workflow", "Step 8: Generate Certificate", resp.status_code == 200 and cert_id is not None, f"Cert ID: {cert_id}")

        # 12. Regulator Verify Certificate: DESTROYED -> CERTIFICATE_VERIFIED -> CLOSED
        resp = requests.post(
            f"{BASE_URL}/certificates/{cert_id}/verify",
            headers={"Authorization": f"Bearer {tokens['REGULATOR']}"}
        )
        log_test("Workflow", "Step 9: Regulator Verification -> CLOSED", resp.status_code == 200, f"Status: {resp.status_code}")

        # Verify final batch status in DB
        db.refresh(batch)
        current_st = batch.current_status.value if hasattr(batch.current_status, 'value') else batch.current_status
        log_test("Workflow", "Batch Final State in DB is CLOSED", current_st == "CLOSED", f"Final Status: {current_st}")

        # 13. Re-entry Fraud Scan on Destroyed/Closed Batch at Pharmacy B
        resp = requests.post(
            f"{BASE_URL}/batches/scan",
            headers={"Authorization": f"Bearer {tokens['PHARMACY_B']}"},
            json={"batch_number": batch_num, "location": "Pharmacy B Store #402"}
        )
        data = resp.json() if resp.status_code == 200 else {}
        fraud_det = data.get("fraud_detected", False)
        alert_str = data.get("alert", "")
        log_test("Fraud", "Re-entry Fraud Detected on Destroyed Batch", resp.status_code == 200 and fraud_det is True, f"Fraud Detected: {fraud_det}, Alert: {alert_str}")

        # Verify that scan did NOT revert batch state back to ACTIVE or anything else
        db.refresh(batch)
        current_st_after_scan = batch.current_status.value if hasattr(batch.current_status, 'value') else batch.current_status
        log_test("Fraud", "Authoritative State Unchanged After Fraud Scan", current_st_after_scan == "CLOSED", f"Status: {current_st_after_scan}")

        return test_batch_id, cert_id
    finally:
        db.close()


def test_hash_chain_and_tampering():
    print("\n=== TESTING SHA-256 HASH CHAIN INTEGRITY & TAMPER DETECTION ===")
    # 1. Verify clean chain
    resp = requests.post(f"{BASE_URL}/audit/verify", headers={"Authorization": f"Bearer {tokens['REGULATOR']}"})
    data = resp.json() if resp.status_code == 200 else {}
    is_valid = data.get("is_valid", False)
    log_test("HashChain", "Baseline Audit Hash Chain Verification", resp.status_code == 200 and is_valid is True, f"Verified records: {data.get('verified_records')}/{data.get('total_records')}")

    # 2. Simulate Tampering in DB
    db = SessionLocal()
    try:
        last_record = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        if last_record:
            original_data = last_record.event_data
            last_record.event_data = json.dumps({"tampered": "hacked_data"})
            db.commit()

            # Test verify with tampered data
            resp_tamper = requests.post(f"{BASE_URL}/audit/verify", headers={"Authorization": f"Bearer {tokens['REGULATOR']}"})
            tamper_data = resp_tamper.json()
            is_invalid = tamper_data.get("is_valid") == False
            log_test("HashChain", "Tamper Detection Flagging", is_invalid, f"Tamper detected correctly: {tamper_data.get('message')}")

            # Restore original data
            last_record.event_data = original_data
            db.commit()

            # Re-verify restored chain
            resp_restored = requests.post(f"{BASE_URL}/audit/verify", headers={"Authorization": f"Bearer {tokens['REGULATOR']}"})
            restored_valid = resp_restored.json().get("is_valid") == True
            log_test("HashChain", "Chain Integrity Restoration", restored_valid, "Restored successfully")
    finally:
        db.close()


def test_moderator_and_ai():
    print("\n=== TESTING MODERATOR AI & FALLBACK ===")
    # 1. Test google-genai direct call
    genai_result = _call_gemini(
        event_type="DISCREPANCY_DETECTED",
        batch_number="BATCH-001",
        current_status="DISPUTED",
        actor_role="DISTRIBUTOR",
        batch_history=[],
        event_data={"declared_qty": 100, "received_qty": 95},
    )
    has_api_key = bool(settings.GEMINI_API_KEY)
    print(f"Gemini API Key configured: {has_api_key} (Model: {settings.GEMINI_MODEL})")
    if has_api_key and genai_result is not None:
        log_test("ModeratorAI", "Gemini API Live Call & Pydantic Validation", True, f"Risk: {genai_result.get('risk_level')}, Analysis: {genai_result.get('analysis')[:60]}...")
    elif not has_api_key:
        log_test("ModeratorAI", "Gemini API Key Missing in Env", False, "GEMINI_API_KEY is not set in backend/.env")
    else:
        log_test("ModeratorAI", "Gemini API Call Failed", False, "Returned None on call")

    # 2. Test deterministic fallback engine
    fallback = calculate_risk(
        event_type="REENTRY_FRAUD_SCAN",
        event_data={"scan_location": "Pharmacy B"},
        batch_history=[],
    )
    log_test("ModeratorAI", "Deterministic Fallback Engine (REENTRY_FRAUD_SCAN)", fallback.get("risk_level") == "CRITICAL", f"Risk: {fallback.get('risk_level')}, Action: {fallback.get('recommended_action')[:50]}")

    # 3. Test Moderator Event Idempotency
    db = SessionLocal()
    try:
        from app.moderator.agent import run_moderator_analysis
        wf_event = db.query(WorkflowEvent).order_by(WorkflowEvent.id.desc()).first()
        if wf_event:
            count_before = db.query(ModeratorEvent).filter(ModeratorEvent.workflow_event_id == wf_event.id).count()
            # Run moderator analysis twice
            run_moderator_analysis(wf_event.id, wf_event.batch_id, wf_event.event_type, wf_event.actor_id)
            run_moderator_analysis(wf_event.id, wf_event.batch_id, wf_event.event_type, wf_event.actor_id)
            count_after = db.query(ModeratorEvent).filter(ModeratorEvent.workflow_event_id == wf_event.id).count()
            log_test("ModeratorAI", "Moderator Event Idempotency", count_after <= 1, f"Count for event {wf_event.id}: {count_after}")
    finally:
        db.close()


def test_missing_and_loose_ends():
    print("\n=== TESTING ROUTING, SCHEMAS & LOOSE ENDS ===")
    # 1. Check trailing slash handling on returns
    resp_no_slash = requests.get(f"{BASE_URL}/returns", headers={"Authorization": f"Bearer {tokens['PHARMACY']}"})
    # If 307 or 404 or 200
    log_test("API Routing", "GET /returns (without trailing slash)", resp_no_slash.status_code in [200, 307], f"Status: {resp_no_slash.status_code}")

    resp_slash = requests.get(f"{BASE_URL}/returns/", headers={"Authorization": f"Bearer {tokens['PHARMACY']}"})
    log_test("API Routing", "GET /returns/ (with trailing slash)", resp_slash.status_code == 200, f"Status: {resp_slash.status_code}")

    # 2. File / Certificate Upload endpoint
    resp_upload = requests.post(f"{BASE_URL}/certificates/upload", headers={"Authorization": f"Bearer {tokens['FACILITY']}"})
    log_test("File Upload", "Certificate Document Upload Endpoint Exists", resp_upload.status_code != 404, f"Status: {resp_upload.status_code} (404 means route does not exist)")

    # 3. Notification Count endpoint
    resp_count = requests.get(f"{BASE_URL}/auth/notifications/count", headers={"Authorization": f"Bearer {tokens['PHARMACY']}"})
    log_test("Notifications", "Notification Count Endpoint", resp_count.status_code == 200 and "count" in resp_count.json(), f"Status: {resp_count.status_code}, Body: {resp_count.text}")

    # 4. Dashboard stats endpoint
    resp_stats = requests.get(f"{BASE_URL}/dashboard/stats", headers={"Authorization": f"Bearer {tokens['REGULATOR']}"})
    log_test("Dashboard", "Regulator Dashboard Stats", resp_stats.status_code == 200, f"Stats: {resp_stats.json()}")


if __name__ == "__main__":
    authenticate_all()
    test_auth_and_rbac()
    test_notification_idor()
    test_complete_batch_workflow()
    test_hash_chain_and_tampering()
    test_moderator_and_ai()
    test_missing_and_loose_ends()
    print("\n=== SUMMARY OF RESULTS ===")
    print(json.dumps(results, indent=2))
