import warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*")

import easyocr
import numpy as np

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.nid import OCRResult, OCROutput

# Module-level OCR engine instance (initialized lazily).
# EasyOCR supports Bengali (bn) and English (en) natively.
_ocr_engine: easyocr.Reader | None = None
_ocr_initialization_failed = False


def get_ocr_engine() -> easyocr.Reader | None:
    """Get or initialize EasyOCR engine.

    Creates a Reader with Bengali and English language support.
    If the library or its dependencies are missing, returns None and
    logs a warning rather than crashing.
    """
    global _ocr_engine, _ocr_initialization_failed
    if _ocr_initialization_failed:
        return None

    if _ocr_engine is None:
        try:
            settings = get_settings()
            languages = settings.ocr.languages
            use_gpu = settings.ocr.use_gpu

            logger.info(f"Initializing EasyOCR engine (languages={languages}, gpu={use_gpu})...")
            _ocr_engine = easyocr.Reader(languages, gpu=use_gpu)
            logger.info("EasyOCR engine initialized successfully")
        except Exception as e:
            logger.error(f"EasyOCR engine initialization failed: {e}")
            _ocr_initialization_failed = True
            _ocr_engine = None

    return _ocr_engine


def run_ocr(image: np.ndarray) -> OCROutput:
    """Run EasyOCR on a preprocessed image.

    Returns structured OCR output with text, confidence, and positions.
    Detects both Bengali and English text from NID cards.

    If EasyOCR is unavailable or fails, returns an empty OCROutput so the
    pipeline can fall back completely to Vision AI.
    """
    settings = get_settings()
    engine = get_ocr_engine()

    if engine is None:
        logger.warning("EasyOCR is unavailable; skipping OCR step and falling back entirely to Vision AI")
        return OCROutput()

    try:
        # EasyOCR returns list of (bbox, text, confidence)
        results = engine.readtext(image)
    except Exception as e:
        logger.error(f"EasyOCR execution failed: {e}")
        return OCROutput()

    if not results:
        logger.warning("EasyOCR returned no results")
        return OCROutput()

    ocr_results: list[OCRResult] = []
    total_confidence = 0.0

    for bbox, text, confidence in results:
        # bbox is a list of 4 corner points: [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
        try:
            center_x = sum(p[0] for p in bbox) / 4.0
            center_y = sum(p[1] for p in bbox) / 4.0
        except Exception:
            center_x, center_y = 0.0, 0.0

        ocr_results.append(OCRResult(
            text=str(text),
            confidence=float(confidence),
            position=[center_x, center_y],
        ))
        total_confidence += float(confidence)

    # Filter results below the confidence threshold
    filtered = [r for r in ocr_results if r.confidence >= settings.ocr.confidence_threshold]
    avg_conf = total_confidence / len(ocr_results) if ocr_results else 0.0

    raw_text = "\n".join(r.text for r in filtered)

    logger.info(f"OCR completed: {len(filtered)} text regions, avg confidence: {avg_conf:.2f}")

    return OCROutput(
        results=filtered,
        raw_text=raw_text,
        avg_confidence=avg_conf,
    )
