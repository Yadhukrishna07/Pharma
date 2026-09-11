"""
Moderator AI Agent — uses google-genai SDK to analyze workflow events.
Executed asynchronously via FastAPI BackgroundTasks.
Includes idempotency checks and fallback to deterministic risk engine.
"""

import json
import logging
import time
from typing import Optional

from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import SessionLocal
from app.models.schemas import (
    ModeratorEvent, WorkflowEvent, Batch, User, ModeratorAnalysis,
)
from app.moderator.prompts import SYSTEM_PROMPT, build_event_prompt
from app.moderator.risk_engine import calculate_risk
from app.services.notification_service import notify_by_role

logger = logging.getLogger("moderator")

# Roles a notification is ever allowed to go to. Anything the AI returns
# outside this set is dropped rather than passed to notify_by_role — the
# model's output should never be able to widen its own blast radius.
_VALID_ROLES = {"PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "FACILITY", "REGULATOR"}

_GEMINI_TIMEOUT_SECONDS = 20
_GEMINI_MAX_ATTEMPTS = 2  # 1 retry on transient failure, then fall back


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
        # ── Idempotency check (best-effort; DB unique constraint on
        # workflow_event_id is the real guarantee — see IntegrityError
        # handling below for the race-safe fallback) ──
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
            logger.warning("Batch %s not found for workflow_event %s", batch_id, workflow_event_id)
            return

        actor = db.query(User).filter(User.id == actor_id).first()
        actor_role = actor.role.value if actor else "UNKNOWN"

        # Build lifecycle history in one pass, batching the actor lookups
        # (previously one query per event — N+1) into a single IN query.
        events = (
            db.query(WorkflowEvent)
            .filter(WorkflowEvent.batch_id == batch_id)
            .order_by(WorkflowEvent.created_at.asc())
            .all()
        )

        actor_ids = {e.actor_id for e in events if e.actor_id is not None}
        actors_by_id = {
            u.id: u for u in db.query(User).filter(User.id.in_(actor_ids)).all()
        } if actor_ids else {}

        batch_history = []
        wf_event = None
        for e in events:
            evt_actor = actors_by_id.get(e.actor_id)
            batch_history.append({
                "timestamp": str(e.created_at),
                "event_type": e.event_type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "actor_role": evt_actor.role.value if evt_actor else "UNKNOWN",
                "data": e.data,
            })
            if e.id == workflow_event_id:
                wf_event = e

        # Fall back to a direct lookup only if the target event wasn't in
        # this batch's history for some reason (shouldn't normally happen).
        if wf_event is None:
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

        recipients = _sanitize_recipients(analysis_result.get("recipients", []))

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

        try:
            db.commit()
        except IntegrityError:
            # Another worker processed this workflow_event_id between our
            # SELECT and this INSERT (requires a unique constraint on
            # workflow_event_id at the DB level). Safe to no-op.
            db.rollback()
            logger.info(
                "workflow_event %s already processed concurrently; skipping",
                workflow_event_id,
            )
            return

        # ── Send notifications (after commit succeeds, so we never notify
        # for a moderator event that didn't actually get persisted) ──
        if recipients:
            notify_by_role(
                db=db,
                roles=recipients,
                title=f"Moderator Alert: {analysis_result.get('risk_level', 'LOW')} — {event_type}",
                message=analysis_result.get("message", ""),
            )

    except Exception as e:
        db.rollback()
        logger.exception(
            "Moderator analysis failed for workflow_event %s (batch %s)",
            workflow_event_id, batch_id,
        )
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
        except IntegrityError:
            db.rollback()  # already recorded concurrently — fine
        except Exception:
            db.rollback()
            logger.exception("Failed to record fallback moderator event as well")
    finally:
        db.close()


def _sanitize_recipients(recipients) -> list:
    """Drop anything the AI (or fallback) returned that isn't a known role,
    so a hallucinated or injected role string can never reach notify_by_role."""
    if not isinstance(recipients, list):
        return []
    return [r for r in recipients if r in _VALID_ROLES]


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
    Retries once on transient failure, then returns None so the caller
    falls back to the deterministic risk engine.
    """
    if not settings.GEMINI_API_KEY:
        return None

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
        http_options=types.HttpOptions(timeout=_GEMINI_TIMEOUT_SECONDS * 1000),
    )

    last_error: Optional[Exception] = None
    for attempt in range(1, _GEMINI_MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

            if not response or not response.text:
                logger.warning("Gemini returned empty response (attempt %d)", attempt)
                last_error = ValueError("empty response")
                continue

            text = response.text.strip()
            if text.startswith("```"):
                lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
                text = "\n".join(lines)

            result = json.loads(text)
            validated = ModeratorAnalysis(**result)

            recipients = _sanitize_recipients(validated.recipients if hasattr(validated, "recipients") else [])
            dumped = validated.model_dump()
            dumped["recipients"] = recipients
            return dumped

        except Exception as e:
            last_error = e
            logger.warning("Gemini API error on attempt %d/%d: %s", attempt, _GEMINI_MAX_ATTEMPTS, e)
            if attempt < _GEMINI_MAX_ATTEMPTS:
                time.sleep(0.5 * attempt)  # small backoff before retrying
                continue

    logger.error("Gemini API failed after %d attempt(s): %s", _GEMINI_MAX_ATTEMPTS, last_error)
    return None