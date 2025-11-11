import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

# Database Configuration
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///sales_orders.db")

# AI Configuration
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

# Email Configuration
IMAP_SERVER: str = os.getenv("IMAP_SERVER", "imap.gmail.com")
SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
EMAIL_ACCOUNT: Optional[str] = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")

# Application Configuration
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
PORT: int = int(os.getenv("PORT", "8000"))

# Worker Configuration
WORKER_EMAIL_INTERVAL_MINUTES: int = int(os.getenv("WORKER_EMAIL_INTERVAL_MINUTES", "2"))
WORKER_WORKFLOW_INTERVAL_SECONDS: int = int(os.getenv("WORKER_WORKFLOW_INTERVAL_SECONDS", "60"))

# Security Configuration
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

def validate_configuration() -> list:
    """Validate required configuration and return list of missing items"""
    missing = []

    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")

    if not EMAIL_ACCOUNT or not EMAIL_PASSWORD:
        missing.append("EMAIL_ACCOUNT and EMAIL_PASSWORD")

    if not DATABASE_URL:
        missing.append("DATABASE_URL")

    return missing

def get_database_url() -> str:
    """Get database URL with proper handling for different environments"""
    return DATABASE_URL

def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"

def get_cors_origins() -> list:
    """Get CORS allowed origins"""
    return [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]
