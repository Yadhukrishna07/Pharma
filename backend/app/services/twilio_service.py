import json
import logging

from twilio.rest import Client

from app.config import settings

log = logging.getLogger(__name__)


def _get_client() -> Client | None:
    """Create a Twilio client when credentials are configured."""

    if not settings.TWILIO_ACCOUNT_SID:
        log.warning("TWILIO_ACCOUNT_SID is not configured.")
        return None

    if not settings.TWILIO_AUTH_TOKEN:
        log.warning("TWILIO_AUTH_TOKEN is not configured.")
        return None

    try:
        return Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
    except Exception as exc:
        log.error("Failed to create Twilio client: %s", exc)
        return None


def send_whatsapp(
    to: str,
    body: str,
    content_variables: dict | None = None,
) -> None:
    """
    Send a WhatsApp message using the configured Twilio Content Template.

    Twilio failures are logged and do not break the main
    PharmaMedian business workflow.
    """

    # Test mode check
    if not settings.TWILIO_TEST_MODE:
        log.info("Twilio test mode disabled. WhatsApp message skipped.")
        return

    if not to:
        log.warning("WhatsApp recipient is empty. Message skipped.")
        return

    client = _get_client()

    if client is None:
        return

    content_sid = settings.TWILIO_CONTENT_SID

    if not content_sid:
        log.warning(
            "TWILIO_CONTENT_SID is not configured. "
            "WhatsApp message skipped."
        )
        return

    try:
        # These variables MUST match the variables
        # configured in your Twilio template.
        variables = content_variables or {
            "1": "PharmaMedian",
            "2": "Return Notification",
            "3": body,
        }

        message = client.messages.create(
            from_=settings.TWILIO_FROM_WHATSAPP,
            to=to,
            content_sid=content_sid,
            content_variables=json.dumps(variables),
        )

        log.info(
            "WhatsApp message sent successfully. SID=%s To=%s",
            message.sid,
            to,
        )

    except Exception as exc:
        # Never allow WhatsApp failure to break the application.
        log.error(
            "Failed to send WhatsApp message to %s: %s",
            to,
            exc,
        )