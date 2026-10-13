"""Generic schemas and error responses."""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(..., ge=0, description="Total matching items across all pages")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    size: int = Field(..., ge=1, description="Page size")
    pages: int = Field(..., ge=0, description="Total number of pages")


class ErrorDetail(BaseModel):
    detail: str
    error_code: str | None = None
