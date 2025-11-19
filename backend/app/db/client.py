"""Synchronous MongoDB client (legacy support)."""

from __future__ import annotations

from typing import Optional

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    """Return a shared MongoClient instance with connection pooling."""
    global _client
    if _client is None:
        if not settings.mongodb_uri:
            raise RuntimeError("MONGODB_URI is not configured")

        try:
            _client = MongoClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=45000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                retryWrites=True,
                retryReads=True,
            )
            # Test connection
            _client.admin.command("ping")
            logger.info(
                "MongoDB synchronous connection established",
                max_pool_size=50,
                min_pool_size=10,
            )
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            raise RuntimeError("Failed to connect to MongoDB") from e

    return _client


def get_db():
    """Return the main application database."""
    client = get_client()
    return client["tavily_proj"]


def check_mongodb_health() -> tuple[bool, str]:
    """Check MongoDB connection health."""
    try:
        client = get_client()
        client.admin.command("ping")
        return True, "MongoDB connection healthy"
    except Exception as e:
        logger.warning("MongoDB health check failed", error=str(e))
        return False, f"MongoDB connection failed: {str(e)}"
