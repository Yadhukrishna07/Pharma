import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pharmamedian")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    
    # Twilio configuration (added)
    TWILIO_TEST_MODE: bool = os.getenv("TWILIO_TEST_MODE", "false").lower() == "true"
    TWILIO_ACCOUNT_SID: str | None = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: str | None = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_WHATSAPP: str | None = os.getenv("TWILIO_FROM_WHATSAPP")
    TWILIO_CONTENT_SID: str | None = os.getenv("TWILIO_CONTENT_SID")
    TEST_PHARMACY_WHATSAPP: str | None = os.getenv("TEST_PHARMACY_WHATSAPP")
    TEST_DISTRIBUTOR_WHATSAPP: str | None = os.getenv("TEST_DISTRIBUTOR_WHATSAPP")
    TEST_MANUFACTURER_WHATSAPP: str | None = os.getenv("TEST_MANUFACTURER_WHATSAPP")
    TEST_DISPOSAL_WHATSAPP: str | None = os.getenv("TEST_DISPOSAL_WHATSAPP")

settings = Settings()
