"""Main entry point — FastAPI web dashboard for trading bot monitoring."""
import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import Config
from database.connection import DatabasePool
from services.data_fetcher import DataFetcher
from services.signal_ws import SignalWSClient
from api import router, set_fetcher, set_signal_client, ws_live, ws_push_loop, broadcast_update

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Fox Trading Bot Monitor — Web Dashboard")
    parser.add_argument("--db-host", default=None, help="Database host")
    parser.add_argument("--db-port", type=int, default=None, help="Database port")
    parser.add_argument("--db-name", default=None, help="Database name")
    parser.add_argument("--db-user", default=None, help="Database user")
    parser.add_argument("--db-password", default=None, help="Database password")
    parser.add_argument("--port", type=int, default=None, help="Web server port (default: 8080)")
    parser.add_argument("--host", default=None, help="Web server host (default: 0.0.0.0)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def setup_logging(level: str):
    log_file = Path(__file__).parent / "monitor_ui.log"
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


# Global references for lifespan
_pool = None
_fetcher = None
_push_task = None
_signal_client = None
_signal_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown."""
    global _pool, _fetcher, _push_task, _signal_client, _signal_task

    args = app.state.args
    config = Config()

    # Override config with CLI args
    db_host = args.db_host or config.DB_HOST
    db_port = args.db_port or config.DB_PORT
    db_name = args.db_name or config.DB_NAME
    db_user = args.db_user or config.DB_USER
    db_password = args.db_password or config.DB_PASSWORD

    logger.info(f"Connecting to {db_host}:{db_port}/{db_name} as {db_user}")

    # Initialize database pool
    await DatabasePool.initialize(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
    )
    _pool = await DatabasePool.get_pool()

    # Test connection
    try:
        async with _pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info(f"Database connected: {version[:60]}...")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

    # Initialize data fetcher
    _fetcher = DataFetcher(_pool)
    set_fetcher(_fetcher)

    # Initial data load
    logger.info("Loading initial data...")
    await _fetcher.fetch_all_fast()
    await _fetcher.fetch_all_slow()
    logger.info("Initial data loaded")

    # Start WebSocket push background task
    _push_task = asyncio.create_task(ws_push_loop(_fetcher))
    logger.info("WebSocket push loop started")

    # Start Signal WebSocket client (if configured)
    if config.SIGNAL_WS_URL and config.SIGNAL_WS_TOKEN:
        _signal_client = SignalWSClient(
            url=config.SIGNAL_WS_URL,
            token=config.SIGNAL_WS_TOKEN,
            reconnect_interval=config.SIGNAL_WS_RECONNECT_INTERVAL,
        )
        _signal_client.on_signal = broadcast_update
        set_signal_client(_signal_client)
        _signal_task = asyncio.create_task(_signal_client.run())
        logger.info(f"Signal WS client started: {config.SIGNAL_WS_URL}")
    else:
        logger.info("Signal WS not configured — skipping")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if _signal_client:
        _signal_client.stop()
    if _signal_task:
        _signal_task.cancel()
        try:
            await _signal_task
        except asyncio.CancelledError:
            pass
    if _push_task:
        _push_task.cancel()
        try:
            await _push_task
        except asyncio.CancelledError:
            pass
    await DatabasePool.close()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fox Crypto Trading Bot Monitor",
        version="3.0.0",
        lifespan=lifespan,
    )

    # API routes
    app.include_router(router)

    # WebSocket
    app.add_websocket_route("/ws/live", ws_live)

    # Static files
    static_dir = Path(__file__).parent / "ui" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Serve index.html at root
    @app.get("/")
    async def root():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Monitor UI — static files not found. Place index.html in ui/static/"}

    return app


def main():
    args = parse_args()
    setup_logging(args.log_level)

    config = Config()
    host = args.host or config.WEB_HOST
    port = args.port or config.WEB_PORT

    logger.info(f"Starting Fox Trading Bot Monitor v3.0 on {host}:{port}")

    app = create_app()
    app.state.args = args

    uvicorn.run(app, host=host, port=port, log_level=args.log_level.lower())


if __name__ == "__main__":
    main()
