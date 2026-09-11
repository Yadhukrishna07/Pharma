import html
import json
import logging
import datetime
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


def _sanitize_log_text(text: str) -> str:
    """Mask Telegram bot token from log messages to prevent credential leakage."""
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN in text:
        return text.replace(settings.TELEGRAM_BOT_TOKEN, "[REDACTED_BOT_TOKEN]")
    return text


def get_chat_id_for_role(role: str) -> Optional[str]:
    """
    Resolve Telegram Chat ID for a given user role.
    Defaults to settings.TELEGRAM_CHAT_ID for test mode while keeping
    extensible role-specific routing for future production configs.
    """
    # Placeholder for future role-specific Telegram channels/chats
    role_to_chat: Dict[str, Optional[str]] = {
        "PHARMACY": settings.TELEGRAM_CHAT_ID,
        "DISTRIBUTOR": settings.TELEGRAM_CHAT_ID,
        "MANUFACTURER": settings.TELEGRAM_CHAT_ID,
        "FACILITY": settings.TELEGRAM_CHAT_ID,
        "REGULATOR": settings.TELEGRAM_CHAT_ID,
    }
    return role_to_chat.get(role.upper(), settings.TELEGRAM_CHAT_ID)


def send_telegram_message(
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
) -> bool:
    """
    Send a message via Telegram Bot API sendMessage endpoint.
    - Timeout: 5 seconds.
    - Gracefully catches all network/HTTP/API errors.
    - Never raises an exception to business logic.
    - Logs errors without exposing bot credentials.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    target_chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    if not token:
        logger.warning("Telegram notification skipped: TELEGRAM_BOT_TOKEN is not configured.")
        return False

    if not target_chat_id:
        logger.warning("Telegram notification skipped: TELEGRAM_CHAT_ID is not configured.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            if res_json.get("ok"):
                logger.info(
                    "Telegram message delivered successfully to chat %s. Message ID=%s",
                    target_chat_id,
                    res_json.get("result", {}).get("message_id"),
                )
                return True
            else:
                logger.error(
                    "Telegram API responded with error: %s",
                    _sanitize_log_text(res_body),
                )
                return False

    except urllib.error.HTTPError as http_err:
        err_msg = http_err.read().decode("utf-8", errors="replace")
        logger.error(
            "Telegram HTTP error %s for chat %s: %s",
            http_err.code,
            target_chat_id,
            _sanitize_log_text(err_msg),
        )
        return False

    except urllib.error.URLError as url_err:
        logger.error(
            "Telegram network connection error: %s",
            _sanitize_log_text(str(url_err.reason)),
        )
        return False

    except Exception as exc:
        logger.error(
            "Unexpected error sending Telegram notification: %s",
            _sanitize_log_text(str(exc)),
        )
        return False


def _dispatch_to_roles(text: str, roles: List[str]) -> bool:
    """
    Send formatted notification to targeted roles using role-aware routing.
    De-duplicates chat IDs so the same chat is not flooded during test mode.
    """
    target_chats = set()
    for role in roles:
        cid = get_chat_id_for_role(role)
        if cid:
            target_chats.add(cid)

    success = True
    for cid in target_chats:
        ok = send_telegram_message(text=text, chat_id=cid)
        if not ok:
            success = False
    return success


# ──────────────────────────────────────────────────────────────
#  Event-specific notification helpers
# ──────────────────────────────────────────────────────────────

def notify_medicine_approaching_expiry(
    medicine_name: str,
    batch_number: str,
    quantity: int,
    expiry_date: str,
    days_remaining: int,
    current_status: str,
    organization_name: str,
    timestamp: Optional[str] = None,
) -> bool:
    """EVENT 1: When a medicine approaches its expiry date."""
    ts = timestamp or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = (
        f"⚠️ <b>PHARMAMED ALERT: Medicine Approaching Expiry</b>\n\n"
        f"💊 <b>Medicine:</b> {html.escape(medicine_name)}\n"
        f"🔢 <b>Batch Number:</b> <code>{html.escape(batch_number)}</code>\n"
        f"📦 <b>Quantity:</b> {quantity} units\n"
        f"📅 <b>Expiry Date:</b> {html.escape(str(expiry_date))} ({days_remaining} days remaining)\n"
        f"📍 <b>Status:</b> {html.escape(current_status)}\n"
        f"🏢 <b>Location / Facility:</b> {html.escape(organization_name)}\n"
        f"⏰ <b>Timestamp:</b> {html.escape(ts)}"
    )
    return _dispatch_to_roles(msg, ["PHARMACY", "REGULATOR"])


def notify_return_created(
    medicine_name: str,
    batch_number: str,
    quantity: int,
    current_status: str,
    pharmacy_org: str,
    distributor_org: str,
    return_id: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """EVENT 2: When a return request is created (Target: Pharmacy + Distributor)."""
    ts = timestamp or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ret_str = f" #{return_id}" if return_id else ""
    msg = (
        f"🔄 <b>PHARMAMED EVENT: Return Request Initiated{ret_str}</b>\n\n"
        f"💊 <b>Medicine:</b> {html.escape(medicine_name)}\n"
        f"🔢 <b>Batch Number:</b> <code>{html.escape(batch_number)}</code>\n"
        f"📦 <b>Declared Quantity:</b> {quantity} units\n"
        f"📍 <b>Status:</b> {html.escape(current_status)}\n"
        f"🏥 <b>Initiated By (Pharmacy):</b> {html.escape(pharmacy_org)}\n"
        f"🚚 <b>Assigned Distributor:</b> {html.escape(distributor_org)}\n"
        f"⏰ <b>Timestamp:</b> {html.escape(ts)}"
    )
    return _dispatch_to_roles(msg, ["PHARMACY", "DISTRIBUTOR"])


def notify_return_approved(
    medicine_name: str,
    batch_number: str,
    quantity: int,
    distributor_org: str,
    pharmacy_org: str,
    return_id: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """EVENT 3: When a distributor approves a return (Target: Pharmacy + Distributor)."""
    ts = timestamp or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ret_str = f" #{return_id}" if return_id else ""
    msg = (
        f"✅ <b>PHARMAMED EVENT: Return Request Approved{ret_str}</b>\n\n"
        f"💊 <b>Medicine:</b> {html.escape(medicine_name)}\n"
        f"🔢 <b>Batch Number:</b> <code>{html.escape(batch_number)}</code>\n"
        f"📦 <b>Quantity:</b> {quantity} units\n"
        f"📍 <b>Status:</b> APPROVED (Ready for Pickup)\n"
        f"🚚 <b>Approved By:</b> {html.escape(distributor_org)}\n"
        f"🏥 <b>Pharmacy:</b> {html.escape(pharmacy_org)}\n"
        f"⏰ <b>Timestamp:</b> {html.escape(ts)}"
    )
    return _dispatch_to_roles(msg, ["PHARMACY", "DISTRIBUTOR"])


def notify_return_rejected(
    medicine_name: str,
    batch_number: str,
    quantity: int,
    distributor_org: str,
    pharmacy_org: str,
    reason: str = "Inspection criteria not met",
    return_id: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """EVENT 4: When a distributor rejects a return (Target: Pharmacy + Distributor)."""
    ts = timestamp or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ret_str = f" #{return_id}" if return_id else ""
    msg = (
        f"❌ <b>PHARMAMED EVENT: Return Request Rejected{ret_str}</b>\n\n"
        f"💊 <b>Medicine:</b> {html.escape(medicine_name)}\n"
        f"🔢 <b>Batch Number:</b> <code>{html.escape(batch_number)}</code>\n"
        f"📦 <b>Quantity:</b> {quantity} units\n"
        f"📍 <b>Status:</b> REJECTED\n"
        f"🚚 <b>Rejected By:</b> {html.escape(distributor_org)}\n"
        f"🏥 <b>Pharmacy:</b> {html.escape(pharmacy_org)}\n"
        f"⚠️ <b>Rejection Reason:</b> {html.escape(reason)}\n"
        f"⏰ <b>Timestamp:</b> {html.escape(ts)}"
    )
    return _dispatch_to_roles(msg, ["PHARMACY", "DISTRIBUTOR"])


def notify_pickup_completed(
    medicine_name: str,
    batch_number: str,
    quantity: int,
    distributor_org: str,
    pharmacy_org: str,
    return_id: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """EVENT 5: When pickup is completed (Target: Pharmacy)."""
    ts = timestamp or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ret_str = f" #{return_id}" if return_id else ""
    msg = (
        f"🚚 <b>PHARMAMED EVENT: Physical Pickup Completed{ret_str}</b>\n\n"
        f"💊 <b>Medicine:</b> {html.escape(medicine_name)}\n"
        f"🔢 <b>Batch Number:</b> <code>{html.escape(batch_number)}</code>\n"
        f"📦 <b>Quantity:</b> {quantity} units\n"
        f"📍 <b>Status:</b> PICKUP_CONFIRMED (In Transit)\n"
        f"🚚 <b>Carrier / Distributor:</b> {html.escape(distributor_org)}\n"
        f"🏥 <b>Picked Up From:</b> {html.escape(pharmacy_org)}\n"
        f"⏰ <b>Timestamp:</b> {html.escape(ts)}"
    )
    return _dispatch_to_roles(msg, ["PHARMACY"])


def notify_return_received(
    medicine_name: str,
    batch_number: str,
    declared_qty: int,
    received_qty: int,
    status: str,
    distributor_org: str,
    is_disputed: bool = False,
    return_id: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """EVENT 6A: When return is received by distributor (Target: Pharmacy + Distributor + Manufacturer)."""
    ts = timestamp or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    ret_str = f" #{return_id}" if return_id else ""
    status_icon = "⚠️" if is_disputed else "📦"
    status_title = "Return Intake Discrepancy" if is_disputed else "Return Received at Distributor"
    msg = (
        f"{status_icon} <b>PHARMAMED EVENT: {status_title}{ret_str}</b>\n\n"
        f"💊 <b>Medicine:</b> {html.escape(medicine_name)}\n"
        f"🔢 <b>Batch Number:</b> <code>{html.escape(batch_number)}</code>\n"
        f"📦 <b>Declared:</b> {declared_qty} | <b>Received:</b> {received_qty} units\n"
        f"📍 <b>Status:</b> {html.escape(status)}\n"
        f"🏢 <b>Warehouse:</b> {html.escape(distributor_org)}\n"
        f"⏰ <b>Timestamp:</b> {html.escape(ts)}"
    )
    return _dispatch_to_roles(msg, ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER"])


def notify_disposal_closure_completed(
    medicine_name: str,
    batch_number: str,
    quantity: int,
    certificate_number: str,
    verifier_org: str,
    facility_org: str,
    timestamp: Optional[str] = None,
) -> bool:
    """EVENT 6B: When disposal and regulatory verification are completed (Target: Manufacturer + Facility)."""
    ts = timestamp or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = (
        f"🏁 <b>PHARMAMED EVENT: Reverse Chain Closed & Verified</b>\n\n"
        f"💊 <b>Medicine:</b> {html.escape(medicine_name)}\n"
        f"🔢 <b>Batch Number:</b> <code>{html.escape(batch_number)}</code>\n"
        f"📦 <b>Destroyed Quantity:</b> {quantity} units\n"
        f"📜 <b>Certificate No:</b> <code>{html.escape(certificate_number)}</code>\n"
        f"📍 <b>Final Status:</b> CLOSED (Cryptographically Sealed)\n"
        f"🏛️ <b>Verified By:</b> {html.escape(verifier_org)}\n"
        f"🏭 <b>Facility:</b> {html.escape(facility_org)}\n"
        f"⏰ <b>Timestamp:</b> {html.escape(ts)}"
    )
    return _dispatch_to_roles(msg, ["MANUFACTURER", "FACILITY"])

def notify_re_entry_fraud_detected(
    medicine_name: str,
    batch_number: str,
    flagged_status: str,
    pharmacy_org: str,
    location: str,
    timestamp: Optional[str] = None,
) -> bool:
    """EVENT 7: When a DESTROYED/in-pipeline batch is rescanned at point-of-sale (fraud re-entry)."""
    ts = timestamp or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = (
        f"🚨 <b>PHARMAMED CRITICAL ALERT: Re-Entry Fraud Detected</b>\n\n"
        f"💊 <b>Medicine:</b> {html.escape(medicine_name)}\n"
        f"🔢 <b>Batch Number:</b> <code>{html.escape(batch_number)}</code>\n"
        f"⛔ <b>Recorded Status:</b> {html.escape(flagged_status)} (should not be sellable)\n"
        f"🏥 <b>Flagged At:</b> {html.escape(pharmacy_org)}\n"
        f"📍 <b>Location:</b> {html.escape(location)}\n"
        f"⏰ <b>Timestamp:</b> {html.escape(ts)}\n\n"
        f"Sale has been automatically blocked."
    )
    return _dispatch_to_roles(msg, ["REGULATOR", "MANUFACTURER"])