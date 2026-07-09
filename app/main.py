"""Punto de entrada de la API."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.error_handlers import register_error_handlers
from app.api.rate_limit import limiter
from app.api.router import api_router
from app.config.config import get_settings
from app.infrastructure.cache.redis_client import close_redis, get_redis
from app.infrastructure.database.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Startup / shutdown hooks."""
    settings = get_settings()
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    await get_redis().ping()
    logger.info("Redis connection OK")
    yield
    await close_redis()
    await engine.dispose()
    logger.info("Engine disposed. Bye.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH"],
            allow_headers=["X-API-Key", "Authorization", "Content-Type"],
        )

    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()