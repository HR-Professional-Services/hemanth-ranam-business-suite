import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "HR Professional Services Business Suite"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "127.0.0.1")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-insecure-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    SESSION_EXPIRE_MINUTES: int = int(os.getenv("SESSION_EXPIRE_MINUTES", "1440"))
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "business_suite.db")))
    
    # Gateways
    CRM_URL: str = os.getenv("CRM_URL", "http://127.0.0.1:8002")
    ACCOUNTS_URL: str = os.getenv("ACCOUNTS_URL", "http://127.0.0.1:8003")
    HRMS_URL: str = os.getenv("HRMS_URL", "http://127.0.0.1:8004")
    ERP_URL: str = os.getenv("ERP_URL", "http://127.0.0.1:8005")
    HELPDESK_URL: str = os.getenv("HELPDESK_URL", "http://127.0.0.1:8006")
    BOOKING_URL: str = os.getenv("BOOKING_URL", "http://127.0.0.1:8007")
    CLIENT_PORTAL_URL: str = os.getenv("CLIENT_PORTAL_URL", "http://127.0.0.1:8009")

settings = Settings()
