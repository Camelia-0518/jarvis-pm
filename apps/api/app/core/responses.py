"""Standardized API response formats"""

from typing import Any, Optional, List, TypeVar, Generic
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import Response
import json

T = TypeVar('T')


class ErrorDetail(BaseModel):
    """Error detail model"""
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field name for validation errors")
    details: Optional[dict] = Field(None, description="Additional error details")


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[ErrorDetail] = Field(None, description="Error details if failed")
    meta: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PaginatedResponse(APIResponse[List[T]]):
    """Paginated response wrapper"""
    data: List[T] = Field(default_factory=list, description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class ResponseBuilder:
    """Builder for standardized API responses"""

    @staticmethod
    def success(
        data: Any = None,
        meta: Optional[dict] = None,
        message: Optional[str] = None
    ) -> dict:
        """Build success response"""
        response_meta = {
            "timestamp": datetime.utcnow().isoformat(),
            **(meta or {})
        }
        if message:
            response_meta["message"] = message

        return {
            "success": True,
            "data": data,
            "error": None,
            "meta": response_meta
        }

    @staticmethod
    def error(
        code: str,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict] = None,
        status_code: int = 400
    ) -> dict:
        """Build error response"""
        error_detail = {
            "code": code,
            "message": message
        }
        if field:
            error_detail["field"] = field
        if details:
            error_detail["details"] = details

        return {
            "success": False,
            "data": None,
            "error": error_detail,
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "status_code": status_code
            }
        }

    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        limit: int,
        total: int,
        extra_meta: Optional[dict] = None
    ) -> dict:
        """Build paginated response"""
        total_pages = (total + limit - 1) // limit if limit > 0 else 0

        meta = {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "timestamp": datetime.utcnow().isoformat(),
            **(extra_meta or {})
        }

        return {
            "success": True,
            "data": {
                "items": data,
                "total": total,
                "page": page,
                "limit": limit,
            },
            "error": None,
            "meta": meta
        }

    @staticmethod
    def created(data: Any, message: str = "Resource created successfully") -> dict:
        """Build created response"""
        return {
            "success": True,
            "data": data,
            "error": None,
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "message": message,
                "status_code": 201
            }
        }

    @staticmethod
    def no_content(message: str = "Resource deleted successfully") -> dict:
        """Build no content response"""
        return {
            "success": True,
            "data": None,
            "error": None,
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "message": message,
                "status_code": 204
            }
        }


# Common error codes
class ErrorCode:
    """Standard error codes"""
    # Authentication errors (1xx)
    AUTH_UNAUTHORIZED = "AUTH_001"
    AUTH_FORBIDDEN = "AUTH_002"
    AUTH_TOKEN_EXPIRED = "AUTH_003"
    AUTH_INVALID_TOKEN = "AUTH_004"

    # Validation errors (2xx)
    VALIDATION_ERROR = "VAL_001"
    VALIDATION_REQUIRED = "VAL_002"
    VALIDATION_INVALID_FORMAT = "VAL_003"
    VALIDATION_OUT_OF_RANGE = "VAL_004"

    # Resource errors (3xx)
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_ALREADY_EXISTS = "RES_002"
    RESOURCE_CONFLICT = "RES_003"

    # Server errors (5xx)
    INTERNAL_ERROR = "SRV_001"
    SERVICE_UNAVAILABLE = "SRV_002"
    DATABASE_ERROR = "SRV_003"
    EXTERNAL_API_ERROR = "SRV_004"

    # Rate limiting (6xx)
    RATE_LIMIT_EXCEEDED = "RAT_001"

    # Business logic errors (7xx)
    BUSINESS_RULE_VIOLATION = "BUS_001"
    WORKFLOW_ERROR = "BUS_002"
