import asyncio
import uuid

import pytest
from redis.asyncio import from_url

from app.config.config import get_settings
from app.infrastructure.coordination.reservation_store import RedisReservationStore


@pytest.fixture
async def store():
    settings = get_settings()
    redis = from_url(settings.redis_url, decode_responses=True)
    prefix = f"test:{uuid.uuid4().hex[:8]}:"
    yield RedisReservationStore(redis, key_prefix=prefix)
    keys = await redis.keys(f"{prefix}*")
    if keys:
        await redis.delete(*keys)
    await redis.aclose()


async def test_claim_pedido_libre(store):
    assert await store.try_claim(pedido_id=1, bot_id="bot_01", lease_seconds=60) is True


async def test_claim_pedido_ocupado(store):
    await store.try_claim(pedido_id=1, bot_id="bot_01", lease_seconds=60)
    assert await store.try_claim(pedido_id=1, bot_id="bot_02", lease_seconds=60) is False


async def test_owner_devuelve_el_dueno(store):
    await store.try_claim(pedido_id=1, bot_id="bot_01", lease_seconds=60)
    assert await store.owner(pedido_id=1) == "bot_01"
    assert await store.owner(pedido_id=999) is None


async def test_release_solo_el_dueno(store):
    await store.try_claim(pedido_id=1, bot_id="bot_01", lease_seconds=60)
    assert await store.release(pedido_id=1, bot_id="bot_02") is False
    assert await store.owner(pedido_id=1) == "bot_01"
    assert await store.release(pedido_id=1, bot_id="bot_01") is True
    assert await store.owner(pedido_id=1) is None


async def test_renew_solo_el_dueno(store):
    await store.try_claim(pedido_id=1, bot_id="bot_01", lease_seconds=60)
    assert await store.renew(pedido_id=1, bot_id="bot_02", lease_seconds=120) is False
    assert await store.renew(pedido_id=1, bot_id="bot_01", lease_seconds=120) is True


async def test_lease_expira_y_pedido_vuelve_a_estar_libre(store):
    await store.try_claim(pedido_id=1, bot_id="bot_01", lease_seconds=1)
    await asyncio.sleep(1.5)
    assert await store.try_claim(pedido_id=1, bot_id="bot_02", lease_seconds=60) is True


async def test_concurrencia_diez_bots_solo_uno_gana(store):
    resultados = await asyncio.gather(*[
        store.try_claim(pedido_id=7, bot_id=f"bot_{i:02d}", lease_seconds=60)
        for i in range(10)
    ])
    assert sum(resultados) == 1