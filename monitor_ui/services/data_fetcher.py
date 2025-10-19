"""Data fetching service with async polling."""
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from database.connection import DatabasePool
from database.models import PositionView, EventView, StatsView, SystemStatus
from database import queries

logger = logging.getLogger(__name__)


class DataFetcher:
    """Async data fetcher with caching and error handling."""

    def __init__(self):
        self.running = False
        self.last_event_time = datetime.now() - timedelta(minutes=5)

        # Cached data
        self.positions_cache: List[PositionView] = []
        self.events_cache: List[EventView] = []
        self.stats_cache: Optional[StatsView] = None
        self.status_cache: Optional[SystemStatus] = None

        # Error tracking
        self.error_count = 0
        self.max_errors = 5
        self.last_error: Optional[str] = None

        # Performance metrics
        self.start_time = datetime.now()

    async def fetch_active_positions(self) -> List[PositionView]:
        """Fetch all active positions with trailing stop info."""
        try:
            pool = await DatabasePool.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(queries.ACTIVE_POSITIONS_QUERY)
                positions = []
                for row in rows:
                    try:
                        pos_dict = dict(row)
                        positions.append(PositionView(**pos_dict))
                    except Exception as e:
                        logger.warning(f"Failed to parse position: {e}")
                        continue

                self.error_count = 0
                return positions

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Failed to fetch positions: {e}")

            # Return cached data on error
            if self.error_count < self.max_errors:
                return self.positions_cache
            else:
                logger.critical(f"Max errors reached ({self.max_errors})")
                return []

    async def fetch_recent_events(self) -> List[EventView]:
        """Fetch events since last poll."""
        try:
            pool = await DatabasePool.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    queries.RECENT_EVENTS_QUERY, self.last_event_time
                )

                events = []
                for row in rows:
                    try:
                        event_dict = dict(row)
                        events.append(EventView(**event_dict))
                    except Exception as e:
                        logger.warning(f"Failed to parse event: {e}")
                        continue

                # Update last event time if we got events
                if events:
                    self.last_event_time = events[0].created_at

                return events

        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return []

    async def fetch_statistics(self) -> Optional[StatsView]:
        """Fetch hourly statistics."""
        try:
            pool = await DatabasePool.get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(queries.STATISTICS_QUERY)
                if row:
                    stats_dict = dict(row)
                    return StatsView(**stats_dict)
                return None

        except Exception as e:
            logger.error(f"Failed to fetch statistics: {e}")
            return self.stats_cache

    async def fetch_system_status(self) -> Optional[SystemStatus]:
        """Fetch system status."""
        try:
            pool = await DatabasePool.get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(queries.SYSTEM_STATUS_QUERY)
                if row:
                    uptime = (datetime.now() - self.start_time).total_seconds()
                    status = SystemStatus(
                        status="RUNNING" if self.error_count < self.max_errors else "ERROR",
                        uptime_seconds=uptime,
                        active_positions=row["active_positions"],
                        total_exposure=row["total_exposure"],
                        last_update=datetime.now(),
                    )
                    return status
                return None

        except Exception as e:
            logger.error(f"Failed to fetch system status: {e}")
            return self.status_cache

    async def start_polling(self):
        """Start all polling tasks."""
        self.running = True
        logger.info("Starting data fetcher polling loops")

        # Run all polling tasks concurrently
        await asyncio.gather(
            self._poll_positions(),
            self._poll_events(),
            self._poll_statistics(),
            self._poll_status(),
            return_exceptions=True,
        )

    async def stop_polling(self):
        """Stop all polling tasks."""
        self.running = False
        logger.info("Stopping data fetcher")

    async def _poll_positions(self):
        """Poll positions every 1 second."""
        while self.running:
            try:
                positions = await self.fetch_active_positions()
                if positions is not None:
                    self.positions_cache = positions
            except Exception as e:
                logger.error(f"Position polling error: {e}")

            await asyncio.sleep(1.0)

    async def _poll_events(self):
        """Poll events every 1 second."""
        while self.running:
            try:
                new_events = await self.fetch_recent_events()
                if new_events:
                    # Prepend new events to cache
                    self.events_cache = new_events + self.events_cache
                    # Keep only last 100 events
                    self.events_cache = self.events_cache[:100]
            except Exception as e:
                logger.error(f"Event polling error: {e}")

            await asyncio.sleep(1.0)

    async def _poll_statistics(self):
        """Poll statistics every 10 seconds."""
        while self.running:
            try:
                stats = await self.fetch_statistics()
                if stats:
                    self.stats_cache = stats
            except Exception as e:
                logger.error(f"Statistics polling error: {e}")

            await asyncio.sleep(10.0)

    async def _poll_status(self):
        """Poll system status every 5 seconds."""
        while self.running:
            try:
                status = await self.fetch_system_status()
                if status:
                    self.status_cache = status
            except Exception as e:
                logger.error(f"Status polling error: {e}")

            await asyncio.sleep(5.0)

    def get_positions(self) -> List[PositionView]:
        """Get cached positions."""
        return self.positions_cache

    def get_events(self) -> List[EventView]:
        """Get cached events."""
        return self.events_cache

    def get_statistics(self) -> Optional[StatsView]:
        """Get cached statistics."""
        return self.stats_cache

    def get_status(self) -> Optional[SystemStatus]:
        """Get cached system status."""
        return self.status_cache

    def has_errors(self) -> bool:
        """Check if there are connection errors."""
        return self.error_count >= self.max_errors
