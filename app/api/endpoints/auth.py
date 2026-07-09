"""Endpoints de autenticación: emisión de JWT e inspección del token."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import APIKeyHeader

from app.api.dependencies import CurrentTokenDep
from app.api.rate_limit import limiter
from app.api.schemas.auth import MeResponse, TokenResponse
from app.config.config import get_settings
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_settings = get_settings()


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtener un JWT con los scopes del cliente",
)
@limiter.limit(_settings.rate_limit_auth)
async def issue_token(
    request: Request,
    response: Response,
    api_key: Annotated[str | None, Depends(_api_key_header)],
) -> TokenResponse:
    service = AuthService()

    token, expires_in, _client_id, scopes = service.issue_token(api_key)

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        scopes=scopes,
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Devuelve la identidad y permisos del token actual",
)
async def me(payload: CurrentTokenDep) -> MeResponse:
    exp = int(payload["exp"])
    now = int(datetime.now(timezone.utc).timestamp())

    return MeResponse(
        client_id=payload["sub"],
        scopes=list(payload["scopes"]),
        expires_in=max(exp - now, 0),
    )