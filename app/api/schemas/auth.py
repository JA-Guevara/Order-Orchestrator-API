"""DTOs para los endpoints de autenticacion."""
from pydantic import Field

from app.api.schemas.base import APIModel


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Segundos hasta que expire el token")
    scopes: list[str]


class MeResponse(APIModel):
    client_id: str
    scopes: list[str]
    expires_in: int = Field(description="Segundos hasta que expire el token actual")
