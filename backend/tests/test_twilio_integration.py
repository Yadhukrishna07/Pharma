"""
Minimal unit tests for Twilio WhatsApp role routing.
Run with:
    pytest tests/test_twilio_integration.py -v

Testing mode:
ALL roles use the same WhatsApp number:
    whatsapp:+919791191427
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from app.config import settings

PATCH_TARGET = "app.services.twilio_service.send_whatsapp"

TEST_NUMBER = "whatsapp:+919791191427"


def _mock_db():
    """Return a db mock that returns an empty user list."""
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    return db


class TestTwilioModeOff(unittest.TestCase):
    """When TWILIO_TEST_MODE=False, send_whatsapp must NEVER be called."""

    def setUp(self):
        settings.TWILIO_TEST_MODE = False

    def tearDown(self):
        settings.TWILIO_TEST_MODE = (
            os.getenv("TWILIO_TEST_MODE", "false").lower() == "true"
        )

    @patch(PATCH_TARGET)
    def test_no_twilio_calls_when_mode_off(self, mock_send):
        from app.services.notification_service import notify_by_role

        notify_by_role(
            _mock_db(),
            ["PHARMACY", "DISTRIBUTOR"],
            "Test",
            "body"
        )

        mock_send.assert_not_called()


class TestTwilioModeOn(unittest.TestCase):
    """
    When TWILIO_TEST_MODE=True, every role uses
    whatsapp:+919791191427.
    """

    def setUp(self):
        settings.TWILIO_TEST_MODE = True

        # Mock value only for unit tests.
        # DO NOT use this fake SID in .env or real Twilio requests.
        settings.TWILIO_CONTENT_SID = "HXmockcontent123"

        # ALL roles use the same testing number.
        settings.TEST_PHARMACY_WHATSAPP = TEST_NUMBER
        settings.TEST_DISTRIBUTOR_WHATSAPP = TEST_NUMBER
        settings.TEST_MANUFACTURER_WHATSAPP = TEST_NUMBER
        settings.TEST_DISPOSAL_WHATSAPP = TEST_NUMBER

    def tearDown(self):
        settings.TWILIO_TEST_MODE = (
            os.getenv("TWILIO_TEST_MODE", "false").lower() == "true"
        )

    @patch(PATCH_TARGET)
    def test_return_request_created_routes_pharmacy_distributor(self, mock_send):
        from app.services.notification_service import notify_by_role

        notify_by_role(
            _mock_db(),
            ["PHARMACY", "DISTRIBUTOR"],
            "Return Created",
            "A new return was created"
        )

        tos = [c.args[0] for c in mock_send.call_args_list]

        self.assertEqual(
            tos,
            [TEST_NUMBER, TEST_NUMBER]
        )

    @patch(PATCH_TARGET)
    def test_pickup_confirmed_routes_pharmacy_only(self, mock_send):
        from app.services.notification_service import notify_by_role

        notify_by_role(
            _mock_db(),
            ["PHARMACY"],
            "Pickup Confirmed",
            "Your pickup has been confirmed"
        )

        tos = [c.args[0] for c in mock_send.call_args_list]

        self.assertEqual(
            tos,
            [TEST_NUMBER]
        )

    @patch(PATCH_TARGET)
    def test_return_received_routes_three_roles(self, mock_send):
        from app.services.notification_service import notify_by_role

        notify_by_role(
            _mock_db(),
            ["PHARMACY", "DISTRIBUTOR", "MANUFACTURER"],
            "Return Received",
            "Return has been accepted"
        )

        tos = [c.args[0] for c in mock_send.call_args_list]

        self.assertEqual(
            tos,
            [TEST_NUMBER, TEST_NUMBER, TEST_NUMBER]
        )

    @patch(PATCH_TARGET)
    def test_disposal_routes_manufacturer_and_facility(self, mock_send):
        from app.services.notification_service import notify_by_role

        notify_by_role(
            _mock_db(),
            ["MANUFACTURER", "DISPOSAL_FACILITY"],
            "Disposal Completed",
            "Drug batch has been destroyed"
        )

        tos = [c.args[0] for c in mock_send.call_args_list]

        self.assertEqual(
            tos,
            [TEST_NUMBER, TEST_NUMBER]
        )

    @patch("app.services.twilio_service.Client")
    def test_twilio_error_does_not_propagate(self, mock_client_cls):
        """A Twilio SDK failure must never raise an exception to the caller."""

        mock_client_cls.return_value.messages.create.side_effect = Exception(
            "Twilio API error"
        )

        from app.services.notification_service import notify_by_role

        # Should complete without raising.
        result = notify_by_role(
            _mock_db(),
            ["PHARMACY"],
            "Test",
            "body"
        )

        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()