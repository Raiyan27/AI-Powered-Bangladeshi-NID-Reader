import time

from app.core.logging import logger
from app.schemas.nid import NIDData
from app.schemas.response import SuccessResponse
from app.services.image_service import validate_image, preprocess_image
from app.services.vision_service import extract_with_vision
from app.services.translation_service import (
    normalize_date,
    normalize_nid_number,
    normalize_name,
    normalize_address,
)
from app.services.validation_service import validate_extraction


async def extract_nid(
    front_bytes: bytes,
    front_filename: str,
    back_bytes: bytes,
    back_filename: str,
) -> SuccessResponse:
    """Orchestrate the full NID extraction pipeline.

    Steps:
    1. Validate both images (format, size, dimensions)
    2. Preprocess both images (rotation, resize, enhance, denoise)
    3. Send images to Vision AI for extraction
    4. Normalize field values (dates, NID digits, name casing)
    5. Validate output and collect warnings
    6. Return structured response
    """
    start_time = time.time()
    logger.info("NID extraction pipeline started")

    # Step 1: Validate
    logger.info("Validating images")
    validate_image(front_bytes, front_filename)
    validate_image(back_bytes, back_filename)

    # Step 2: Preprocess
    logger.info("Preprocessing images")
    front_processed = preprocess_image(front_bytes)
    back_processed = preprocess_image(back_bytes)
    logger.info(
        f"Preprocessing complete — "
        f"front: {len(front_processed) // 1024}KB, back: {len(back_processed) // 1024}KB"
    )

    # Step 3: Vision AI extraction
    logger.info("Running Vision AI extraction")
    vision_result = await extract_with_vision(
        front_image_bytes=front_processed,
        back_image_bytes=back_processed,
    )

    # Step 4: Normalize field values
    logger.info("Normalizing extracted field values")
    normalized = NIDData(
        name=normalize_name(vision_result.name),
        fatherName=normalize_name(vision_result.fatherName),
        motherName=normalize_name(vision_result.motherName),
        spouseName=normalize_name(vision_result.spouseName),
        dateOfBirth=normalize_date(vision_result.dateOfBirth),
        nidNumber=normalize_nid_number(vision_result.nidNumber),
        presentAddress=normalize_address(vision_result.presentAddress),
        permanentAddress=normalize_address(vision_result.permanentAddress),
    )

    # Step 5: Validate
    warnings = validate_extraction(normalized)

    elapsed = time.time() - start_time
    logger.info(f"NID extraction completed in {elapsed:.2f}s with {len(warnings)} warnings")

    return SuccessResponse(data=normalized, warnings=warnings)
