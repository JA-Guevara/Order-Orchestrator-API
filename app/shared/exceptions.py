"""
Excepciones de dominio.

Los servicios y repositorios lanzan estas excepciones, independientes
de HTTP. El handler global en `app/api/error_handlers.py` las traduce
a respuestas HTTP apropiadas.
"""


class DomainError(Exception):
    """Raíz de toda excepción del dominio."""

    default_message: str = "Domain error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class NotFoundError(DomainError):
    """El recurso buscado no existe."""

    default_message = "Resource not found"


class ValidationError(DomainError):
    """Regla de negocio violada (distinta de validación de schema)."""

    default_message = "Validation failed"


class AuthenticationError(DomainError):
    """API Key inválida / JWT inválido o expirado / sin credencial."""

    default_message = "Authentication failed"


class AuthorizationError(DomainError):
    """Autenticado pero el token no tiene los scopes requeridos."""

    default_message = "Forbidden"
