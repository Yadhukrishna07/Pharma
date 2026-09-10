"""
Moderator AI Agent — uses google-genai SDK to analyze workflow events.
Executed asynchronously via FastAPI BackgroundTasks.
Includes idempotency checks and fallback to deterministic risk engine.
"""

import json
import traceback
from typing import Optional

from app.config import settings
from app.database import SessionLocal
from app.models.schemas import (
    ModeratorEvent, WorkflowEvent, Batch, User, ModeratorAnalysis,
)
from app.moderator.prompts import SYSTEM_PROMPT, build_event_prompt
from app.moderator.risk_engine import calculate_risk
from app.services.notification_service import notify_by_role


def run_moderator_analysis(
    workflow_event_id: int,
    batch_id: int,
    event_type: str,
    actor_id: int,
) -> None:
    """
    Background task: Run Gemini AI analysis on a workflow event.
    - Checks idempotency (workflow_event_id uniqueness in moderator_events)
    - Builds context from batch lifecycle history
    - Calls Gemini API
    - Falls back to deterministic risk engine on failure
    """
    db = SessionLocal()
    try:
        # ── Idempotency check ──
        existing = (
            db.query(ModeratorEvent)
            .filter(ModeratorEvent.workflow_event_id == workflow_event_id)
            .first()
        )
        if existing:
            return  # Already processed

        # ── Gather context ──
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return

        actor = db.query(User).filter(User.id == actor_id).first()
        actor_role = actor.role.value if actor else "UNKNOWN"

        # Build lifecycle history
        events = (
            db.query(WorkflowEvent)
            .filter(WorkflowEvent.batch_id == batch_id)
            .order_by(WorkflowEvent.created_at.asc())
            .all()
        )
        batch_history = []
        for e in events:
            evt_actor = db.query(User).filter(User.id == e.actor_id).first()
            batch_history.append({
                "timestamp": str(e.created_at),
                "event_type": e.event_type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "actor_role": evt_actor.role.value if evt_actor else "UNKNOWN",
                "data": e.data,
            })

        # Get event data from the workflow event
        wf_event = db.query(WorkflowEvent).filter(WorkflowEvent.id == workflow_event_id).first()
        event_data = {}
        if wf_event and wf_event.data:
            try:
                event_data = json.loads(wf_event.data)
            except json.JSONDecodeError:
                event_data = {"raw": wf_event.data}

        current_status = batch.current_status
        if hasattr(current_status, "value"):
            current_status = current_status.value

        # ── Attempt AI analysis ──
        analysis_result = _call_gemini(
            event_type=event_type,
            batch_number=batch.batch_number,
            current_status=current_status,
            actor_role=actor_role,
            batch_history=batch_history,
            event_data=event_data,
        )

        # ── Fallback to deterministic engine on failure ──
        if analysis_result is None:
            analysis_result = calculate_risk(
                event_type=event_type,
                event_data=event_data,
                batch_history=batch_history,
            )

        # ── Store moderator event ──
        moderator_event = ModeratorEvent(
            workflow_event_id=workflow_event_id,
            batch_id=batch_id,
            risk_level=analysis_result.get("risk_level", "LOW"),
            analysis=analysis_result.get("analysis", ""),
            recommended_action=analysis_result.get("recommended_action", ""),
            message=analysis_result.get("message", ""),
        )
        db.add(moderator_event)

        # ── Send notifications ──
        recipients = analysis_result.get("recipients", [])
        if recipients:
            notify_by_role(
                db=db,
                roles=recipients,
                title=f"Moderator Alert: {analysis_result.get('risk_level', 'LOW')} — {event_type}",
                message=analysis_result.get("message", ""),
            )

        db.commit()

    except Exception as e:
        db.rollback()
        # Insert a deterministic fallback so business workflows are never blocked
        try:
            fallback_event = ModeratorEvent(
                workflow_event_id=workflow_event_id,
                batch_id=batch_id,
                risk_level="LOW",
                analysis=f"System warning: Moderator analysis failed. Error: {str(e)}",
                recommended_action="Manual review recommended.",
                message="Automated analysis unavailable. Please review manually.",
            )
            db.add(fallback_event)
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def _call_gemini(
    event_type: str,
    batch_number: str,
    current_status: str,
    actor_role: str,
    batch_history: list,
    event_data: dict,
) -> Optional[dict]:
    """
    Call the Google Gemini API using the google-genai SDK.
    Returns parsed JSON dict or None on failure.
    """
    if not settings.GEMINI_API_KEY:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = build_event_prompt(
            event_type=event_type,
            batch_number=batch_number,
            current_status=current_status,
            actor_role=actor_role,
            batch_history=batch_history,
            event_data=event_data,
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=ModeratorAnalysis,
        )

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=config,
        )

        if not response or not response.text:
            return None

        # Extract text from response
        text = response.text.strip()
        # Clean markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        result = json.loads(text)

        # Validate with Pydantic
        validated = ModeratorAnalysis(**result)
        return validated.model_dump()

    except Exception as e:
        print(f"Gemini API error: {e}")
        traceback.print_exc()
        return None

