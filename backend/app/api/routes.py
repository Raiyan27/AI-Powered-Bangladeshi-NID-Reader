from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.core.logging import logger
from app.schemas.response import ErrorResponse, ErrorDetail
from app.services.image_service import ImageValidationError
from app.services.vision_service import VisionExtractionError
from app.services.extraction_service import extract_nid

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/extract")
async def extract_nid_endpoint(
    front: UploadFile = File(..., description="Front side of NID card"),
    back: UploadFile = File(..., description="Back side of NID card"),
):
    """Extract information from Bangladesh NID card images.

    Accepts front and back images, runs OCR + Vision AI extraction,
    and returns structured NID data.
    """
    logger.info("Received NID extraction request")

    # Validate file presence
    if not front or not front.filename:
        return _error_response("MISSING_FRONT_IMAGE", "Front side image is required.", 400)

    if not back or not back.filename:
        return _error_response("MISSING_BACK_IMAGE", "Back side image is required.", 400)

    try:
        front_bytes = await front.read()
        back_bytes = await back.read()

        if not front_bytes:
            return _error_response("MISSING_FRONT_IMAGE", "Front side image is required.", 400)
        if not back_bytes:
            return _error_response("MISSING_BACK_IMAGE", "Back side image is required.", 400)

        result = await extract_nid(
            front_bytes=front_bytes,
            front_filename=front.filename,
            back_bytes=back_bytes,
            back_filename=back.filename,
        )

        return result.model_dump()

    except ImageValidationError as e:
        logger.warning(f"Image validation failed: {e.code} - {e.message}")
        return _error_response(e.code, e.message, 400)

    except VisionExtractionError as e:
        logger.error(f"Vision extraction failed: {e.code} - {e.message}")
        return _error_response(e.code, e.message, 500)

    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}", exc_info=True)
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again.",
            500,
        )


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    """Build a structured error response."""
    error = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=error.model_dump())
