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
    front: UploadFile = File(..., description="Front side or combined NID image"),
    back: UploadFile | None = File(None, description="Back side of NID card (optional if combined image)"),
):
    """Extract information from Bangladesh NID card images.

    Accepts front and back images (or a single combined image), runs OCR + Vision AI extraction,
    and returns structured NID data.
    """
    logger.info("Received NID extraction request")

    # Validate front file presence
    if not front or not front.filename:
        return _error_response("MISSING_FRONT_IMAGE", "Front side image is required.", 400)

    try:
        front_bytes = await front.read()
        if not front_bytes:
            return _error_response("MISSING_FRONT_IMAGE", "Front side image is required.", 400)

        # If back image is not provided, split the front NID image vertically
        if not back or not back.filename:
            logger.info("Back image is missing; auto-splitting front image vertically")
            try:
                from app.utils.image_utils import split_image_vertically
                front_bytes, back_bytes = split_image_vertically(front_bytes)
                back_filename = f"back_{front.filename}"
            except Exception as e:
                logger.error(f"Failed to auto-split combined image: {e}")
                return _error_response(
                    "INVALID_IMAGE_FORMAT",
                    "Failed to process combined NID image. Make sure it is a valid image containing both sides.",
                    400,
                )
        else:
            back_bytes = await back.read()
            if not back_bytes:
                return _error_response("MISSING_BACK_IMAGE", "Back side image is required.", 400)
            back_filename = back.filename

        result = await extract_nid(
            front_bytes=front_bytes,
            front_filename=front.filename,
            back_bytes=back_bytes,
            back_filename=back_filename,
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

