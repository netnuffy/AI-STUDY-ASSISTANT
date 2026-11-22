"""Application exception hierarchy + FastAPI exception handlers.

Every error returned to the client has the same shape:
    {"detail": "<human-readable message>"}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.logging import get_logger

logger = get_logger(__name__)


class AppException(Exception):
    status_code: int = 500
    message: str = "Internal server error"

    def __init__(self, message: str | None = None, status_code: int | None = None):
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)


class BadRequestError(AppException):
    status_code = 400
    message = "Bad request"


class UnauthorizedError(AppException):
    status_code = 401
    message = "Authentication required"


class ForbiddenError(AppException):
    status_code = 403
    message = "You do not have permission to do this"


class NotFoundError(AppException):
    status_code = 404
    message = "Resource not found"


class ConflictError(AppException):
    status_code = 409
    message = "Resource already exists"


class ExternalServiceError(AppException):
    status_code = 502
    message = "An external service failed"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
