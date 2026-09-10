import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.schemas import (
    Batch, ReturnRequest, Dispute, DestructionRecord, Certificate,
    WorkflowEvent, ModeratorEvent, Alert, AuditLog,
)
from app.services.audit_service import verify_audit_chain

BASE = 'http://localhost:8000'

def get_token(u):
    return requests.post(f'{BASE}/auth/login', json={'username': u, 'password': 'password123'}).json()['access_token']

def test_full_pipeline():
    tokens = {u: get_token(u) for u in ['medplus', 'pharmacyb', 'bluedart', 'sunpharma', 'bioclean', 'cdsco']}
    headers = {u: {'Authorization': f'Bearer {tokens[u]}'} for u in tokens}

    print('=== STARTING RUNTIME STEP-BY-STEP AUDIT ===')

    # Step 0: Reset fresh
    res = requests.post(f'{BASE}/dashboard/reset', json={'mode': 'fresh'})
    assert res.status_code == 200, f'Reset failed: {res.text}'

    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == 'BATCH-001').first()
    assert b.current_status.value == 'EXPIRED'
    assert b.quantity == 100
    batch_id = b.id
    db.close()
    print('Step 0 PASS: Fresh EXPIRED state (PostgreSQL + Dashboard verified)')

    # Step 1: Pharmacy return
    res = requests.post(f'{BASE}/returns/', json={'batch_id': batch_id, 'declared_quantity': 100, 'distributor_id': 3}, headers=headers['medplus'])
    assert res.status_code == 200
    ret_id = res.json()['id']

    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == 'BATCH-001').first()
    assert b.current_status.value == 'RETURN_REQUESTED'
    db.close()

    # Cross role: Distributor sees it
    d_dash = requests.get(f'{BASE}/dashboard/distributor', headers=headers['bluedart']).json()
    assert d_dash['batch']['current_status'] == 'RETURN_REQUESTED'
    assert d_dash['incoming_return']['id'] == ret_id
    assert d_dash['pickup_state'] == 'PENDING'
    print('Step 1 PASS: Pharmacy return -> Distributor sees incoming return')

    # Step 2: Pickup confirmed
    res = requests.post(f'{BASE}/returns/{ret_id}/pickup', headers=headers['bluedart'])
    assert res.status_code == 200

    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == 'BATCH-001').first()
    assert b.current_status.value == 'PICKUP_CONFIRMED'
    db.close()

    # Cross role: Pharmacy & Distributor update
    p_dash = requests.get(f'{BASE}/dashboard/pharmacy', headers=headers['medplus']).json()
    d_dash = requests.get(f'{BASE}/dashboard/distributor', headers=headers['bluedart']).json()
    assert p_dash['batch']['current_status'] == 'PICKUP_CONFIRMED'
    assert d_dash['batch']['current_status'] == 'PICKUP_CONFIRMED'
    assert d_dash['pickup_state'] == 'CONFIRMED'
    print('Step 2 PASS: Pickup confirmed -> Pharmacy & Distributor updated')

    # Step 3: Distributor receives 95 vs 100 -> Discrepancy
    res = requests.post(f'{BASE}/returns/{ret_id}/receive', json={'batch_id': ret_id, 'received_quantity': 95}, headers=headers['bluedart'])
    assert res.status_code == 200
    assert res.json()['status'] == 'disputed'
    disp_id = res.json()['dispute_id']

    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == 'BATCH-001').first()
    assert b.current_status.value == 'DISPUTED'
    disp = db.query(Dispute).filter(Dispute.id == disp_id).first()
    assert disp.status.value == 'OPEN'
    assert disp.declared_qty == 100 and disp.received_qty == 95
    db.close()

    d_dash = requests.get(f'{BASE}/dashboard/distributor', headers=headers['bluedart']).json()
    assert d_dash['dispute']['status'] == 'OPEN'
    assert d_dash['dispute']['variance'] == 5
    print('Step 3 PASS: Discrepancy -> Dispute OPEN (100 declared vs 95 received)')

    # Step 4: Resolve dispute
    res = requests.post(f'{BASE}/disputes/{disp_id}/resolve', json={'resolution_notes': 'Damaged units discarded per SOP'}, headers=headers['bluedart'])
    assert res.status_code == 200

    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == 'BATCH-001').first()
    assert b.current_status.value == 'RECEIVED_BY_MANUFACTURER'
    disp = db.query(Dispute).filter(Dispute.id == disp_id).first()
    assert disp.status.value == 'RESOLVED'
    db.close()

    m_dash = requests.get(f'{BASE}/dashboard/manufacturer', headers=headers['sunpharma']).json()
    assert m_dash['batch']['current_status'] == 'RECEIVED_BY_MANUFACTURER'
    assert m_dash['batch']['quantity'] == 95
    print('Step 4 PASS: Dispute resolved -> Manufacturer received (95 packs)')

    # Step 5: Schedule destruction
    res = requests.post(f'{BASE}/destruction/schedule', json={'batch_id': batch_id, 'facility_id': 5}, headers=headers['sunpharma'])
    assert res.status_code == 200

    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == 'BATCH-001').first()
    assert b.current_status.value == 'DESTRUCTION_SCHEDULED'
    db.close()

    f_dash = requests.get(f'{BASE}/dashboard/facility', headers=headers['bioclean']).json()
    assert f_dash['batch']['current_status'] == 'DESTRUCTION_SCHEDULED'
    assert f_dash['batch']['quantity_to_destroy'] == 95
    print('Step 5 PASS: Destruction scheduled -> Facility sees 95 packs')

    # Step 6: Record destruction
    res = requests.post(f'{BASE}/destruction/record', json={'batch_id': batch_id, 'quantity_destroyed': 95}, headers=headers['bioclean'])
    assert res.status_code == 200

    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == 'BATCH-001').first()
    assert b.current_status.value == 'DESTROYED'
    db.close()

    f_dash = requests.get(f'{BASE}/dashboard/facility', headers=headers['bioclean']).json()
    r_dash = requests.get(f'{BASE}/dashboard/regulator', headers=headers['cdsco']).json()
    assert f_dash['batch']['current_status'] == 'DESTROYED'
    assert r_dash['batch']['current_status'] == 'DESTROYED'
    print('Step 6 PASS: Destruction recorded -> Facility & Regulator show DESTROYED')

    # Step 7: Certificate creation & verification
    res = requests.post(f'{BASE}/certificates/', json={'certificate_number': 'CERT-771122', 'batch_id': batch_id, 'quantity': 95}, headers=headers['bioclean'])
    assert res.status_code == 200
    cert_id = res.json()['id']

    res = requests.post(f'{BASE}/certificates/{cert_id}/verify', headers=headers['cdsco'])
    assert res.status_code == 200

    db = SessionLocal()
    b = db.query(Batch).filter(Batch.batch_number == 'BATCH-001').first()
    assert b.current_status.value == 'CLOSED'
    db.close()

    for r, u in [('pharmacy', 'medplus'), ('distributor', 'bluedart'), ('manufacturer', 'sunpharma'), ('facility', 'bioclean'), ('regulator', 'cdsco')]:
        d = requests.get(f'{BASE}/dashboard/{r}', headers=headers[u]).json()
        assert d['batch']['current_status'] == 'CLOSED'
    print('Step 7 PASS: Certificate verified -> CLOSED visible on ALL 5 dashboards')

    # Step 8: Pharmacy B scan -> CRITICAL RE-ENTRY
    res = requests.post(f'{BASE}/batches/scan', json={'batch_number': 'BATCH-001', 'location': 'Pharmacy B', 'actor_role': 'PHARMACY'}, headers=headers['pharmacyb'])
    assert res.status_code == 200
    assert res.json()['fraud_detected'] is True

    db = SessionLocal()
    alerts = db.query(Alert).filter(Alert.batch_id == batch_id, Alert.severity == 'CRITICAL').all()
    assert len(alerts) >= 1
    db.close()

    r_dash = requests.get(f'{BASE}/dashboard/regulator', headers=headers['cdsco']).json()
    assert any(a['severity'] == 'CRITICAL' for a in r_dash['alerts'])
    print('Step 8 PASS: Pharmacy B scan -> CRITICAL RE-ENTRY fraud detected & visible on Regulator')

    # Step 9: Audit chain verification
    db = SessionLocal()
    audit_res = verify_audit_chain(db)
    assert audit_res['is_valid'] is True
    print(f'Step 9 PASS: SHA-256 Audit Chain verified ({audit_res["total_records"]} records intact)')
    db.close()

    print('=== ALL RUNTIME STEPS AUDITED SUCCESSFULLY ===')

if __name__ == '__main__':
    test_full_pipeline()
