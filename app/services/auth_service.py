"""
Servicio de autenticaciÃ³n.

Ãšnico punto donde se valida la API Key y se emite el JWT. Si la lÃ³gica
de "quÃ© hace un login" cambia (por ejemplo, agregar rate limiting o
auditar quiÃ©n pidiÃ³ token), va acÃ¡.
"""
from app.infrastructure.security.security import (
    authenticate_api_key,
    create_access_token,
)
from app.shared.exceptions import AuthenticationError


class AuthService:
    """No tiene estado: las funciones de security son stateless."""

    def issue_token(self, api_key: str | None) -> tuple[str, int, str, list[str]]:
        """
        Devuelve (token, expires_in, client_id, scopes) si la API key es vÃ¡lida.
        Lanza AuthenticationError si no.
        """
        client = authenticate_api_key(api_key)
        if client is None:
            raise AuthenticationError("Invalid or missing API key")

        token, expires_in = create_access_token(client)
        return token, expires_in, client.id, client.scopes

