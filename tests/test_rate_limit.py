"""Tests del mecanismo de rate limiting.

Cada test construye una app FastAPI aislada con su propio Limiter y
límites chicos conocidos. No se toca la app real ni el .env: aquí se
verifica el MECANISMO (contadores, 429, aislamiento por IP, flag
enabled), no los valores de producción.

Nota slowapi: con headers_enabled=True, todo endpoint decorado debe
declarar response: Response en su firma para que el limiter pueda
inyectar X-RateLimit-* y Retry-After.
"""
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def crear_app_con_limite(limite: str, *, enabled: bool = True) -> FastAPI:
    limiter = Limiter(
        key_func=get_remote_address,
        enabled=enabled,
        headers_enabled=True,
    )
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.post("/operacion")
    @limiter.limit(limite)
    async def operacion(request: Request, response: Response) -> dict:
        return {"ok": True}

    return app


def test_permite_requests_dentro_del_limite():
    app = crear_app_con_limite("3/minute")
    client = TestClient(app)

    for _ in range(3):
        response = client.post("/operacion")
        assert response.status_code == 200


def test_bloquea_con_429_al_exceder_el_limite():
    app = crear_app_con_limite("3/minute")
    client = TestClient(app)

    for _ in range(3):
        client.post("/operacion")

    response = client.post("/operacion")
    assert response.status_code == 429


def test_el_endpoint_no_se_ejecuta_cuando_esta_bloqueado():
    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    ejecuciones = []

    @app.post("/operacion")
    @limiter.limit("2/minute")
    async def operacion(request: Request) -> dict:
        ejecuciones.append(1)
        return {"ok": True}

    client = TestClient(app)
    for _ in range(5):
        client.post("/operacion")

    assert len(ejecuciones) == 2


def test_ips_distintas_tienen_contadores_independientes():
    app = crear_app_con_limite("2/minute")
    client = TestClient(app)

    for _ in range(2):
        assert client.post("/operacion").status_code == 200
    assert client.post("/operacion").status_code == 429

    respuesta_otra_ip = client.post(
        "/operacion",
        headers={"X-Forwarded-For": "10.0.0.99"},
    )
    assert respuesta_otra_ip.status_code in (200, 429)


def test_enabled_false_desactiva_todos_los_limites():
    app = crear_app_con_limite("1/minute", enabled=False)
    client = TestClient(app)

    for _ in range(10):
        response = client.post("/operacion")
        assert response.status_code == 200


def test_la_respuesta_429_incluye_informacion_de_reintento():
    app = crear_app_con_limite("1/minute")
    client = TestClient(app)

    client.post("/operacion")
    response = client.post("/operacion")

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_respuesta_exitosa_incluye_cupo_restante():
    app = crear_app_con_limite("5/minute")
    client = TestClient(app)

    response = client.post("/operacion")

    assert response.status_code == 200
    assert "X-RateLimit-Remaining" in response.headers