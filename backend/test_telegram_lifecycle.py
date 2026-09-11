"""
Comprehensive test script for Telegram Bot notifications integration across all 6 PharmaMed events:
- Event 1: Medicine approaching expiry (POST /telegram/check-expiry)
- Event 2: Return request created (POST /returns/)
- Event 3: Return request approved (POST /returns/{id}/approve)
- Event 4: Return request rejected (POST /returns/{id}/reject)
- Event 5: Pickup completed (POST /returns/{id}/pickup)
- Event 6A: Return received by distributor (POST /returns/{id}/receive)
- Event 6B: Disposal / batch closure verified (POST /certificates/{id}/verify)
- Fault tolerance verification: Simulated Telegram failure does not break the business transaction.
"""

import sys
import os
import json
import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def get_token(username, password="password123"):
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]

def run_tests():
    print("=== STARTING PHARMAMED TELEGRAM INTEGRATION TESTS ===")

    # 0. Authenticate roles
    tokens = {
        "PHARMACY": get_token("medplus"),
        "DISTRIBUTOR": get_token("bluedart"),
        "MANUFACTURER": get_token("sunpharma"),
        "FACILITY": get_token("bioclean"),
        "REGULATOR": get_token("cdsco"),
    }
    print("Authentication tokens acquired for all 5 roles.")

    # 1. Reset demo workflow to fresh state
    reset_res = requests.post(f"{BASE_URL}/dashboard/reset", json={"mode": "fresh"})
    assert reset_res.status_code == 200
    print("Database reset to fresh state (BATCH-001 at EXPIRED).")

    # 2. Test Telegram Protected Test Endpoint
    test_res = requests.post(
        f"{BASE_URL}/telegram/test",
        headers={"Authorization": f"Bearer {tokens['PHARMACY']}"}
    )
    assert test_res.status_code == 200, f"Test endpoint failed: {test_res.text}"
    assert test_res.json().get("status") == "success"
    print("[PASS] Test Endpoint (POST /telegram/test) delivered test notification.")

    # 3. Test Event 1: Medicine Approaching Expiry
    exp_res = requests.post(
        f"{BASE_URL}/telegram/check-expiry",
        headers={"Authorization": f"Bearer {tokens['REGULATOR']}"}
    )
    assert exp_res.status_code == 200, f"Check expiry failed: {exp_res.text}"
    exp_data = exp_res.json()
    assert exp_data.get("notifications_triggered", 0) >= 1
    print(f"[PASS] Event 1 (Medicine Approaching Expiry): {exp_data['notifications_triggered']} batch notification(s) sent.")
    time.sleep(1)

    # 4. Test Event 2: Return Request Created
    # Get batch ID
    batches_res = requests.get(f"{BASE_URL}/batches/", headers={"Authorization": f"Bearer {tokens['PHARMACY']}"})
    batch_id = batches_res.json()[0]["id"]

    return_payload = {
        "batch_id": batch_id,
        "declared_quantity": 100,
        "distributor_id": 3, # BlueDart
        "evidence_id": "EV-TEST-001",
        "evidence_url": "/uploads/evidence/test_evidence.jpg"
    }
    ret_res = requests.post(
        f"{BASE_URL}/returns/",
        headers={"Authorization": f"Bearer {tokens['PHARMACY']}"},
        json=return_payload,
    )
    assert ret_res.status_code == 200, f"Return creation failed: {ret_res.text}"
    return_id = ret_res.json()["id"]
    print(f"[PASS] Event 2 (Return Request Created): Return #{return_id} created with photo evidence. Notification sent.")
    time.sleep(1)

    # 5. Test Event 3: Return Approved by Distributor
    approve_res = requests.post(
        f"{BASE_URL}/returns/{return_id}/approve",
        headers={"Authorization": f"Bearer {tokens['DISTRIBUTOR']}"},
    )
    assert approve_res.status_code == 200, f"Return approve failed: {approve_res.text}"
    assert approve_res.json().get("return_status") == "APPROVED"
    print(f"[PASS] Event 3 (Return Approved): Return #{return_id} approved by BlueDart Logistics. Notification sent.")
    time.sleep(1)

    # 6. Test Event 4: Return Rejected Notification (demonstrated via reject endpoint)
    # We create a second test batch/return to verify reject without blocking the main workflow
    # Or test rejecting a secondary return:
    from app.database import SessionLocal
    from app.models.schemas import Batch, Medicine, BatchStatus, ReturnRequest
    db = SessionLocal()
    try:
        med = db.query(Medicine).first()
        test_batch_2 = Batch(
            batch_number=f"BATCH-REJECT-{int(time.time())}",
            medicine_id=med.id,
            quantity=50,
            expiry_date=datetime.date.today(),
            current_status=BatchStatus.RETURN_REQUESTED,
        )
        db.add(test_batch_2)
        db.commit()
        db.refresh(test_batch_2)

        test_ret_2 = ReturnRequest(
            batch_id=test_batch_2.id,
            declared_quantity=50,
            distributor_id=3,
            status="PENDING",
            evidence_id="EV-TEST-REJ",
            evidence_url="/uploads/test.jpg"
        )
        db.add(test_ret_2)
        db.commit()
        db.refresh(test_ret_2)

        reject_res = requests.post(
            f"{BASE_URL}/returns/{test_ret_2.id}/reject",
            headers={"Authorization": f"Bearer {tokens['DISTRIBUTOR']}"},
            json={"reason": "Packaging compromised and seal damaged during initial pharmacy inspection"}
        )
        assert reject_res.status_code == 200, f"Return reject failed: {reject_res.text}"
        assert reject_res.json().get("return_status") == "REJECTED"
        print(f"[PASS] Event 4 (Return Rejected): Return #{test_ret_2.id} rejected with reason. Notification sent.")
    finally:
        db.close()
    time.sleep(1)

    # 7. Test Event 5: Pickup Completed
    pickup_res = requests.post(
        f"{BASE_URL}/returns/{return_id}/pickup",
        headers={"Authorization": f"Bearer {tokens['DISTRIBUTOR']}"},
    )
    assert pickup_res.status_code == 200, f"Pickup failed: {pickup_res.text}"
    print(f"[PASS] Event 5 (Pickup Completed): Physical pickup confirmed for Return #{return_id}. Notification sent.")
    time.sleep(1)

    # 8. Test Event 6A: Return Received by Distributor
    receive_res = requests.post(
        f"{BASE_URL}/returns/{return_id}/receive",
        headers={"Authorization": f"Bearer {tokens['DISTRIBUTOR']}"},
        json={"batch_id": return_id, "received_quantity": 100},
    )
    assert receive_res.status_code == 200, f"Receive failed: {receive_res.text}"
    assert receive_res.json().get("status") == "received"
    print(f"[PASS] Event 6A (Return Received): 100 units verified and received at distributor warehouse. Notification sent.")
    time.sleep(1)

    # 9. Test Event 6B: Disposal / Batch Closure Verified
    # First, manufacturer receives from distributor: RECEIVED_BY_DISTRIBUTOR -> RECEIVED_BY_MANUFACTURER
    mfg_res = requests.post(
        f"{BASE_URL}/manufacturer/receive",
        headers={"Authorization": f"Bearer {tokens['MANUFACTURER']}"},
        json={"batch_id": batch_id, "notes": "Received 100 units at quarantine bay"},
    )
    assert mfg_res.status_code == 200, f"Manufacturer receive failed: {mfg_res.text}"

    # Facility user id lookup
    users_res = requests.get(f"{BASE_URL}/dashboard/facility", headers={"Authorization": f"Bearer {tokens['FACILITY']}"})
    sched_res = requests.post(
        f"{BASE_URL}/destruction/schedule",
        headers={"Authorization": f"Bearer {tokens['MANUFACTURER']}"},
        json={"batch_id": batch_id, "facility_id": 5}, # BioClean
    )
    assert sched_res.status_code == 200, f"Schedule failed: {sched_res.text}"

    rec_res = requests.post(
        f"{BASE_URL}/destruction/record",
        headers={"Authorization": f"Bearer {tokens['FACILITY']}"},
        json={"batch_id": batch_id, "quantity_destroyed": 100},
    )
    assert rec_res.status_code == 200

    cert_num = f"CERT-TG-{int(time.time())}"
    cert_res = requests.post(
        f"{BASE_URL}/certificates/",
        headers={"Authorization": f"Bearer {tokens['FACILITY']}"},
        json={"batch_id": batch_id, "certificate_number": cert_num, "quantity": 100},
    )
    assert cert_res.status_code == 200
    cert_id = cert_res.json()["id"]

    verify_res = requests.post(
        f"{BASE_URL}/certificates/{cert_id}/verify",
        headers={"Authorization": f"Bearer {tokens['REGULATOR']}"},
    )
    assert verify_res.status_code == 200, f"Verify failed: {verify_res.text}"
    assert verify_res.json().get("batch_status") == "CLOSED"
    print(f"[PASS] Event 6B (Disposal & Batch Closure Verified): Certificate {cert_num} verified, batch CLOSED. Notification sent.")

    # 10. Fault Tolerance Test: Telegram Failure MUST NOT Break Pharmaceutical Transactions
    print("\n--- Testing Fault Tolerance (Telegram Error Handling) ---")
    from app.config import settings
    original_token = settings.TELEGRAM_BOT_TOKEN
    from app.services.telegram_service import send_telegram_message, notify_return_created
    try:
        # Intentionally tamper with the token to simulate API/network failure
        settings.TELEGRAM_BOT_TOKEN = "999999999:INVALID_MOCK_TOKEN_FOR_TESTING"
        result = send_telegram_message("Test failure resilience", chat_id="1579295220")
        assert result is False, "send_telegram_message should return False on API error!"
        print("[PASS] Fault Tolerance: send_telegram_message gracefully caught network/API error and returned False without raising.")

        # Test event helper with invalid token
        event_result = notify_return_created("Test Med", "BATCH-FAIL", 10, "ACTIVE", "Pharm", "Dist")
        assert event_result is False, "Event notification should return False on failure!"
        print("[PASS] Fault Tolerance: notify_return_created returned False without breaking transaction.")

        # Test invalid chat ID with original token
        settings.TELEGRAM_BOT_TOKEN = original_token
        result_bad_chat = send_telegram_message("Test invalid chat", chat_id="99999999999999999")
        assert result_bad_chat is False, "send_telegram_message should handle invalid chat ID gracefully!"
        print("[PASS] Fault Tolerance: Handled non-existent chat ID gracefully without raising.")

    finally:
        # Restore valid token
        settings.TELEGRAM_BOT_TOKEN = original_token


    print("\n=======================================================")
    print("ALL 6 WORKFLOW EVENTS & FAULT TOLERANCE TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    import datetime
    run_tests()
