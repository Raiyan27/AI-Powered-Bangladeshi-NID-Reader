import time

from app.core.logging import logger
from app.schemas.nid import NIDData
from app.schemas.response import SuccessResponse
from app.services.image_service import validate_image, preprocess_image
from app.services.ocr_service import run_ocr
from app.services.vision_service import extract_with_vision
from app.services.merge_service import merge_results
from app.services.validation_service import validate_extraction


async def extract_nid(
    front_bytes: bytes,
    front_filename: str,
    back_bytes: bytes,
    back_filename: str,
) -> SuccessResponse:
    """Orchestrate the full NID extraction pipeline.

    Steps:
    1. Validate both images
    2. Preprocess both images
    3. Run OCR on both
    4. Run Vision AI with images + OCR text
    5. Merge OCR and Vision results
    6. Validate final output
    7. Return structured response
    """
    start_time = time.time()
    logger.info("Starting NID extraction pipeline")

    # Step 1: Validate
    logger.info("Validating front image")
    validate_image(front_bytes, front_filename)
    logger.info("Validating back image")
    validate_image(back_bytes, back_filename)

    # Step 2: Preprocess
    logger.info("Preprocessing images")
    front_img, front_processed = preprocess_image(front_bytes)
    back_img, back_processed = preprocess_image(back_bytes)

    # Step 3: OCR
    logger.info("Running OCR on front image")
    ocr_front = run_ocr(front_img)
    logger.info("Running OCR on back image")
    ocr_back = run_ocr(back_img)

    logger.info(f"OCR front text: {ocr_front.raw_text[:200] if ocr_front.raw_text else '(empty)'}")
    logger.info(f"OCR back text: {ocr_back.raw_text[:200] if ocr_back.raw_text else '(empty)'}")

    # Step 4: Vision AI
    logger.info("Running Vision AI extraction")
    vision_result = await extract_with_vision(
        front_image_bytes=front_processed,
        back_image_bytes=back_processed,
        front_ocr_text=ocr_front.raw_text,
        back_ocr_text=ocr_back.raw_text,
    )

    # Step 5: Merge
    logger.info("Merging OCR and Vision results")
    merged_data, merge_warnings = merge_results(ocr_front, ocr_back, vision_result)

    # Step 6: Validate
    validation_warnings = validate_extraction(merged_data)

    all_warnings = merge_warnings + validation_warnings

    elapsed = time.time() - start_time
    logger.info(f"NID extraction completed in {elapsed:.2f}s with {len(all_warnings)} warnings")

    return SuccessResponse(
        data=merged_data,
        warnings=all_warnings,
    )
