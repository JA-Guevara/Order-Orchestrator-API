"""
Coordinación de reservas de pedidos entre bots.

ReservationStore es el contrato (Protocol): el service depende de él,
no de Redis. RedisReservationStore lo implementa con SET NX EX:
  - NX garantiza atomicidad (dos bots jamás reservan el mismo pedido)
  - EX es el lease: si el bot muere, la clave expira sola y el pedido
    vuelve a estar disponible sin intervención

Redis solo guarda estado efímero de coordinación. La verdad del
negocio (estados finales) vive en SQL Server.
"""
from typing import Protocol

from redis.asyncio import Redis

KEY_PREFIX = "reserva:pedido:"


class ReservationStore(Protocol):
    async def try_claim(self, *, pedido_id: int, bot_id: str, lease_seconds: int) -> bool: ...
    async def owner(self, *, pedido_id: int) -> str | None: ...
    async def renew(self, *, pedido_id: int, bot_id: str, lease_seconds: int) -> bool: ...
    async def release(self, *, pedido_id: int, bot_id: str) -> bool: ...


class RedisReservationStore:
    def __init__(self, redis: Redis, *, key_prefix: str = KEY_PREFIX) -> None:
        self._redis = redis
        self._prefix = key_prefix

    def _key(self, pedido_id: int) -> str:
        return f"{self._prefix}{pedido_id}"

    async def try_claim(self, *, pedido_id: int, bot_id: str, lease_seconds: int) -> bool:
        return bool(
            await self._redis.set(self._key(pedido_id), bot_id, nx=True, ex=lease_seconds)
        )

    async def owner(self, *, pedido_id: int) -> str | None:
        return await self._redis.get(self._key(pedido_id))

    async def renew(self, *, pedido_id: int, bot_id: str, lease_seconds: int) -> bool:
        if await self.owner(pedido_id=pedido_id) != bot_id:
            return False
        return bool(await self._redis.expire(self._key(pedido_id), lease_seconds))

    async def release(self, *, pedido_id: int, bot_id: str) -> bool:
        if await self.owner(pedido_id=pedido_id) != bot_id:
            return False
        return bool(await self._redis.delete(self._key(pedido_id)))