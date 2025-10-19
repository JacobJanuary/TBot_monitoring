#!/usr/bin/env python3
"""Main entry point for Trading Bot Monitor UI."""
import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database.connection import DatabasePool
from ui.app import run_monitor_app
from config import Config


def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    handlers = [logging.StreamHandler()]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


async def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="Fox Crypto Trading Bot Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (localhost database)
  python main.py

  # Connect to remote database
  python main.py --db-host remote.server.com --db-user trader

  # Enable debug logging
  python main.py --log-level DEBUG

  # Use custom database
  python main.py --db-name my_trading_db --db-port 5433
        """,
    )

    # Database arguments
    parser.add_argument(
        "--db-host",
        default=Config.DB_HOST,
        help=f"Database host (default: {Config.DB_HOST})",
    )
    parser.add_argument(
        "--db-port",
        type=int,
        default=Config.DB_PORT,
        help=f"Database port (default: {Config.DB_PORT})",
    )
    parser.add_argument(
        "--db-name",
        default=Config.DB_NAME,
        help=f"Database name (default: {Config.DB_NAME})",
    )
    parser.add_argument(
        "--db-user",
        default=Config.DB_USER,
        help=f"Database user (default: {Config.DB_USER})",
    )
    parser.add_argument(
        "--db-password", default=Config.DB_PASSWORD, help="Database password"
    )

    # Logging arguments
    parser.add_argument(
        "--log-level",
        default=Config.LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=f"Logging level (default: {Config.LOG_LEVEL})",
    )
    parser.add_argument(
        "--log-file", default=Config.LOG_FILE, help="Log file path (optional)"
    )

    # Connection pool arguments
    parser.add_argument(
        "--pool-min",
        type=int,
        default=Config.DB_MIN_POOL_SIZE,
        help=f"Minimum pool size (default: {Config.DB_MIN_POOL_SIZE})",
    )
    parser.add_argument(
        "--pool-max",
        type=int,
        default=Config.DB_MAX_POOL_SIZE,
        help=f"Maximum pool size (default: {Config.DB_MAX_POOL_SIZE})",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)

    logger.info("Starting Fox Crypto Trading Bot Monitor")
    logger.info(f"Connecting to database: {args.db_name}@{args.db_host}:{args.db_port}")

    try:
        # Initialize database connection pool
        await DatabasePool.initialize(
            host=args.db_host,
            port=args.db_port,
            database=args.db_name,
            user=args.db_user,
            password=args.db_password,
            min_size=args.pool_min,
            max_size=args.pool_max,
        )

        # Test connection
        logger.info("Testing database connection...")
        if await DatabasePool.test_connection():
            logger.info("Database connection successful")
        else:
            logger.error("Database connection test failed")
            sys.exit(1)

        # Run the monitor app
        logger.info("Starting monitor UI...")
        await run_monitor_app()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        logger.info("Closing database connections...")
        await DatabasePool.close()
        logger.info("Monitor shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)
