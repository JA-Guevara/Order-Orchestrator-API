"""
Cliente Redis compartido de la API.

Un solo cliente global con pool de conexiones interno, mismo patrón
que el engine de SQLAlchemy en database/session.py. Se inicializa
perezosamente y se cierra en el lifespan de la app.
"""
from redis.asyncio import Redis, from_url

from app.config.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None