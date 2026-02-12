"""DataFetcher — async database polling service for the web dashboard."""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from database.queries import (
    ACTIVE_POSITIONS_QUERY,
    RECENT_EVENTS_QUERY,
    STATISTICS_QUERY,
    SYSTEM_STATUS_QUERY,
    HISTORICAL_PNL_QUERY,
    DAILY_PNL_QUERY,
    TRAILING_STOP_DETAILS_QUERY,
    RISK_EVENTS_QUERY,
    RECENT_TRADES_QUERY,
    EVENT_SEVERITY_COUNTS_QUERY,
    PERFORMANCE_SUMMARY_QUERY,
    HEALTH_CHECK_QUERY,
)
from database.models import (
    PositionView,
    EventView,
    StatsView,
    SystemStatus,
    TrailingStopView,
    RiskEventView,
    RecentTradeView,
    PnlDataPoint,
    PerformanceMetricView,
)

logger = logging.getLogger(__name__)


def _to_float(val) -> Optional[float]:
    """Convert Decimal or any numeric to float."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def _row_to_dict(row) -> dict:
    """Convert asyncpg Record to dict with Decimal→float coercion."""
    d = {}
    for key in row.keys():
        val = row[key]
        if isinstance(val, Decimal):
            d[key] = float(val)
        else:
            d[key] = val
    return d


class DataFetcher:
    """Fetches data from monitoring DB and caches results."""

    def __init__(self, pool):
        self.pool = pool
        self._start_time = datetime.now(timezone.utc)
        # Caches
        self._positions: List[PositionView] = []
        self._events: List[EventView] = []
        self._stats: Optional[StatsView] = None
        self._status: Optional[SystemStatus] = None
        self._trailing_stops: List[TrailingStopView] = []
        self._risk_events: List[RiskEventView] = []
        self._recent_trades: List[RecentTradeView] = []
        self._pnl_hourly: List[PnlDataPoint] = []
        self._pnl_daily: List[PnlDataPoint] = []
        self._performance: List[PerformanceMetricView] = []
        self._severity_counts: Dict[str, int] = {}
        # Last event timestamp for incremental fetch
        self._last_event_ts = datetime.now(timezone.utc) - timedelta(hours=24)
        # Error tracking
        self._consecutive_errors = 0

    async def _execute_query(self, query: str, *args):
        """Execute query and return rows."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
            self._consecutive_errors = 0
            return rows
        except Exception as e:
            self._consecutive_errors += 1
            logger.error(f"Query error (consecutive: {self._consecutive_errors}): {e}")
            raise

    # ─── Core data fetchers ─────────────────────────────────────

    async def fetch_positions(self) -> List[PositionView]:
        try:
            rows = await self._execute_query(ACTIVE_POSITIONS_QUERY)
            self._positions = [PositionView(**_row_to_dict(r)) for r in rows]
        except Exception:
            pass  # keep cached
        return self._positions

    async def fetch_events(self) -> List[EventView]:
        try:
            rows = await self._execute_query(RECENT_EVENTS_QUERY, self._last_event_ts)
            if rows:
                new_events = [EventView(**_row_to_dict(r)) for r in rows]
                # Merge with existing, dedup by id
                existing_ids = {e.id for e in self._events}
                for ev in new_events:
                    if ev.id not in existing_ids:
                        self._events.insert(0, ev)
                # Trim to 500
                self._events = self._events[:500]
                # Update timestamp
                if new_events:
                    latest = max(e.created_at for e in new_events if e.created_at)
                    if latest:
                        self._last_event_ts = latest
        except Exception:
            pass
        return self._events

    async def fetch_stats(self) -> Optional[StatsView]:
        try:
            rows = await self._execute_query(STATISTICS_QUERY)
            if rows:
                self._stats = StatsView(**_row_to_dict(rows[0]))
        except Exception:
            pass
        return self._stats

    async def fetch_status(self) -> Optional[SystemStatus]:
        try:
            rows = await self._execute_query(SYSTEM_STATUS_QUERY)
            if rows:
                d = _row_to_dict(rows[0])
                uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
                d["uptime_seconds"] = uptime
                d["db_connected"] = True
                # Merge severity counts
                d["error_count"] = self._severity_counts.get("ERROR", 0)
                d["warning_count"] = self._severity_counts.get("WARNING", 0)
                d["critical_count"] = self._severity_counts.get("CRITICAL", 0)
                self._status = SystemStatus(**d)
        except Exception:
            if self._status:
                self._status.db_connected = False
        return self._status

    # ─── New data fetchers ──────────────────────────────────────

    async def fetch_trailing_stops(self) -> List[TrailingStopView]:
        try:
            rows = await self._execute_query(TRAILING_STOP_DETAILS_QUERY)
            self._trailing_stops = [TrailingStopView(**_row_to_dict(r)) for r in rows]
        except Exception:
            pass
        return self._trailing_stops

    async def fetch_risk_events(self) -> List[RiskEventView]:
        try:
            rows = await self._execute_query(RISK_EVENTS_QUERY)
            self._risk_events = [RiskEventView(**_row_to_dict(r)) for r in rows]
        except Exception:
            pass
        return self._risk_events

    async def fetch_recent_trades(self) -> List[RecentTradeView]:
        try:
            rows = await self._execute_query(RECENT_TRADES_QUERY)
            self._recent_trades = [RecentTradeView(**_row_to_dict(r)) for r in rows]
        except Exception:
            pass
        return self._recent_trades

    async def fetch_pnl_hourly(self) -> List[PnlDataPoint]:
        try:
            rows = await self._execute_query(HISTORICAL_PNL_QUERY)
            self._pnl_hourly = [
                PnlDataPoint(
                    timestamp=r["hour"],
                    trades_count=r["trades_count"],
                    total_pnl=_to_float(r["total_pnl"]) or 0,
                    avg_pnl=_to_float(r["avg_pnl"]),
                )
                for r in rows
            ]
        except Exception:
            pass
        return self._pnl_hourly

    async def fetch_pnl_daily(self) -> List[PnlDataPoint]:
        try:
            rows = await self._execute_query(DAILY_PNL_QUERY)
            self._pnl_daily = [
                PnlDataPoint(
                    timestamp=r["day"],
                    trades_count=r["trades_count"],
                    total_pnl=_to_float(r["total_pnl"]) or 0,
                    winners=r["winners"],
                    losers=r["losers"],
                )
                for r in rows
            ]
        except Exception:
            pass
        return self._pnl_daily

    async def fetch_performance(self) -> List[PerformanceMetricView]:
        try:
            rows = await self._execute_query(PERFORMANCE_SUMMARY_QUERY)
            self._performance = [PerformanceMetricView(**_row_to_dict(r)) for r in rows]
        except Exception:
            pass
        return self._performance

    async def fetch_severity_counts(self) -> Dict[str, int]:
        try:
            rows = await self._execute_query(EVENT_SEVERITY_COUNTS_QUERY)
            self._severity_counts = {r["severity"]: r["count"] for r in rows}
        except Exception:
            pass
        return self._severity_counts

    # ─── Batch fetchers ──────────────────────────────────────────

    async def fetch_all_fast(self) -> Dict[str, Any]:
        """Fetch fast-updating data (positions, events, stats) in parallel."""
        await asyncio.gather(
            self.fetch_positions(),
            self.fetch_events(),
            self.fetch_stats(),
            self.fetch_severity_counts(),
        )
        return self.get_snapshot_fast()

    async def fetch_all_slow(self) -> Dict[str, Any]:
        """Fetch slow-updating data (PnL, risk, trailing, performance)."""
        await asyncio.gather(
            self.fetch_status(),
            self.fetch_trailing_stops(),
            self.fetch_risk_events(),
            self.fetch_recent_trades(),
            self.fetch_pnl_hourly(),
            self.fetch_pnl_daily(),
            self.fetch_performance(),
        )
        return self.get_snapshot_slow()

    # ─── Snapshot getters ────────────────────────────────────────

    def get_snapshot_fast(self) -> Dict[str, Any]:
        return {
            "positions": [p.model_dump(mode="json") for p in self._positions],
            "events": [e.model_dump(mode="json") for e in self._events[:50]],
            "stats": self._stats.model_dump(mode="json") if self._stats else None,
            "severity_counts": self._severity_counts,
        }

    def get_snapshot_slow(self) -> Dict[str, Any]:
        return {
            "status": self._status.model_dump(mode="json") if self._status else None,
            "trailing_stops": [t.model_dump(mode="json") for t in self._trailing_stops],
            "risk_events": [r.model_dump(mode="json") for r in self._risk_events],
            "recent_trades": [t.model_dump(mode="json") for t in self._recent_trades],
            "pnl_hourly": [p.model_dump(mode="json") for p in self._pnl_hourly],
            "pnl_daily": [p.model_dump(mode="json") for p in self._pnl_daily],
            "performance": [p.model_dump(mode="json") for p in self._performance],
        }

    def get_full_snapshot(self) -> Dict[str, Any]:
        return {**self.get_snapshot_fast(), **self.get_snapshot_slow()}
