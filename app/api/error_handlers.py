import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.shared.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DomainError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _problem(status_code: int, title: str, detail: str) -> dict[str, Any]:
    return {"status": status_code, "title": title, "detail": detail}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _request_validation(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        detail = "; ".join(
            f"{'.'.join(str(item) for item in error['loc'][1:])}: {error['msg']}"
            for error in exc.errors()
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_problem(422, "Unprocessable Entity", detail or "Invalid request"),
        )

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_problem(404, "Not Found", exc.message),
        )

    @app.exception_handler(ValidationError)
    async def _bad_request(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_problem(400, "Bad Request", exc.message),
        )

    @app.exception_handler(AuthenticationError)
    async def _unauthorized(_: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_problem(401, "Unauthorized", exc.message),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def _forbidden(_: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_problem(403, "Forbidden", exc.message),
        )

    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        logger.warning("Unhandled DomainError subclass: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_problem(400, "Bad Request", exc.message),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_problem(500, "Internal Server Error", "Unexpected error"),
        )
