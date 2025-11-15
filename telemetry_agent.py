"""Main telemetry agent for collecting GPS data from Signal K and pushing to Supabase."""
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from supabase import create_client, Client

from config import Config


class SignalKClient:
    """Client for fetching data from Signal K server."""

    def __init__(self, url: str, token: Optional[str] = None):
        self.url = url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get_gps_position(self) -> Optional[dict]:
        """
        Fetch current GPS position from Signal K.

        Returns:
            dict with keys: latitude, longitude, altitude (optional),
            speed_over_ground (optional), course_over_ground (optional), timestamp
            Returns None if data unavailable or error occurs.
        """
        try:
            # Signal K REST API endpoint for navigation data
            response = self.session.get(
                f"{self.url}/signalk/v1/api/vessels/self/navigation/position",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            if not data or "value" not in data:
                logging.warning("No position data available from Signal K")
                return None

            position = data["value"]
            timestamp = data.get("timestamp", datetime.now(timezone.utc).isoformat())

            # Get additional navigation data
            speed_response = self.session.get(
                f"{self.url}/signalk/v1/api/vessels/self/navigation/speedOverGround",
                timeout=5
            )
            course_response = self.session.get(
                f"{self.url}/signalk/v1/api/vessels/self/navigation/courseOverGroundTrue",
                timeout=5
            )

            speed = None
            course = None

            if speed_response.ok:
                speed_data = speed_response.json()
                if speed_data and "value" in speed_data:
                    speed = speed_data["value"]  # m/s

            if course_response.ok:
                course_data = course_response.json()
                if course_data and "value" in course_data:
                    course = course_data["value"]  # radians

            return {
                "latitude": position.get("latitude"),
                "longitude": position.get("longitude"),
                "altitude": position.get("altitude"),
                "speed_over_ground": speed,
                "course_over_ground": course,
                "timestamp": timestamp,
            }

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch GPS position from Signal K: {e}")
            return None
        except (KeyError, ValueError) as e:
            logging.error(f"Failed to parse GPS data from Signal K: {e}")
            return None


class TelemetryAgent:
    """Main telemetry agent for collecting and storing GPS data."""

    def __init__(self, config: Config):
        self.config = config
        self.signalk = SignalKClient(config.signalk_url, config.signalk_token)
        self.supabase: Client = create_client(
            config.supabase_url,
            config.supabase_service_role_key
        )
        self.logger = logging.getLogger(__name__)

    def store_gps_position(self, gps_data: dict) -> bool:
        """
        Store GPS position data in Supabase.

        Args:
            gps_data: GPS data dictionary from Signal K

        Returns:
            True if successful, False otherwise
        """
        try:
            record = {
                "boat_id": self.config.boat_id,
                "latitude": gps_data["latitude"],
                "longitude": gps_data["longitude"],
                "altitude": gps_data.get("altitude"),
                "speed_over_ground": gps_data.get("speed_over_ground"),
                "course_over_ground": gps_data.get("course_over_ground"),
                "timestamp": gps_data["timestamp"],
            }

            result = self.supabase.table("gps_position").insert(record).execute()

            if result.data:
                self.logger.info(
                    f"Stored GPS position: lat={gps_data['latitude']:.6f}, "
                    f"lon={gps_data['longitude']:.6f}"
                )
                return True
            else:
                self.logger.error("Failed to store GPS position: no data returned")
                return False

        except Exception as e:
            self.logger.error(f"Failed to store GPS position in Supabase: {e}")
            return False

    def run(self):
        """Main loop: fetch GPS data and store every N seconds."""
        self.logger.info(
            f"Starting telemetry agent for boat '{self.config.boat_id}' "
            f"(poll interval: {self.config.poll_interval_seconds}s)"
        )

        consecutive_failures = 0
        max_consecutive_failures = 5

        while True:
            try:
                # Fetch GPS position from Signal K
                gps_data = self.signalk.get_gps_position()

                if gps_data:
                    # Store in Supabase
                    if self.store_gps_position(gps_data):
                        consecutive_failures = 0  # Reset on success
                    else:
                        consecutive_failures += 1
                else:
                    self.logger.warning("No GPS data available, skipping this cycle")
                    consecutive_failures += 1

                # Check if we're having too many failures
                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error(
                        f"Too many consecutive failures ({consecutive_failures}), "
                        "but continuing to retry..."
                    )
                    # Don't exit, just log and continue

                # Wait for next poll interval
                time.sleep(self.config.poll_interval_seconds)

            except KeyboardInterrupt:
                self.logger.info("Received shutdown signal, stopping telemetry agent")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                consecutive_failures += 1
                time.sleep(self.config.poll_interval_seconds)


def setup_logging(log_level: str):
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("telemetry_agent.log"),
        ],
    )


def main():
    """Main entry point."""
    try:
        # Load configuration
        config = Config.from_env()

        # Setup logging
        setup_logging(config.log_level)

        # Create and run agent
        agent = TelemetryAgent(config)
        agent.run()

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
