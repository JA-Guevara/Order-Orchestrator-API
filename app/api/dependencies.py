"""Inyección de dependencias de la API.

Define cómo se construye cada pieza que los endpoints declaran:
sesión de BD, repositorios, servicios, y validación de JWT/scopes.
Orden de secciones: infraestructura → seguridad → identidad → negocio.
"""

from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import get_settings
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.coordination.reservation_store import (
    RedisReservationStore,
    ReservationStore,
)
from app.infrastructure.database.repositories.pedidos_repository import PedidosRepository
from app.infrastructure.database.session import get_db
from app.infrastructure.security.security import decode_access_token, has_required_scopes
from app.services.pedidos_service import PedidosService
from app.shared.exceptions import AuthenticationError, AuthorizationError

SessionDep = Annotated[AsyncSession, Depends(get_db)]
_bearer_scheme = HTTPBearer(auto_error=False, bearerFormat="JWT")


async def require_jwt(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> dict[str, Any]:
    """Valida el JWT del header Authorization y devuelve su payload."""
    if creds is None or not creds.credentials:
        raise AuthenticationError("Missing bearer token")
    try:
        return decode_access_token(creds.credentials)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

CurrentTokenDep = Annotated[dict[str, Any], Depends(require_jwt)]


def _normalize_scopes(raw_scopes: Any) -> list[str]:
    """Acepta scopes como lista o string separado por espacios."""
    if raw_scopes is None:
        return []
    if isinstance(raw_scopes, str):
        return raw_scopes.split()
    return list(raw_scopes)


def require_scopes(*required: str):
    """Fábrica de validadores: require_scopes("x") devuelve un checker
    que FastAPI ejecuta por request y falla con 403 si el token no tiene x."""

    async def _checker(payload: CurrentTokenDep) -> None:
        token_scopes = _normalize_scopes(payload.get("scopes"))
        if not has_required_scopes(token_scopes, required):
            raise AuthorizationError(
                f"Token missing required scope(s): {', '.join(required)}"
            )

    return _checker

def get_bot_id(payload: CurrentTokenDep) -> str:
    """Identidad del cliente autenticado (claim sub del JWT)."""
    return str(payload["sub"])
BotIdDep = Annotated[str, Depends(get_bot_id)]


def get_reservation_store() -> ReservationStore:
    settings = get_settings()
    return RedisReservationStore(get_redis(), key_prefix=settings.reserva_key_prefix)
ReservationStoreDep = Annotated[ReservationStore, Depends(get_reservation_store)]


def get_pedidos_repository(session: SessionDep) -> PedidosRepository:
    return PedidosRepository(session)
PedidosRepoDep = Annotated[PedidosRepository, Depends(get_pedidos_repository)]

def get_pedidos_service(
    repo: PedidosRepoDep,
    reservations: ReservationStoreDep,
) -> PedidosService:
    settings = get_settings()
    return PedidosService(
        repository=repo,
        reservations=reservations,
        lease_seconds=settings.reserva_lease_seconds,
        max_candidatos=settings.reserva_max_candidatos,
    )
PedidosServiceDep = Annotated[PedidosService, Depends(get_pedidos_service)]