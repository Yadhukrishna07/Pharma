"""
Comprehensive End-to-End Live Workflow Verification Script.
Tests all transitions through HTTP API endpoints and verifies:
1. Pharmacy return -> Distributor sees return
2. Pickup -> Pharmacy/Distributor update
3. 100 -> 95 discrepancy -> Dispute appears
4. Dispute resolution -> Manufacturer can proceed
5. Manufacturer receipt -> destruction becomes available
6. Destruction -> Facility/Regulator update
7. Certificate verification -> CLOSED everywhere
8. Pharmacy B scan -> CRITICAL RE-ENTRY visible on Regulator + relevant dashboards
9. SHA-256 audit chain verified intact in PostgreSQL
"""

import sys
import requests

BASE_URL = "http://localhost:8000"


def get_token(username, password="password123"):
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def run_full_test():
    print("=" * 70)
    print("PHARMAMEDIAN — FULL LIVE WORKFLOW END-TO-END VERIFICATION")
    print("=" * 70)

    # 1. Obtain tokens for all roles
    tokens = {
        "medplus": get_token("medplus"),
        "pharmacyb": get_token("pharmacyb"),
        "bluedart": get_token("bluedart"),
        "sunpharma": get_token("sunpharma"),
        "bioclean": get_token("bioclean"),
        "cdsco": get_token("cdsco"),
    }
    print("[1/10] Authenticated all 6 users successfully.")

    # 2. Reset BATCH-001 to fresh EXPIRED state
    res = requests.post(f"{BASE_URL}/dashboard/reset", json={"mode": "fresh"})
    assert res.status_code == 200, f"Reset failed: {res.text}"
    print("[2/10] Reset BATCH-001 to fresh state (EXPIRED, 100 packs).")

    # Check pharmacy dashboard
    p_dash = requests.get(f"{BASE_URL}/dashboard/pharmacy", headers=auth_header(tokens["medplus"])).json()
    assert p_dash["batch"]["current_status"] == "EXPIRED"
    assert p_dash["batch"]["quantity"] == 100
    batch_id = p_dash["batch"]["id"]
    print(f"       Pharmacy dashboard verified: Batch {p_dash['batch']['batch_number']} status is EXPIRED.")

    # 3. Step 1: Pharmacy creates return request
    res = requests.post(
        f"{BASE_URL}/returns/",
        json={"batch_id": batch_id, "declared_quantity": 100, "distributor_id": 3},
        headers=auth_header(tokens["medplus"]),
    )
    assert res.status_code == 200, f"Return request failed: {res.text}"
    return_id = res.json()["id"]
    print(f"[3/10] Pharmacy created return request #{return_id} (100 packs).")

    # Verify Distributor dashboard sees incoming return
    d_dash = requests.get(f"{BASE_URL}/dashboard/distributor", headers=auth_header(tokens["bluedart"])).json()
    assert d_dash["batch"]["current_status"] == "RETURN_REQUESTED"
    assert d_dash["incoming_return"]["id"] == return_id
    assert d_dash["pickup_state"] == "PENDING"
    print("       Distributor dashboard verified: Incoming return visible, pickup PENDING.")

    # 4. Step 2: Distributor confirms pickup
    res = requests.post(
        f"{BASE_URL}/returns/{return_id}/pickup",
        headers=auth_header(tokens["bluedart"]),
    )
    assert res.status_code == 200, f"Pickup failed: {res.text}"
    print("[4/10] Distributor confirmed pickup at MedPlus Central.")

    # Verify Pharmacy + Distributor dashboards reflect PICKUP_CONFIRMED
    p_dash = requests.get(f"{BASE_URL}/dashboard/pharmacy", headers=auth_header(tokens["medplus"])).json()
    d_dash = requests.get(f"{BASE_URL}/dashboard/distributor", headers=auth_header(tokens["bluedart"])).json()
    assert p_dash["batch"]["current_status"] == "PICKUP_CONFIRMED"
    assert d_dash["batch"]["current_status"] == "PICKUP_CONFIRMED"
    assert d_dash["pickup_state"] == "CONFIRMED"
    print("       Pharmacy & Distributor dashboards updated: Status PICKUP_CONFIRMED.")

    # 5. Step 3: Distributor receives 95 packs -> Discrepancy detected (100 declared vs 95 received)
    res = requests.post(
        f"{BASE_URL}/returns/{return_id}/receive",
        json={"batch_id": return_id, "received_quantity": 95},
        headers=auth_header(tokens["bluedart"]),
    )
    assert res.status_code == 200, f"Receive failed: {res.text}"
    assert res.json()["status"] == "disputed"
    dispute_id = res.json()["dispute_id"]
    print(f"[5/10] Distributor received 95 packs. Discrepancy detected! Dispute #{dispute_id} created.")

    # Verify Distributor dashboard shows DISPUTE OPEN
    d_dash = requests.get(f"{BASE_URL}/dashboard/distributor", headers=auth_header(tokens["bluedart"])).json()
    assert d_dash["batch"]["current_status"] == "DISPUTED"
    assert d_dash["dispute"]["status"] == "OPEN"
    assert d_dash["dispute"]["variance"] == 5
    print("       Distributor dashboard verified: DISPUTE OPEN (100 declared vs 95 received).")

    # 6. Step 4: Distributor resolves dispute -> Workflow resumes to Manufacturer
    res = requests.post(
        f"{BASE_URL}/disputes/{dispute_id}/resolve",
        json={"resolution_notes": "Discrepancy verified: 5 units damaged in transit and discarded per SOP."},
        headers=auth_header(tokens["bluedart"]),
    )
    assert res.status_code == 200, f"Resolve dispute failed: {res.text}"
    print("[6/10] Dispute resolved. Batch forwarded to Manufacturer.")

    # Verify Manufacturer dashboard updates
    m_dash = requests.get(f"{BASE_URL}/dashboard/manufacturer", headers=auth_header(tokens["sunpharma"])).json()
    assert m_dash["batch"]["current_status"] == "RECEIVED_BY_MANUFACTURER"
    assert m_dash["manufacturer_receipt_state"] == "CONFIRMED"
    print("       Manufacturer dashboard verified: RECEIVED_BY_MANUFACTURER.")

    # 7. Step 5: Manufacturer schedules destruction with BioClean (facility_id=5)
    res = requests.post(
        f"{BASE_URL}/destruction/schedule",
        json={"batch_id": batch_id, "facility_id": 5},
        headers=auth_header(tokens["sunpharma"]),
    )
    assert res.status_code == 200, f"Schedule destruction failed: {res.text}"
    print("[7/10] Manufacturer scheduled destruction with BioClean Biomedical Waste Facility.")

    # Verify Facility dashboard
    f_dash = requests.get(f"{BASE_URL}/dashboard/facility", headers=auth_header(tokens["bioclean"])).json()
    assert f_dash["batch"]["current_status"] == "DESTRUCTION_SCHEDULED"
    assert f_dash["batch"]["quantity_to_destroy"] == 95
    print("       Facility dashboard verified: DESTRUCTION_SCHEDULED (95 packs).")

    # 8. Step 6: Facility confirms destruction
    res = requests.post(
        f"{BASE_URL}/destruction/record",
        json={"batch_id": batch_id, "quantity_destroyed": 95},
        headers=auth_header(tokens["bioclean"]),
    )
    assert res.status_code == 200, f"Record destruction failed: {res.text}"
    print("[8/10] Facility recorded destruction of 95 packs. Batch status: DESTROYED.")

    # Verify Facility + Regulator dashboards reflect DESTROYED
    f_dash = requests.get(f"{BASE_URL}/dashboard/facility", headers=auth_header(tokens["bioclean"])).json()
    r_dash = requests.get(f"{BASE_URL}/dashboard/regulator", headers=auth_header(tokens["cdsco"])).json()
    assert f_dash["batch"]["current_status"] == "DESTROYED"
    assert r_dash["batch"]["current_status"] == "DESTROYED"
    print("       Facility & Regulator dashboards verified: Status DESTROYED.")

    # 9. Step 7: Facility issues Certificate and Regulator verifies -> CLOSED
    cert_num = "CERT-998811"
    res = requests.post(
        f"{BASE_URL}/certificates/",
        json={"certificate_number": cert_num, "batch_id": batch_id, "quantity": 95},
        headers=auth_header(tokens["bioclean"]),
    )
    assert res.status_code == 200, f"Certificate creation failed: {res.text}"
    cert_id = res.json()["id"]
    print(f"       Facility issued certificate #{cert_num} (ID: {cert_id}).")

    res = requests.post(
        f"{BASE_URL}/certificates/{cert_id}/verify",
        headers=auth_header(tokens["cdsco"]),
    )
    assert res.status_code == 200, f"Certificate verify failed: {res.text}"
    print("[9/10] Regulator verified certificate. Lifecycle transitioned to CLOSED everywhere.")

    # Verify batch is CLOSED on all dashboards
    for role, u_key in [("pharmacy", "medplus"), ("distributor", "bluedart"), ("manufacturer", "sunpharma"), ("facility", "bioclean"), ("regulator", "cdsco")]:
        dash = requests.get(f"{BASE_URL}/dashboard/{role}", headers=auth_header(tokens[u_key])).json()
        assert dash["batch"]["current_status"] == "CLOSED", f"Role {role} does not show CLOSED (got {dash['batch']['current_status']})"
    print("       Verified: Batch status is CLOSED on all 5 role dashboards!")

    # 10. Step 8: Pharmacy B scans closed batch -> CRITICAL RE-ENTRY
    res = requests.post(
        f"{BASE_URL}/batches/scan",
        json={"batch_number": "BATCH-001", "location": "Pharmacy B", "actor_role": "PHARMACY"},
        headers=auth_header(tokens["pharmacyb"]),
    )
    assert res.status_code == 200, f"Scan failed: {res.text}"
    scan_data = res.json()
    assert scan_data["fraud_detected"] is True
    print("[10/10] Pharmacy B scanned BATCH-001: CRITICAL RE-ENTRY fraud detected!")

    # Verify Regulator dashboard displays the critical alert
    r_dash = requests.get(f"{BASE_URL}/dashboard/regulator", headers=auth_header(tokens["cdsco"])).json()
    assert any(a["severity"] == "CRITICAL" for a in r_dash["alerts"])
    print("        Regulator dashboard verified: CRITICAL RE-ENTRY alert visible!")

    # 11. Verify Cryptographic Audit Chain
    audit_res = requests.post(f"{BASE_URL}/audit/verify", headers=auth_header(tokens["cdsco"])).json()
    assert audit_res["is_valid"] is True, f"Audit chain broken: {audit_res}"
    print(f"       Cryptographic SHA-256 Audit Chain verified: {audit_res['verified_records']} records intact.")

    print("\n" + "=" * 70)
    print("ALL 10 VERIFICATION STEPS PASSED PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_full_test()
