"""Database connection pool manager."""
import asyncpg
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabasePool:
    """Singleton database connection pool manager."""

    _instance: Optional[asyncpg.Pool] = None
    _config: dict = {}

    @classmethod
    async def initialize(
        cls,
        host: str = "localhost",
        port: int = 5432,
        database: str = "fox_crypto",
        user: str = "evgeniyyanvarskiy",
        password: str = "",
        min_size: int = 2,
        max_size: int = 5,
    ) -> None:
        """Initialize the connection pool with configuration."""
        cls._config = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "min_size": min_size,
            "max_size": max_size,
            "command_timeout": 5.0,
            "max_inactive_connection_lifetime": 300.0,
        }

        # Add password only if provided
        if password:
            cls._config["password"] = password

        # Create the pool
        await cls.get_pool()
        logger.info(f"Database pool initialized: {database}@{host}:{port}")

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Get or create the connection pool."""
        if cls._instance is None:
            if not cls._config:
                # Use default configuration
                await cls.initialize()

            try:
                cls._instance = await asyncpg.create_pool(**cls._config)
                logger.info("Connection pool created successfully")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise

        return cls._instance

    @classmethod
    async def close(cls) -> None:
        """Close the connection pool."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            logger.info("Connection pool closed")

    @classmethod
    async def test_connection(cls) -> bool:
        """Test database connectivity."""
        try:
            pool = await cls.get_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
