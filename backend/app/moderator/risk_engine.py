"""
Deterministic risk engine for fallback when AI is unavailable.
Provides rule-based risk assessment based on event type and data.
"""

from typing import List


def calculate_risk(
    event_type: str,
    event_data: dict,
    batch_history: list,
) -> dict:
    """
    Rule-based risk calculation as a fallback for the AI moderator.
    Returns a dict matching the ModeratorAnalysis schema.
    """
    risk_level = "LOW"
    analysis = ""
    recommended_action = ""
    message = ""
    recipients: List[str] = []

    if event_type == "REENTRY_FRAUD_SCAN":
        risk_level = "CRITICAL"
        analysis = (
            "Re-entry fraud detected. A batch that was previously destroyed or closed "
            "has been scanned at a new location. This indicates potential counterfeit "
            "product re-entering the supply chain."
        )
        recommended_action = (
            "Immediately quarantine the scanned batch. Initiate investigation. "
            "Notify regulatory authorities and all stakeholders."
        )
        message = (
            f"CRITICAL ALERT: Batch re-entry fraud detected. "
            f"Scan location: {event_data.get('scan_location', 'unknown')}. "
            "Immediate investigation required."
        )
        recipients = ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER", "FACILITY", "REGULATOR"]

    elif event_type == "DISCREPANCY_DETECTED":
        declared = event_data.get("declared_qty", 0)
        received = event_data.get("received_qty", 0)
        diff = abs(declared - received)
        pct = (diff / declared * 100) if declared > 0 else 0

        if pct > 10:
            risk_level = "HIGH"
        else:
            risk_level = "MEDIUM"

        analysis = (
            f"Quantity discrepancy detected: declared {declared}, received {received} "
            f"({diff} units, {pct:.1f}% variance)."
        )
        recommended_action = (
            "Review transportation logs. Verify packaging integrity. "
            "Resolve dispute before proceeding with manufacturer handoff."
        )
        message = (
            f"Quantity discrepancy of {diff} units detected during distributor receipt. "
            "Dispute has been raised and requires resolution."
        )
        recipients = ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER"]

    elif event_type in ("RETURN_REQUESTED", "RETURN_REQUEST"):
        risk_level = "LOW"
        analysis = "Return request initiated. Routine process for expired medication."
        recommended_action = "Proceed with standard pickup and verification workflow."
        message = "A new return request has been submitted for processing."
        recipients = ["PHARMACY", "DISTRIBUTOR"]

    elif event_type == "DESTRUCTION_RECORDED":
        risk_level = "MEDIUM"
        analysis = "Destruction event recorded. Verify quantities match expected values."
        recommended_action = "Generate destruction certificate and submit for regulatory verification."
        message = "Batch destruction has been recorded. Certificate generation pending."
        recipients = ["FACILITY", "MANUFACTURER", "REGULATOR"]

    elif event_type == "CERTIFICATE_GENERATED":
        risk_level = "LOW"
        analysis = "Destruction certificate generated. Awaiting regulatory verification."
        recommended_action = "Submit certificate for regulatory review and approval."
        message = "Destruction certificate has been generated and is ready for verification."
        recipients = ["FACILITY", "REGULATOR"]

    elif event_type in ("PICKUP_CONFIRMED", "PICKUP"):
        risk_level = "LOW"
        analysis = "Pickup confirmed by distributor. Standard logistics event."
        recommended_action = "Monitor transit and await receipt confirmation."
        message = "Batch pickup has been confirmed by the logistics partner."
        recipients = ["PHARMACY", "DISTRIBUTOR"]

    else:
        risk_level = "LOW"
        analysis = f"Routine workflow event: {event_type}."
        recommended_action = "No immediate action required. Continue standard workflow."
        message = f"Workflow event '{event_type}' processed successfully."
        recipients = ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER"]

    return {
        "risk_level": risk_level,
        "event_type": event_type,
        "analysis": analysis,
        "recommended_action": recommended_action,
        "message": message,
        "recipients": recipients,
    }
