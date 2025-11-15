"""Tiered retention cleanup for GPS telemetry data."""
import logging
import sys
from datetime import datetime, timezone
from typing import Dict

from supabase import create_client, Client

from config import Config


class TelemetryCleanup:
    """Manages tiered retention cleanup of GPS telemetry data."""

    def __init__(self, config: Config, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.supabase: Client = create_client(
            config.supabase_url,
            config.supabase_service_role_key
        )
        self.logger = logging.getLogger(__name__)

    def cleanup_tier_2(self) -> Dict[str, int]:
        """
        Tier 2: 7-30 days old - Keep 1 record per minute.

        Returns:
            dict with 'kept' and 'deleted' counts
        """
        self.logger.info("Starting Tier 2 cleanup (7-30 days old → 1 per minute)")
        return self._cleanup_tier_2_batch()

    def _cleanup_tier_2_batch(self) -> Dict[str, int]:
        """Tier 2 cleanup using batch processing."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=30)
        end_date = now - timedelta(days=7)

        total_deleted = 0
        total_would_delete = 0

        # Process day by day to avoid loading too much into memory
        current_date = start_date
        while current_date < end_date:
            next_date = current_date + timedelta(days=1)

            # Fetch all records for this day
            result = self.supabase.table('gps_position').select('id, timestamp').eq(
                'boat_id', self.config.boat_id
            ).gte(
                'timestamp', current_date.isoformat()
            ).lt(
                'timestamp', next_date.isoformat()
            ).execute()

            if not result.data:
                current_date = next_date
                continue

            # Group by minute and keep only first record
            records_by_minute = {}
            for record in result.data:
                ts = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                minute_key = ts.strftime('%Y-%m-%d %H:%M')

                if minute_key not in records_by_minute:
                    records_by_minute[minute_key] = []
                records_by_minute[minute_key].append(record['id'])

            # Delete all but the first record in each minute
            ids_to_delete = []
            for minute_records in records_by_minute.values():
                if len(minute_records) > 1:
                    ids_to_delete.extend(minute_records[1:])  # Keep first, delete rest

            if ids_to_delete:
                if self.dry_run:
                    total_would_delete += len(ids_to_delete)
                    self.logger.info(f"[DRY RUN] Tier 2: Would delete {len(ids_to_delete)} records from {current_date.date()}")
                else:
                    # Delete in batches of 1000
                    for i in range(0, len(ids_to_delete), 1000):
                        batch = ids_to_delete[i:i+1000]
                        self.supabase.table('gps_position').delete().in_(
                            'id', batch
                        ).execute()
                        total_deleted += len(batch)

                    self.logger.info(f"Tier 2: Deleted {len(ids_to_delete)} records from {current_date.date()}")

            current_date = next_date

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Tier 2: Would delete {total_would_delete} total records")
            return {'kept': 0, 'deleted': 0, 'would_delete': total_would_delete}
        else:
            self.logger.info(f"Tier 2 cleanup complete: {total_deleted} records deleted")
            return {'kept': 0, 'deleted': total_deleted}

    def cleanup_tier_3(self) -> Dict[str, int]:
        """
        Tier 3: 30-90 days old - Keep 1 record per 10 minutes.

        Returns:
            dict with 'kept' and 'deleted' counts
        """
        self.logger.info("Starting Tier 3 cleanup (30-90 days old → 1 per 10 minutes)")

        from datetime import timedelta

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=90)
        end_date = now - timedelta(days=30)

        total_deleted = 0
        total_would_delete = 0

        # Process day by day
        current_date = start_date
        while current_date < end_date:
            next_date = current_date + timedelta(days=1)

            # Fetch all records for this day
            result = self.supabase.table('gps_position').select('id, timestamp').eq(
                'boat_id', self.config.boat_id
            ).gte(
                'timestamp', current_date.isoformat()
            ).lt(
                'timestamp', next_date.isoformat()
            ).execute()

            if not result.data:
                current_date = next_date
                continue

            # Group by 10-minute interval and keep only first record
            records_by_interval = {}
            for record in result.data:
                ts = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                # Round down to 10-minute interval
                interval_minute = (ts.minute // 10) * 10
                interval_key = ts.strftime(f'%Y-%m-%d %H:{interval_minute:02d}')

                if interval_key not in records_by_interval:
                    records_by_interval[interval_key] = []
                records_by_interval[interval_key].append(record['id'])

            # Delete all but the first record in each 10-minute interval
            ids_to_delete = []
            for interval_records in records_by_interval.values():
                if len(interval_records) > 1:
                    ids_to_delete.extend(interval_records[1:])  # Keep first, delete rest

            if ids_to_delete:
                if self.dry_run:
                    total_would_delete += len(ids_to_delete)
                    self.logger.info(f"[DRY RUN] Tier 3: Would delete {len(ids_to_delete)} records from {current_date.date()}")
                else:
                    # Delete in batches of 1000
                    for i in range(0, len(ids_to_delete), 1000):
                        batch = ids_to_delete[i:i+1000]
                        self.supabase.table('gps_position').delete().in_(
                            'id', batch
                        ).execute()
                        total_deleted += len(batch)

                    self.logger.info(f"Tier 3: Deleted {len(ids_to_delete)} records from {current_date.date()}")

            current_date = next_date

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Tier 3: Would delete {total_would_delete} total records")
            return {'kept': 0, 'deleted': 0, 'would_delete': total_would_delete}
        else:
            self.logger.info(f"Tier 3 cleanup complete: {total_deleted} records deleted")
            return {'kept': 0, 'deleted': total_deleted}

    def cleanup_old_data(self, days: int = 90) -> int:
        """
        Delete all records older than specified days.

        Args:
            days: Delete records older than this many days

        Returns:
            Number of records deleted
        """
        self.logger.info(f"Deleting records older than {days} days")

        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        if self.dry_run:
            result = self.supabase.table('gps_position').select(
                'id', count='exact'
            ).eq(
                'boat_id', self.config.boat_id
            ).lt(
                'timestamp', cutoff_date.isoformat()
            ).execute()

            would_delete = result.count or 0
            self.logger.info(f"[DRY RUN] Would delete {would_delete} records older than {days} days")
            return 0

        # Delete in batches to avoid timeouts
        total_deleted = 0
        batch_size = 1000

        while True:
            result = self.supabase.table('gps_position').delete().eq(
                'boat_id', self.config.boat_id
            ).lt(
                'timestamp', cutoff_date.isoformat()
            ).limit(batch_size).execute()

            deleted_count = len(result.data) if result.data else 0
            total_deleted += deleted_count

            if deleted_count < batch_size:
                break  # No more records to delete

        self.logger.info(f"Deleted {total_deleted} records older than {days} days")
        return total_deleted

    def run_full_cleanup(self):
        """Run complete tiered cleanup process."""
        self.logger.info("=" * 60)
        self.logger.info(f"Starting tiered cleanup for boat '{self.config.boat_id}'")
        if self.dry_run:
            self.logger.info("DRY RUN MODE - No data will be deleted")
        self.logger.info("=" * 60)

        # Tier 2: 7-30 days → 1 per minute
        tier2_result = self.cleanup_tier_2()

        # Tier 3: 30-90 days → 1 per 10 minutes
        tier3_result = self.cleanup_tier_3()

        # Delete records older than 90 days
        old_deleted = self.cleanup_old_data(days=90)

        # Summary
        total_deleted = tier2_result.get('deleted', 0) + tier3_result.get('deleted', 0) + old_deleted

        self.logger.info("=" * 60)
        self.logger.info(f"Cleanup complete! Total deleted: {total_deleted} records")
        self.logger.info("=" * 60)


def setup_logging(log_level: str):
    """Configure logging for the cleanup script."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("telemetry_cleanup.log"),
        ],
    )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Tiered retention cleanup for GPS telemetry')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    args = parser.parse_args()

    try:
        # Load configuration
        config = Config.from_env()

        # Setup logging
        setup_logging(config.log_level)

        # Run cleanup
        cleanup = TelemetryCleanup(config, dry_run=args.dry_run)
        cleanup.run_full_cleanup()

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        logging.error(f"Fatal error during cleanup: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
