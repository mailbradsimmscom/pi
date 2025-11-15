"""Configuration management for the telemetry agent."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration for the telemetry agent."""

    # Signal K
    signalk_url: str
    signalk_token: str | None

    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # Boat
    boat_id: str

    # Telemetry
    poll_interval_seconds: int

    # Logging
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Required variables
        required_vars = [
            "SIGNALK_URL",
            "SUPABASE_URL",
            "PY_SUPABASE_SERVICE_KEY",
            "BOAT_ID",
        ]

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            signalk_url=os.getenv("SIGNALK_URL"),
            signalk_token=os.getenv("SIGNALK_TOKEN"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_service_role_key=os.getenv("PY_SUPABASE_SERVICE_KEY"),
            boat_id=os.getenv("BOAT_ID"),
            poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
