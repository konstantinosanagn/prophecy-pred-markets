"""Main FastAPI application."""

from __future__ import annotations

import os
from typing import Any

import aiohttp
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.logging_config import configure_logging, get_logger
from app.core.polymarket_utils import get_event_and_markets_by_slug
from app.core.resilience import openai_circuit
from app.db.async_client import check_mongodb_health as check_mongodb_health_async
from app.routes import analyze, runs
from app.schemas import HealthResponse

# Configure logging on startup
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(log_level=log_level)
logger = get_logger(__name__)

# Reset circuit breakers on startup to allow fresh attempts

if openai_circuit.state.value == "open":
    logger.info("Resetting OpenAI circuit breaker on startup")
    openai_circuit.reset()

# Create FastAPI app
app = FastAPI(
    title="Tavily Signals API",
    description="Multi-agent prediction market analysis API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
# Get allowed origins from environment or default to localhost for development
allowed_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(analyze.router, prefix="/api", tags=["analysis"])
app.include_router(runs.router, prefix="/api", tags=["runs"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Tavily Signals API", log_level=log_level)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Tavily Signals API")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for safe error responses."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": "An internal server error occurred. Please try again later.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health():
    """Basic liveness check."""
    return HealthResponse(
        status="ok",
        message="Service is running",
    )


@app.get("/health/live", response_model=HealthResponse, tags=["health"])
async def health_live():
    """Liveness probe - checks if service is alive."""
    return HealthResponse(
        status="ok",
        message="Service is alive",
    )


@app.get("/ping-db", tags=["health"])
async def ping_db():
    """Legacy endpoint - ping MongoDB database (migrated from Flask)."""
    try:
        db_healthy, db_message = await check_mongodb_health_async()
        if not db_healthy:
            return JSONResponse(
                status_code=500,
                content={"connected": False, "error": db_message},
            )

        # Test write capability
        from app.db.async_client import get_async_db

        db = await get_async_db()
        pings_collection = db["pings"]
        await pings_collection.insert_one({"msg": "hello from FastAPI", "ok": True})
        count = await pings_collection.count_documents({})

        return {
            "connected": True,
            "collection": "pings",
            "count": count,
        }
    except Exception as e:
        logger.warning("Database ping failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"connected": False, "error": str(e)},
        )


@app.get("/health/ready", response_model=HealthResponse, tags=["health"])
async def health_ready():
    """Readiness probe - checks if service is ready to serve requests."""
    checks: dict[str, Any] = {}
    all_healthy = True

    # Check MongoDB
    try:
        db_healthy, db_message = await check_mongodb_health_async()
        checks["mongodb"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "message": db_message,
        }
        if not db_healthy:
            all_healthy = False
    except Exception as e:
        logger.warning("MongoDB health check failed", error=str(e))
        checks["mongodb"] = {"status": "unhealthy", "message": str(e)}
        all_healthy = False

    # Check external APIs
    external_apis = {
        "polymarket": "https://gamma-api.polymarket.com/markets?slug=test",
        "tavily": "https://api.tavily.com/search",
        "openai": "https://api.openai.com/v1/models",
    }

    async with aiohttp.ClientSession() as session:
        for service_name, url in external_apis.items():
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    checks[service_name] = {
                        "status": "healthy" if resp.status < 500 else "unhealthy",
                        "message": f"HTTP {resp.status}",
                    }
                    if resp.status >= 500:
                        all_healthy = False
            except Exception as e:
                logger.warning(f"{service_name} health check failed", error=str(e))
                checks[service_name] = {"status": "unhealthy", "message": str(e)}
                all_healthy = False

    status = "ok" if all_healthy else "degraded"
    message = (
        "Service is ready" if all_healthy else "Service is degraded - some dependencies unavailable"
    )

    return HealthResponse(
        status=status,
        message=message,
        checks=checks,
    )


@app.get("/debug/polymarket/{slug:path}", tags=["debug"])
async def debug_polymarket(slug: str):
    """Debug endpoint to inspect raw Polymarket API responses.

    **Note:** This is a development/debugging endpoint. Disabled in production.

    Usage: GET /debug/polymarket/house-passes-epstein-disclosure-billresolution-in-2025
    """
    # Disable in production for security
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        logger.warning("Debug endpoint accessed in production", slug=slug)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )
    try:
        from app.config import PolymarketAPI
        from app.core.cache import polymarket_cache
        from app.core.polymarket_utils import fetch_json_async

        # Clear cache for this slug to force fresh fetch
        # Cache keys match the format used in fetch_json_async
        params_events = {"slug": slug}
        params_markets = {"slug": slug}
        cache_key_events = f"polymarket:{PolymarketAPI.GAMMA_API}/events:{hash(str(params_events))}"
        cache_key_markets = (
            f"polymarket:{PolymarketAPI.GAMMA_API}/markets:{hash(str(params_markets))}"
        )
        polymarket_cache._cache.pop(cache_key_events, None)
        polymarket_cache._cache.pop(cache_key_markets, None)

        # Fetch from both endpoints
        events_response = await fetch_json_async(
            f"{PolymarketAPI.GAMMA_API}/events", params={"slug": slug}
        )
        markets_response = await fetch_json_async(
            f"{PolymarketAPI.GAMMA_API}/markets", params={"slug": slug}
        )

        # Also get the processed result
        event, markets = await get_event_and_markets_by_slug(slug)

        return {
            "slug": slug,
            "raw_events_response": events_response,
            "raw_markets_response": markets_response,
            "processed_event": event,
            "processed_markets_count": len(markets) if markets else 0,
            "processed_markets_sample": markets[:2] if markets else [],  # First 2 markets
            "commentCount_from_event": event.get("commentCount") if event else None,
            "commentCount_from_raw_events": (
                events_response.get("data", [{}])[0].get("commentCount")
                if isinstance(events_response, dict) and events_response.get("data")
                else (
                    events_response[0].get("commentCount")
                    if isinstance(events_response, list) and len(events_response) > 0
                    else None
                )
            ),
            "pydantic_validation_attempted": True,
            "raw_event_commentCount": (
                events_response[0].get("commentCount")
                if isinstance(events_response, list) and len(events_response) > 0
                else None
            ),
        }
    except Exception as e:
        logger.error("Debug endpoint error", slug=slug, error=str(e), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "slug": slug},
        )
