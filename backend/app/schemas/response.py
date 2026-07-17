from pydantic import BaseModel

from app.schemas.nid import NIDData


class SuccessResponse(BaseModel):
    """Successful extraction response."""
    success: bool = True
    data: NIDData
    warnings: list[str] = []


class ErrorDetail(BaseModel):
    """Structured error detail."""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: ErrorDetail
