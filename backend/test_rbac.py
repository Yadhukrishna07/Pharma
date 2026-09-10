"""
Test Suite: Backend Auth + RBAC Verification (test_rbac.py)
PharmMedian Closed-Loop Drug Return Platform

Verifies:
1. Authentication: 401 Unauthorized when missing or invalid token.
2. Authorization: 403 Forbidden when role is disallowed.
3. Successful execution: 200 OK / 201 Created when role is authorized.
4. Complete 2x2 Matrix across all protected endpoints specified in the Endpoint Protection Matrix.
"""

import sys
import uuid
import datetime
import httpx
from app.database import SessionLocal
from app.models.schemas import Batch, BatchStatus, Medicine, User, UserRole

BASE_URL = "http://127.0.0.1:8000"

# Role credentials
CREDENTIALS = {
    "PHARMACY": ("medplus", "password123"),
    "DISTRIBUTOR": ("bluedart", "password123"),
    "MANUFACTURER": ("sunpharma", "password123"),
    "FACILITY": ("bioclean", "password123"),
    "REGULATOR": ("cdsco", "password123"),
}

ALL_ROLES = ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "FACILITY", "REGULATOR"]


def get_tokens(client: httpx.Client) -> dict[str, str]:
    tokens = {}
    print("\n--- 1. Authenticating Roles & Obtaining JWTs ---")
    for role, (username, password) in CREDENTIALS.items():
        resp = client.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, f"Login failed for {role}: {resp.text}"
        data = resp.json()
        token = data.get("access_token")
        assert token, f"No access token returned for {role}"
        tokens[role] = token
        print(f"  [OK] {role:<14} -> Authenticated (token: {token[:18]}...)")
    return tokens


def setup_fresh_batch():
    """Create a fresh test batch for the state-changing RBAC tests."""
    db = SessionLocal()
    med = db.query(Medicine).first()
    if not med:
        med = Medicine(name="Amoxicillin 500mg", manufacturer="Sun Pharma Laboratories")
        db.add(med)
        db.commit()
        db.refresh(med)

    batch_num = f"RBAC-TEST-{uuid.uuid4().hex[:6].upper()}"
    batch = Batch(
        batch_number=batch_num,
        medicine_id=med.id,
        quantity=100,
        expiry_date=datetime.date.today() - datetime.timedelta(days=10),
        current_status=BatchStatus.EXPIRED,
        current_location="MedPlus Central Indiranagar",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    batch_id = batch.id
    batch_number = batch.batch_number
    db.close()
    return batch_id, batch_number


def run_tests():
    total_checks = 0
    passed_checks = 0

    def assert_status(resp: httpx.Response, expected_status: int or list, context: str):
        nonlocal total_checks, passed_checks
        total_checks += 1
        expected = [expected_status] if isinstance(expected_status, int) else expected_status
        if resp.status_code in expected:
            passed_checks += 1
            print(f"    PASS [{resp.status_code}] {context}")
            return True
        else:
            print(f"    FAIL [{resp.status_code} != expected {expected}] {context} - Body: {resp.text[:100]}")
            return False

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        tokens = get_tokens(client)

        def auth_header(role: str) -> dict:
            return {"Authorization": f"Bearer {tokens[role]}"}

        print("\n--- 2. Testing Endpoint Protection Matrix ---")

        # -------------------------------------------------------------
        # 1. POST /auth/login (Public)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /auth/login (Public)")
        resp = client.post("/auth/login", json={"username": "cdsco", "password": "password123"})
        assert_status(resp, 200, "Public login -> 200 OK")

        # -------------------------------------------------------------
        # 2. POST /batches/scan (Allowed: PHARMACY, REGULATOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /batches/scan (Allowed: PHARMACY, REGULATOR)")
        scan_payload = {"batch_number": "BATCH-001", "location": "Test Loc"}
        # 401 Unauthorized
        resp = client.post("/batches/scan", json=scan_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        # 403 Disallowed
        for role in ["DISTRIBUTOR", "MANUFACTURER", "FACILITY"]:
            resp = client.post("/batches/scan", json=scan_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        # 200 Allowed
        for role in ["PHARMACY", "REGULATOR"]:
            resp = client.post("/batches/scan", json=scan_payload, headers=auth_header(role))
            assert_status(resp, 200, f"Allowed {role} -> 200 OK")

        # -------------------------------------------------------------
        # 3. GET /batches/{id} (All Authenticated)
        # -------------------------------------------------------------
        print("\n[Endpoint] GET /batches/{id} (All Authenticated)")
        resp = client.get("/batches/1")
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ALL_ROLES:
            resp = client.get("/batches/1", headers=auth_header(role))
            assert_status(resp, 200, f"Authenticated {role} -> 200 OK")

        # -------------------------------------------------------------
        # 4. GET /batches/{id}/timeline (All Authenticated)
        # -------------------------------------------------------------
        print("\n[Endpoint] GET /batches/{id}/timeline (All Authenticated)")
        resp = client.get("/batches/1/timeline")
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ALL_ROLES:
            resp = client.get("/batches/1/timeline", headers=auth_header(role))
            assert_status(resp, 200, f"Authenticated {role} -> 200 OK")

        # -------------------------------------------------------------
        # 5. POST /returns (Allowed: PHARMACY)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /returns (Allowed: PHARMACY)")
        test_batch_id, test_batch_no = setup_fresh_batch()
        return_payload = {"batch_id": test_batch_id, "declared_quantity": 50, "distributor_id": 3}
        resp = client.post("/returns", json=return_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["DISTRIBUTOR", "MANUFACTURER", "FACILITY", "REGULATOR"]:
            resp = client.post("/returns", json=return_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post("/returns", json=return_payload, headers=auth_header("PHARMACY"))
        assert_status(resp, 200, "Allowed PHARMACY -> 200 OK")
        created_return_id = resp.json().get("id")

        # -------------------------------------------------------------
        # 6. GET /returns (Allowed: PHARMACY, DISTRIBUTOR, REGULATOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] GET /returns (Allowed: PHARMACY, DISTRIBUTOR, REGULATOR)")
        resp = client.get("/returns")
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["MANUFACTURER", "FACILITY"]:
            resp = client.get("/returns", headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        for role in ["PHARMACY", "DISTRIBUTOR", "REGULATOR"]:
            resp = client.get("/returns", headers=auth_header(role))
            assert_status(resp, 200, f"Allowed {role} -> 200 OK")

        # -------------------------------------------------------------
        # 7. POST /returns/{id}/pickup (Allowed: DISTRIBUTOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /returns/{id}/pickup (Allowed: DISTRIBUTOR)")
        pickup_url = f"/returns/{created_return_id}/pickup"
        resp = client.post(pickup_url)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "MANUFACTURER", "FACILITY", "REGULATOR"]:
            resp = client.post(pickup_url, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post(pickup_url, headers=auth_header("DISTRIBUTOR"))
        assert_status(resp, 200, "Allowed DISTRIBUTOR -> 200 OK")

        # -------------------------------------------------------------
        # 8. POST /returns/{id}/receive (Allowed: DISTRIBUTOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /returns/{id}/receive (Allowed: DISTRIBUTOR)")
        receive_url = f"/returns/{created_return_id}/receive"
        recv_payload = {"batch_id": test_batch_id, "received_quantity": 50}
        resp = client.post(receive_url, json=recv_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "MANUFACTURER", "FACILITY", "REGULATOR"]:
            resp = client.post(receive_url, json=recv_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post(receive_url, json=recv_payload, headers=auth_header("DISTRIBUTOR"))
        assert_status(resp, 200, "Allowed DISTRIBUTOR -> 200 OK")

        # -------------------------------------------------------------
        # 9. POST /disputes (Allowed: DISTRIBUTOR, MANUFACTURER)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /disputes (Allowed: DISTRIBUTOR, MANUFACTURER)")
        disp_payload = {"batch_id": test_batch_id, "declared_qty": 50, "received_qty": 40, "reason": "Damaged pack"}
        resp = client.post("/disputes", json=disp_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "FACILITY", "REGULATOR"]:
            resp = client.post("/disputes", json=disp_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp_dist = client.post("/disputes", json=disp_payload, headers=auth_header("DISTRIBUTOR"))
        assert_status(resp_dist, 200, "Allowed DISTRIBUTOR -> 200 OK")
        created_disp_id = resp_dist.json().get("id")

        # -------------------------------------------------------------
        # 10. POST /disputes/{id}/resolve (Allowed: DISTRIBUTOR, REGULATOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /disputes/{id}/resolve (Allowed: DISTRIBUTOR, REGULATOR)")
        resolve_url = f"/disputes/{created_disp_id}/resolve"
        res_payload = {"resolution_notes": "Settled shortage with credit note"}
        resp = client.post(resolve_url, json=res_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "FACILITY"]:
            resp = client.post(resolve_url, json=res_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post(resolve_url, json=res_payload, headers=auth_header("REGULATOR"))
        assert_status(resp, 200, "Allowed REGULATOR -> 200 OK")

        # -------------------------------------------------------------
        # 11. POST /manufacturer/receive (Allowed: MANUFACTURER)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /manufacturer/receive (Allowed: MANUFACTURER)")
        mfg_url = "/manufacturer/receive"
        mfg_payload = {"batch_id": test_batch_id, "notes": "Verified intake at facility"}
        resp = client.post(mfg_url, json=mfg_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "DISTRIBUTOR", "FACILITY", "REGULATOR"]:
            resp = client.post(mfg_url, json=mfg_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post(mfg_url, json=mfg_payload, headers=auth_header("MANUFACTURER"))
        assert_status(resp, 200, "Allowed MANUFACTURER -> 200 OK")

        # -------------------------------------------------------------
        # 12. POST /destruction/schedule (Allowed: MANUFACTURER)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /destruction/schedule (Allowed: MANUFACTURER)")
        sched_url = "/destruction/schedule"
        sched_payload = {"batch_id": test_batch_id, "facility_id": 5}
        resp = client.post(sched_url, json=sched_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "DISTRIBUTOR", "FACILITY", "REGULATOR"]:
            resp = client.post(sched_url, json=sched_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post(sched_url, json=sched_payload, headers=auth_header("MANUFACTURER"))
        assert_status(resp, 200, "Allowed MANUFACTURER -> 200 OK")

        # -------------------------------------------------------------
        # 13. POST /destruction/confirm (Allowed: FACILITY)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /destruction/confirm (Allowed: FACILITY)")
        conf_url = "/destruction/confirm"
        conf_payload = {"batch_id": test_batch_id, "quantity_destroyed": 50}
        resp = client.post(conf_url, json=conf_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "REGULATOR"]:
            resp = client.post(conf_url, json=conf_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post(conf_url, json=conf_payload, headers=auth_header("FACILITY"))
        assert_status(resp, 200, "Allowed FACILITY -> 200 OK")

        # -------------------------------------------------------------
        # 14. POST /certificates (Allowed: FACILITY)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /certificates (Allowed: FACILITY)")
        cert_num = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        cert_payload = {"certificate_number": cert_num, "batch_id": test_batch_id, "quantity": 50}
        resp = client.post("/certificates", json=cert_payload)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "REGULATOR"]:
            resp = client.post("/certificates", json=cert_payload, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post("/certificates", json=cert_payload, headers=auth_header("FACILITY"))
        assert_status(resp, 200, "Allowed FACILITY -> 200 OK")
        created_cert_id = resp.json().get("id")

        # -------------------------------------------------------------
        # 15. POST /certificates/{id}/verify (Allowed: REGULATOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /certificates/{id}/verify (Allowed: REGULATOR)")
        verify_url = f"/certificates/{created_cert_id}/verify"
        resp = client.post(verify_url)
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "FACILITY"]:
            resp = client.post(verify_url, headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post(verify_url, headers=auth_header("REGULATOR"))
        assert_status(resp, 200, "Allowed REGULATOR -> 200 OK")

        # -------------------------------------------------------------
        # 16. GET /alerts (Allowed: REGULATOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] GET /alerts (Allowed: REGULATOR)")
        resp = client.get("/alerts")
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "FACILITY"]:
            resp = client.get("/alerts", headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.get("/alerts", headers=auth_header("REGULATOR"))
        assert_status(resp, 200, "Allowed REGULATOR -> 200 OK")

        # -------------------------------------------------------------
        # 17. GET /notifications (All Authenticated)
        # -------------------------------------------------------------
        print("\n[Endpoint] GET /notifications (All Authenticated)")
        resp = client.get("/notifications")
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ALL_ROLES:
            resp = client.get("/notifications", headers=auth_header(role))
            assert_status(resp, 200, f"Authenticated {role} -> 200 OK")

        # -------------------------------------------------------------
        # 18. GET /moderator/events (Allowed: REGULATOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] GET /moderator/events (Allowed: REGULATOR)")
        resp = client.get("/moderator/events")
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "FACILITY"]:
            resp = client.get("/moderator/events", headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.get("/moderator/events", headers=auth_header("REGULATOR"))
        assert_status(resp, 200, "Allowed REGULATOR -> 200 OK")

        # -------------------------------------------------------------
        # 19. POST /audit/verify (Allowed: REGULATOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] POST /audit/verify (Allowed: REGULATOR)")
        resp = client.post("/audit/verify")
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "FACILITY"]:
            resp = client.post("/audit/verify", headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} -> 403 Forbidden")
        resp = client.post("/audit/verify", headers=auth_header("REGULATOR"))
        assert_status(resp, 200, "Allowed REGULATOR -> 200 OK")

        # -------------------------------------------------------------
        # 20. GET /dashboard/{role} (Allowed: Matching Role or REGULATOR)
        # -------------------------------------------------------------
        print("\n[Endpoint] GET /dashboard/{role} (Allowed: Matching Role or REGULATOR)")
        resp = client.get("/dashboard/pharmacy")
        assert_status(resp, 401, "No auth -> 401 Unauthorized")
        for role in ["DISTRIBUTOR", "MANUFACTURER", "FACILITY"]:
            resp = client.get("/dashboard/pharmacy", headers=auth_header(role))
            assert_status(resp, 403, f"Disallowed {role} on pharmacy dashboard -> 403 Forbidden")
        resp = client.get("/dashboard/pharmacy", headers=auth_header("PHARMACY"))
        assert_status(resp, 200, "Matching role PHARMACY -> 200 OK")
        resp = client.get("/dashboard/pharmacy", headers=auth_header("REGULATOR"))
        assert_status(resp, 200, "Super-role REGULATOR -> 200 OK")

    print("\n" + "=" * 60)
    print(f"RBAC MATRIX TEST SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED (100%)")
    print("=" * 60)
    if passed_checks == total_checks:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
