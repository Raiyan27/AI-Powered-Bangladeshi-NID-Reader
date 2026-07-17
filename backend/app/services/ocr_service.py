import numpy as np
from paddleocr import PaddleOCR

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.nid import OCRResult, OCROutput

# Module-level OCR engine instance (initialized lazily)
_ocr_engine: PaddleOCR | None = None


def get_ocr_engine() -> PaddleOCR:
    """Get or initialize PaddleOCR engine."""
    global _ocr_engine
    if _ocr_engine is None:
        settings = get_settings()
        logger.info("Initializing PaddleOCR engine...")
        _ocr_engine = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            use_gpu=settings.ocr.use_gpu,
            show_log=False,
        )
        logger.info("PaddleOCR engine initialized")
    return _ocr_engine


def run_ocr(image: np.ndarray) -> OCROutput:
    """Run PaddleOCR on a preprocessed image.

    Returns structured OCR output with text, confidence, and positions.
    """
    settings = get_settings()
    engine = get_ocr_engine()

    try:
        result = engine.ocr(image, cls=True)
    except Exception as e:
        logger.error(f"PaddleOCR execution failed: {e}")
        return OCROutput()

    if not result or not result[0]:
        logger.warning("PaddleOCR returned no results")
        return OCROutput()

    ocr_results: list[OCRResult] = []
    total_confidence = 0.0

    for line in result[0]:
        bbox = line[0]
        text = line[1][0]
        confidence = line[1][1]

        # Use center of bounding box as position
        center_x = sum(p[0] for p in bbox) / 4
        center_y = sum(p[1] for p in bbox) / 4

        ocr_results.append(OCRResult(
            text=text,
            confidence=confidence,
            position=[center_x, center_y],
        ))
        total_confidence += confidence

    # Filter below threshold
    filtered = [r for r in ocr_results if r.confidence >= settings.ocr.confidence_threshold]
    avg_conf = total_confidence / len(ocr_results) if ocr_results else 0.0

    raw_text = "\n".join(r.text for r in filtered)

    logger.info(f"OCR completed: {len(filtered)} text regions, avg confidence: {avg_conf:.2f}")

    return OCROutput(
        results=filtered,
        raw_text=raw_text,
        avg_confidence=avg_conf,
    )
