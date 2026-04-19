"""Custom exceptions and global error handlers"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Optional, Dict, Any
import logging

from app.core.responses import ResponseBuilder, ErrorCode

logger = logging.getLogger(__name__)


# ============== Custom Exceptions ==============

class AppException(Exception):
    """Base application exception"""
    def __init__(
        self,
        message: str,
        code: str = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Authentication related errors"""
    def __init__(self, message: str = "Authentication failed", code: str = ErrorCode.AUTH_UNAUTHORIZED):
        super().__init__(message, code, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppException):
    """Authorization/permission errors"""
    def __init__(self, message: str = "Permission denied", code: str = ErrorCode.AUTH_FORBIDDEN):
        super().__init__(message, code, status.HTTP_403_FORBIDDEN)


class ValidationError(AppException):
    """Input validation errors"""
    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        code: str = ErrorCode.VALIDATION_ERROR
    ):
        details = {"field": field} if field else {}
        super().__init__(message, code, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class ResourceNotFoundError(AppException):
    """Resource not found errors"""
    def __init__(self, resource: str = "Resource", resource_id: Optional[str] = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        super().__init__(message, ErrorCode.RESOURCE_NOT_FOUND, status.HTTP_404_NOT_FOUND)


class ResourceConflictError(AppException):
    """Resource conflict errors"""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, ErrorCode.RESOURCE_ALREADY_EXISTS, status.HTTP_409_CONFLICT)


class RateLimitError(AppException):
    """Rate limit exceeded errors"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(message, ErrorCode.RATE_LIMIT_EXCEEDED, status.HTTP_429_TOO_MANY_REQUESTS)
        self.retry_after = retry_after


class DatabaseError(AppException):
    """Database operation errors"""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, ErrorCode.DATABASE_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExternalAPIError(AppException):
    """External API call errors"""
    def __init__(self, service: str = "External service", message: str = "API call failed"):
        super().__init__(f"{service}: {message}", ErrorCode.EXTERNAL_API_ERROR, status.HTTP_502_BAD_GATEWAY)


class BusinessLogicError(AppException):
    """Business logic/rule errors"""
    def __init__(self, message: str = "Business rule violation"):
        super().__init__(message, ErrorCode.BUSINESS_RULE_VIOLATION, status.HTTP_400_BAD_REQUEST)


# ============== Error Handlers ==============

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions"""
    logger.error(
        f"AppException: {exc.code} - {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "code": exc.code,
            "details": exc.details
        }
    )

    headers = {}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseBuilder.error(
            code=exc.code,
            message=exc.message,
            details=exc.details if exc.details else None
        ),
        headers=headers
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette HTTP exceptions"""
    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail}",
        extra={"path": request.url.path, "method": request.method}
    )

    # Map HTTP status codes to error codes
    code_mapping = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.AUTH_UNAUTHORIZED,
        403: ErrorCode.AUTH_FORBIDDEN,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        409: ErrorCode.RESOURCE_CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_ERROR,
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseBuilder.error(
            code=code_mapping.get(exc.status_code, ErrorCode.INTERNAL_ERROR),
            message=str(exc.detail)
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors"""
    errors = exc.errors()

    # Format validation errors
    formatted_errors = []
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []) if loc != "body")
        formatted_errors.append({
            "field": field,
            "message": error.get("msg", ""),
            "type": error.get("type", "")
        })

    logger.warning(
        f"ValidationError: {len(errors)} validation errors",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": formatted_errors
        }
    )

    # Get first error for main message
    first_error = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first_error.get("loc", []) if loc != "body")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResponseBuilder.error(
            code=ErrorCode.VALIDATION_ERROR,
            message=first_error.get("msg", "Validation failed"),
            field=field if field else None,
            details={"errors": formatted_errors} if len(formatted_errors) > 1 else None
        )
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions"""
    logger.exception(
        f"Unhandled exception: {str(exc)}",
        extra={"path": request.url.path, "method": request.method}
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ResponseBuilder.error(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred. Please try again later."
        )
    )


# ============== Exception Handler Registration ==============

def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
