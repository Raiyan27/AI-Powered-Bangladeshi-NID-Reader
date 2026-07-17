import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

import numpy as np
from paddleocr import PaddleOCR

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.nid import OCRResult, OCROutput

# Module-level OCR engine instance (initialized lazily).
# PaddleOCR does not support Bengali (bn) natively.
# We use the English model which also detects digits and Latin text from NID cards.
# Bengali text extraction is handled by the Vision AI model downstream.
_ocr_engine: PaddleOCR | None = None
_ocr_initialization_failed = False
_ocr_is_v3 = False


def get_ocr_engine() -> PaddleOCR | None:
    """Get or initialize PaddleOCR engine.

    Uses dynamic argument selection to support both PaddleOCR 2.x and 3.x APIs.
    If the library or its runtime dependencies (e.g. paddlepaddle) are missing,
    it returns None and logs a warning rather than crashing.
    """
    global _ocr_engine, _ocr_initialization_failed, _ocr_is_v3
    if _ocr_initialization_failed:
        return None

    if _ocr_engine is None:
        try:
            settings = get_settings()
            logger.info("Initializing PaddleOCR engine...")

            import inspect
            sig = inspect.signature(PaddleOCR.__init__)
            params = sig.parameters

            kwargs = {}

            # Detect PaddleOCR 3.x vs 2.x
            is_v3 = "use_textline_orientation" in params
            _ocr_is_v3 = is_v3

            if is_v3:
                # PaddleOCR 3.x configuration
                kwargs["device"] = "gpu" if settings.ocr.use_gpu else "cpu"
                kwargs["use_textline_orientation"] = True
            else:
                # PaddleOCR 2.x configuration
                kwargs["use_gpu"] = settings.ocr.use_gpu
                kwargs["use_angle_cls"] = True

            # Set language and logs
            if "lang" in params:
                kwargs["lang"] = "en"
            if "show_log" in params:
                kwargs["show_log"] = False

            logger.info(f"PaddleOCR args: {kwargs}")
            _ocr_engine = PaddleOCR(**kwargs)
            logger.info("PaddleOCR engine initialized successfully")
        except Exception as e:
            logger.error(
                f"PaddleOCR engine initialization failed (possibly due to missing dependencies like paddlepaddle): {e}"
            )
            _ocr_initialization_failed = True
            _ocr_engine = None

    return _ocr_engine


def run_ocr(image: np.ndarray) -> OCROutput:
    """Run PaddleOCR on a preprocessed image.

    Returns structured OCR output with text, confidence, and positions.
    Detects English text and numeric data (NID number, date of birth).
    Bengali text is recognized opportunistically; Vision AI is the primary
    source for Bengali semantic content.

    If PaddleOCR is unavailable or fails, returns an empty OCROutput so the
    pipeline can fallback completely to Vision AI.
    """
    settings = get_settings()
    engine = get_ocr_engine()

    if engine is None:
        logger.warning("PaddleOCR is unavailable; skipping OCR step and falling back entirely to Vision AI")
        return OCROutput()

    try:
        global _ocr_is_v3
        if _ocr_is_v3:
            result = engine.ocr(image)
        else:
            result = engine.ocr(image, cls=True)
    except Exception as e:
        logger.error(f"PaddleOCR execution failed: {e}")
        return OCROutput()

    # PaddleOCR may return None or [None] on empty images
    if not result or result[0] is None:
        logger.warning("PaddleOCR returned no results")
        return OCROutput()

    ocr_results: list[OCRResult] = []
    total_confidence = 0.0

    # Parse results based on PaddleOCR version (v3 dictionary vs v2 list)
    if isinstance(result[0], dict):
        res_dict = result[0]
        rec_texts = res_dict.get("rec_texts", [])
        rec_scores = res_dict.get("rec_scores", [])
        rec_polys = res_dict.get("rec_polys", []) or res_dict.get("rec_boxes", [])

        for i in range(len(rec_texts)):
            text = str(rec_texts[i])
            confidence = float(rec_scores[i])

            if i < len(rec_polys):
                poly = rec_polys[i]
                try:
                    if len(poly) == 4 and hasattr(poly[0], "__len__") and len(poly[0]) >= 2:
                        # Polygon (list of 4 coordinates)
                        center_x = sum(p[0] for p in poly) / 4.0
                        center_y = sum(p[1] for p in poly) / 4.0
                    elif len(poly) == 4:
                        # Bounding box [x_min, y_min, x_max, y_max]
                        center_x = (poly[0] + poly[2]) / 2.0
                        center_y = (poly[1] + poly[3]) / 2.0
                    else:
                        center_x, center_y = 0.0, 0.0
                except Exception:
                    center_x, center_y = 0.0, 0.0
            else:
                center_x, center_y = 0.0, 0.0

            ocr_results.append(OCRResult(
                text=text,
                confidence=confidence,
                position=[center_x, center_y],
            ))
            total_confidence += confidence
    else:
        # Standard PaddleOCR v2 format
        for line in result[0]:
            if not line or len(line) < 2:
                continue
            bbox = line[0]
            text_data = line[1]

            if not text_data or len(text_data) < 2:
                continue

            text = str(text_data[0])
            confidence = float(text_data[1])

            # Compute center of bounding box as position reference
            center_x = sum(p[0] for p in bbox) / 4.0
            center_y = sum(p[1] for p in bbox) / 4.0

            ocr_results.append(OCRResult(
                text=text,
                confidence=confidence,
                position=[center_x, center_y],
            ))
            total_confidence += confidence

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
