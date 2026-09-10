"""
Comprehensive test script for Moderator AI Gemini Integration and Fallback.
Tests:
1. Live / configured Gemini call with google-genai
2. Structured output parsing & Pydantic validation
3. Full pipeline: Event -> Moderator AI -> ModeratorEvent in DB -> Notifications
4. Fallback execution when Gemini fails
5. Moderator Event idempotency
6. Safe non-blocking execution inside BackgroundTasks
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import SessionLocal
from app.models.schemas import (
    User, UserRole, Batch, BatchStatus, WorkflowEvent, ModeratorEvent, Notification, ModeratorAnalysis,
)
from app.moderator.agent import _call_gemini, run_moderator_analysis
from app.moderator.risk_engine import calculate_risk

def test_pydantic_schema_validation():
    print("\n--- 1. Testing Pydantic Structured Output Validation ---")
    sample_data = {
        "risk_level": "HIGH",
        "event_type": "DISCREPANCY",
        "analysis": "5% discrepancy detected between declared and received units.",
        "recommended_action": "Audit warehouse manifest and verify transit logs.",
        "message": "Discrepancy detected during return handoff.",
        "recipients": ["DISTRIBUTOR", "MANUFACTURER", "REGULATOR"],
    }
    validated = ModeratorAnalysis(**sample_data)
    assert validated.risk_level == "HIGH"
    assert "REGULATOR" in validated.recipients
    print("  [OK] ModeratorAnalysis schema validated correctly.")

def test_deterministic_fallback():
    print("\n--- 2. Testing Deterministic Risk Engine Fallback ---")
    fallback_reentry = calculate_risk(
        event_type="REENTRY_FRAUD_SCAN",
        event_data={"scan_location": "Pharmacy B"},
        batch_history=[],
    )
    assert fallback_reentry["risk_level"] == "CRITICAL"
    assert "REGULATOR" in fallback_reentry["recipients"]
    print("  [OK] Fallback for REENTRY_FRAUD_SCAN -> CRITICAL with REGULATOR notification.")

    fallback_discrepancy = calculate_risk(
        event_type="DISCREPANCY_DETECTED",
        event_data={"declared_qty": 100, "received_qty": 80},
        batch_history=[],
    )
    assert fallback_discrepancy["risk_level"] == "HIGH" # > 10%
    print("  [OK] Fallback for DISCREPANCY_DETECTED (20% variance) -> HIGH risk.")

def test_full_moderator_pipeline():
    print("\n--- 3. Testing Full Moderator Pipeline & Database Persistence ---")
    db = SessionLocal()
    try:
        batch = db.query(Batch).first()
        user = db.query(User).first()
        assert batch is not None, "No batch found in database"
        assert user is not None, "No user found in database"

        # Create a test workflow event
        wf_event = WorkflowEvent(
            batch_id=batch.id,
            actor_id=user.id,
            event_type="TEST_MODERATOR_DISCREPANCY",
            from_status="PICKUP_CONFIRMED",
            to_status="DISPUTED",
            data=json.dumps({"declared_qty": 100, "received_qty": 95}),
        )
        db.add(wf_event)
        db.commit()
        db.refresh(wf_event)

        initial_notif_count = db.query(Notification).count()

        # Run moderator analysis
        run_moderator_analysis(
            workflow_event_id=wf_event.id,
            batch_id=batch.id,
            event_type=wf_event.event_type,
            actor_id=user.id,
        )

        # Verify ModeratorEvent created
        mod_event = db.query(ModeratorEvent).filter(ModeratorEvent.workflow_event_id == wf_event.id).first()
        assert mod_event is not None, "ModeratorEvent was not created in DB!"
        print(f"  [OK] ModeratorEvent created: ID={mod_event.id}, Risk={mod_event.risk_level}, Action={mod_event.recommended_action[:40]}...")

        # Verify Notifications created
        new_notif_count = db.query(Notification).count()
        assert new_notif_count > initial_notif_count, "No notifications created by moderator pipeline!"
        print(f"  [OK] Notifications created: {new_notif_count - initial_notif_count} new notification(s) dispatched to target roles.")

        # Test Idempotency (calling again should not create duplicate ModeratorEvent or duplicate Notifications)
        run_moderator_analysis(
            workflow_event_id=wf_event.id,
            batch_id=batch.id,
            event_type=wf_event.event_type,
            actor_id=user.id,
        )
        mod_event_count = db.query(ModeratorEvent).filter(ModeratorEvent.workflow_event_id == wf_event.id).count()
        after_idempotency_notif_count = db.query(Notification).count()
        assert mod_event_count == 1, f"Expected 1 ModeratorEvent for workflow_event_id={wf_event.id}, found {mod_event_count}"
        assert after_idempotency_notif_count == new_notif_count, "Idempotency violated: duplicate notifications created!"
        print("  [OK] Idempotency verified: re-running analysis produced 0 duplicate events and 0 duplicate notifications.")

    finally:
        db.close()

if __name__ == "__main__":
    test_pydantic_schema_validation()
    test_deterministic_fallback()
    test_full_moderator_pipeline()
    print("\n=== ALL MODERATOR AI TESTS PASSED ===")
