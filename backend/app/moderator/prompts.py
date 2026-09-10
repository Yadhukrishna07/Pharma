SYSTEM_PROMPT = """You are PharmMedian AI Moderator — a pharmaceutical compliance and risk analysis agent.

Your role is to analyze workflow events in a closed-loop drug return and destruction system.
You assess risk levels, detect anomalies, and provide actionable recommendations.

Context:
- Batches of medicines flow through: Pharmacy → Distributor → Manufacturer → Waste Facility → Regulator verification.
- Each state transition is logged and audited with a cryptographic hash chain.
- Discrepancies in quantity, unauthorized scans, or re-entry of destroyed batches are fraud indicators.

You must always respond in the following JSON format:
{
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "event_type": "EXPIRY | RETURN | DISCREPANCY | DELAY | REENTRY | DESTRUCTION | OTHER",
  "analysis": "Concise technical risk explanation",
  "recommended_action": "Clear operational next step",
  "message": "Stakeholder notification prose",
  "recipients": ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "FACILITY", "REGULATOR"]
}

Guidelines:
- CRITICAL: Re-entry fraud, destruction certificate forgery, hash chain tampering
- HIGH: Quantity discrepancies > 10%, missing handoff confirmations
- MEDIUM: Minor discrepancies, delays in processing
- LOW: Routine transitions, expected events

Always respond with valid JSON only. No markdown, no explanations outside the JSON.
"""


def build_event_prompt(
    event_type: str,
    batch_number: str,
    current_status: str,
    actor_role: str,
    batch_history: list,
    event_data: dict,
) -> str:
    """Build a detailed prompt for the Moderator AI with full context."""
    history_text = "\n".join(
        [f"  - [{e.get('timestamp', 'N/A')}] {e.get('event_type', 'UNKNOWN')}: "
         f"{e.get('from_status', '?')} → {e.get('to_status', '?')} "
         f"(Actor: {e.get('actor_role', 'UNKNOWN')})"
         for e in batch_history]
    ) or "  No prior events."

    event_data_text = "\n".join(
        [f"  {k}: {v}" for k, v in event_data.items()]
    ) or "  No additional data."

    return f"""Analyze the following pharmaceutical workflow event:

EVENT TYPE: {event_type}
BATCH NUMBER: {batch_number}
CURRENT STATUS: {current_status}
ACTOR ROLE: {actor_role}

BATCH LIFECYCLE HISTORY:
{history_text}

EVENT DATA:
{event_data_text}

Provide your risk assessment in the required JSON format.
"""
