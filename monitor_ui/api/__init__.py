"""FastAPI routes — REST endpoints and WebSocket for live data."""
import logging
import asyncio
import json
from typing import Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse

from services.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Global reference — set by main.py at startup
_fetcher: Optional[DataFetcher] = None


def set_fetcher(fetcher: DataFetcher):
    global _fetcher
    _fetcher = fetcher


def get_fetcher() -> DataFetcher:
    if _fetcher is None:
        raise RuntimeError("DataFetcher not initialized")
    return _fetcher


# ─── REST Endpoints ──────────────────────────────────────────

@router.get("/positions")
async def get_positions():
    f = get_fetcher()
    positions = await f.fetch_positions()
    return [p.model_dump(mode="json") for p in positions]


@router.get("/events")
async def get_events(limit: int = Query(50, le=200)):
    f = get_fetcher()
    events = await f.fetch_events()
    return [e.model_dump(mode="json") for e in events[:limit]]


@router.get("/stats")
async def get_stats():
    f = get_fetcher()
    stats = await f.fetch_stats()
    return stats.model_dump(mode="json") if stats else {}


@router.get("/status")
async def get_status():
    f = get_fetcher()
    status = await f.fetch_status()
    return status.model_dump(mode="json") if status else {}


@router.get("/trailing-stops")
async def get_trailing_stops():
    f = get_fetcher()
    stops = await f.fetch_trailing_stops()
    return [s.model_dump(mode="json") for s in stops]


@router.get("/risk-events")
async def get_risk_events():
    f = get_fetcher()
    events = await f.fetch_risk_events()
    return [e.model_dump(mode="json") for e in events]


@router.get("/recent-trades")
async def get_recent_trades():
    f = get_fetcher()
    trades = await f.fetch_recent_trades()
    return [t.model_dump(mode="json") for t in trades]


@router.get("/pnl-history")
async def get_pnl_history(period: str = Query("24h", pattern="^(24h|7d|30d)$")):
    f = get_fetcher()
    if period == "24h":
        data = await f.fetch_pnl_hourly()
    else:
        data = await f.fetch_pnl_daily()
    return [d.model_dump(mode="json") for d in data]


@router.get("/performance")
async def get_performance():
    f = get_fetcher()
    perf = await f.fetch_performance()
    return [p.model_dump(mode="json") for p in perf]


@router.get("/health")
async def health_check():
    f = get_fetcher()
    status = await f.fetch_status()
    return {
        "status": "ok" if status and status.db_connected else "error",
        "db_connected": status.db_connected if status else False,
        "active_positions": status.active_positions if status else 0,
        "uptime_seconds": status.uptime_seconds if status else 0,
    }


@router.get("/snapshot")
async def get_full_snapshot():
    """Full data snapshot (all data at once for initial page load)."""
    f = get_fetcher()
    await asyncio.gather(f.fetch_all_fast(), f.fetch_all_slow())
    return f.get_full_snapshot()


# ─── WebSocket ───────────────────────────────────────────────

# Connected WebSocket clients
_ws_clients: Set[WebSocket] = set()


async def ws_live(websocket: WebSocket):
    """WebSocket endpoint for live data push."""
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info(f"WebSocket client connected ({len(_ws_clients)} total)")

    try:
        # Send initial full snapshot
        f = get_fetcher()
        await asyncio.gather(f.fetch_all_fast(), f.fetch_all_slow())
        snapshot = f.get_full_snapshot()
        await websocket.send_json({"type": "snapshot", "data": snapshot})

        # Keep connection alive, listen for client messages
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle client commands
                if msg == "refresh":
                    await asyncio.gather(f.fetch_all_fast(), f.fetch_all_slow())
                    snapshot = f.get_full_snapshot()
                    await websocket.send_json({"type": "snapshot", "data": snapshot})
                elif msg == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send ping to keep alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        _ws_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected ({len(_ws_clients)} total)")


async def broadcast_update(update_type: str, data: dict):
    """Broadcast update to all connected WebSocket clients."""
    if not _ws_clients:
        return

    message = json.dumps({"type": update_type, "data": data})
    disconnected = set()

    for ws in _ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)

    for ws_to_remove in disconnected:
        _ws_clients.discard(ws_to_remove)


async def ws_push_loop(fetcher: DataFetcher):
    """Background task that pushes updates to WebSocket clients."""
    fast_interval = 1.5  # seconds
    slow_interval = 10.0
    slow_counter = 0

    while True:
        try:
            if _ws_clients:
                # Always fetch fast data
                await fetcher.fetch_all_fast()
                await broadcast_update("fast", fetcher.get_snapshot_fast())

                # Slow data less frequently
                slow_counter += fast_interval
                if slow_counter >= slow_interval:
                    await fetcher.fetch_all_slow()
                    await broadcast_update("slow", fetcher.get_snapshot_slow())
                    slow_counter = 0

            await asyncio.sleep(fast_interval)
        except Exception as e:
            logger.error(f"WebSocket push loop error: {e}")
            await asyncio.sleep(5)
