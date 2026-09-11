"""
Quick script to verify Twilio config is loaded correctly.
Run from backend dir:  python test_config.py
"""
import sys
sys.path.insert(0, ".")
from app.config import settings

print("=" * 50)
print("Twilio Configuration Check")
print("=" * 50)
print(f"TWILIO_TEST_MODE      : {settings.TWILIO_TEST_MODE}")
print(f"TWILIO_ACCOUNT_SID    : {'SET (' + settings.TWILIO_ACCOUNT_SID[:8] + '...)' if settings.TWILIO_ACCOUNT_SID else 'NOT SET'}")
print(f"TWILIO_AUTH_TOKEN     : {'SET' if settings.TWILIO_AUTH_TOKEN else 'NOT SET'}")
print(f"TWILIO_FROM_WHATSAPP  : {settings.TWILIO_FROM_WHATSAPP or 'NOT SET'}")
print(f"TWILIO_CONTENT_SID    : {settings.TWILIO_CONTENT_SID or 'NOT SET'}")
print(f"TEST_PHARMACY         : {settings.TEST_PHARMACY_WHATSAPP or 'NOT SET'}")
print(f"TEST_DISTRIBUTOR      : {settings.TEST_DISTRIBUTOR_WHATSAPP or 'NOT SET'}")
print(f"TEST_MANUFACTURER     : {settings.TEST_MANUFACTURER_WHATSAPP or 'NOT SET'}")
print(f"TEST_DISPOSAL         : {settings.TEST_DISPOSAL_WHATSAPP or 'NOT SET'}")
print("=" * 50)
