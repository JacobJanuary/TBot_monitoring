"""Configuration for monitoring UI."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)


class Config:
    """Application configuration."""

    # Database configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "fox_crypto")
    DB_USER = os.getenv("DB_USER", "evgeniyyanvarskiy")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # Connection pool settings
    DB_MIN_POOL_SIZE = int(os.getenv("DB_MIN_POOL_SIZE", "2"))
    DB_MAX_POOL_SIZE = int(os.getenv("DB_MAX_POOL_SIZE", "5"))

    # Update intervals (seconds)
    POSITION_UPDATE_INTERVAL = float(os.getenv("POSITION_UPDATE_INTERVAL", "1.0"))
    EVENT_UPDATE_INTERVAL = float(os.getenv("EVENT_UPDATE_INTERVAL", "1.0"))
    STATUS_UPDATE_INTERVAL = float(os.getenv("STATUS_UPDATE_INTERVAL", "5.0"))
    STATS_UPDATE_INTERVAL = float(os.getenv("STATS_UPDATE_INTERVAL", "10.0"))

    # Web server settings
    WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT = int(os.getenv("WEB_PORT", "8080"))

    # UI settings
    MAX_EVENTS_DISPLAY = int(os.getenv("MAX_EVENTS_DISPLAY", "100"))
    POSITION_AGE_WARNING_HOURS = int(os.getenv("POSITION_AGE_WARNING_HOURS", "12"))
    POSITION_AGE_CRITICAL_HOURS = int(os.getenv("POSITION_AGE_CRITICAL_HOURS", "24"))

    # Signal WebSocket
    SIGNAL_WS_URL = os.getenv("SIGNAL_WS_URL", "")
    SIGNAL_WS_TOKEN = os.getenv("SIGNAL_WS_TOKEN", "")
    SIGNAL_WS_RECONNECT_INTERVAL = int(os.getenv("SIGNAL_WS_RECONNECT_INTERVAL", "5"))

    # Binance API
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    BINANCE_UPDATE_INTERVAL = float(os.getenv("BINANCE_UPDATE_INTERVAL", "10.0"))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "monitor_ui.log")

    @classmethod
    def get_db_url(cls) -> str:
        """Get PostgreSQL connection URL."""
        password_part = f":{cls.DB_PASSWORD}" if cls.DB_PASSWORD else ""
        return f"postgresql://{cls.DB_USER}{password_part}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

    @classmethod
    def to_dict(cls) -> dict:
        """Convert config to dictionary."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if key.isupper() and not key.startswith("_")
        }


# Example .env file content (create this file manually if needed):
"""
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fox_crypto
DB_USER=evgeniyyanvarskiy
DB_PASSWORD=

DB_MIN_POOL_SIZE=2
DB_MAX_POOL_SIZE=5

POSITION_UPDATE_INTERVAL=1.0
EVENT_UPDATE_INTERVAL=1.0
STATUS_UPDATE_INTERVAL=5.0
STATS_UPDATE_INTERVAL=10.0

MAX_EVENTS_DISPLAY=50
POSITION_AGE_WARNING_HOURS=12
POSITION_AGE_CRITICAL_HOURS=24

LOG_LEVEL=INFO
LOG_FILE=monitor_ui.log
"""
