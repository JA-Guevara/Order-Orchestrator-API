"""Smoke test de conexión a Redis. Ejecutar: python -m scripts.test_redis_connection"""
import asyncio

from redis.asyncio import from_url

from app.config.config import get_settings


async def main() -> None:
    settings = get_settings()
    redis = from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)

    pong = await redis.ping()
    print(f"PING -> {pong}")

    ok = await redis.set("test:conexion", "bot_prueba", nx=True, ex=30)
    print(f"SET NX -> {ok}")

    duplicado = await redis.set("test:conexion", "otro_bot", nx=True, ex=30)
    print(f"SET NX duplicado -> {duplicado} (None = atomicidad OK)")

    ttl = await redis.ttl("test:conexion")
    print(f"TTL -> {ttl}s")

    await redis.delete("test:conexion")
    await redis.aclose()
    print("Conexión Redis OK")


if __name__ == "__main__":
    asyncio.run(main())