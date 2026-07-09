"""
Primitivas de seguridad:
  - Verificacion de API key contra api_clients.json (autenticacion inicial).
  - Emision y validacion de JWT firmados HS256 (uso normal).
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from app.config.config import get_settings
from app.infrastructure.security.auth_clients import APIClient, find_by_api_key


def authenticate_api_key(api_key: str | None) -> APIClient | None:
    """Devuelve el cliente API si la key es valida y activo, o None."""
    if not api_key:
        return None
    settings = get_settings()
    return find_by_api_key(api_key, settings.api_clients_file)


def create_access_token(client: APIClient) -> tuple[str, int]:
    """Firma un JWT con los datos del cliente. Devuelve (token, expires_in)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "sub": client.id,
        "scopes": client.scopes,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid4().hex,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Valida firma + expiracion + issuer + claims requeridos.

    Lanza ValueError si algo falla (el resto del proyecto no conoce PyJWT).
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except InvalidTokenError as exc:
        raise ValueError(f"Invalid or expired token: {exc}") from exc

    if "scopes" not in payload or not isinstance(payload["scopes"], list):
        raise ValueError("Token missing 'scopes' claim")
    return payload


def has_required_scopes(token_scopes: list[str], required: tuple[str, ...]) -> bool:
    """El token cumple si tiene todos los scopes requeridos."""
    return all(scope in token_scopes for scope in required)