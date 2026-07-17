import io

import cv2
import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.core.logging import logger
from app.utils.file_utils import get_file_extension
from app.utils.image_utils import bytes_to_numpy, numpy_to_bytes, read_exif_rotation


class ImageValidationError(Exception):
    """Raised when image validation fails."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_image(file_bytes: bytes, filename: str) -> None:
    """Validate uploaded image file.

    Checks extension, corruption, file size, and dimensions.
    Raises ImageValidationError with structured error codes.
    """
    settings = get_settings()

    ext = get_file_extension(filename)
    if ext not in settings.backend.supported_formats:
        raise ImageValidationError(
            code="INVALID_IMAGE_FORMAT",
            message=f"Unsupported file format '.{ext}'. Supported: {', '.join(settings.backend.supported_formats)}.",
        )

    if len(file_bytes) > settings.max_upload_bytes:
        raise ImageValidationError(
            code="INVALID_IMAGE_FORMAT",
            message=f"File size exceeds {settings.backend.max_upload_size_mb}MB limit.",
        )

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except Exception:
        raise ImageValidationError(
            code="INVALID_IMAGE_FORMAT",
            message="The uploaded file is corrupted or not a valid image.",
        )

    # Re-open after verify (verify closes the image)
    img = Image.open(io.BytesIO(file_bytes))
    width, height = img.size

    if width < settings.backend.min_image_dimension or height < settings.backend.min_image_dimension:
        raise ImageValidationError(
            code="LOW_IMAGE_QUALITY",
            message="The image is too small. Please upload a higher resolution image.",
        )

    if width > settings.backend.max_image_dimension or height > settings.backend.max_image_dimension:
        logger.info(f"Image will be resized: {width}x{height} exceeds max dimension")


def preprocess_image(file_bytes: bytes) -> tuple[np.ndarray, bytes]:
    """Preprocess image for OCR and Vision AI.

    Steps: auto-rotate, resize, enhance contrast, denoise.
    Returns (numpy array for OCR, processed bytes for Vision API).
    """
    # Auto-rotate based on EXIF
    rotation = read_exif_rotation(file_bytes)
    img = bytes_to_numpy(file_bytes)

    if img is None:
        raise ImageValidationError(
            code="INVALID_IMAGE_FORMAT",
            message="Failed to decode image data.",
        )

    if rotation != 0:
        if rotation == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif rotation == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        logger.info(f"Auto-rotated image by {rotation} degrees")

    # Resize if too large (preserve aspect ratio)
    settings = get_settings()
    h, w = img.shape[:2]
    max_dim = settings.backend.max_image_dimension

    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.info(f"Resized image from {w}x{h} to {new_w}x{new_h}")

    # Deskew using minimum area rectangle on largest contour
    img = _deskew(img)

    # Enhance contrast using CLAHE on L channel of LAB color space
    img = _enhance_contrast(img)

    # Denoise
    img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    processed_bytes = numpy_to_bytes(img)
    return img, processed_bytes


def _deskew(img: np.ndarray) -> np.ndarray:
    """Attempt to deskew image using contour detection."""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Find lines using Hough transform
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

        if lines is None or len(lines) < 5:
            return img

        # Calculate median angle from detected lines
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) < 15:  # Only consider near-horizontal lines
                angles.append(angle)

        if not angles:
            return img

        median_angle = np.median(angles)

        if abs(median_angle) < 0.5:  # Skip if nearly straight
            return img

        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)

        logger.info(f"Deskewed image by {median_angle:.2f} degrees")
        return rotated

    except Exception as e:
        logger.warning(f"Deskew failed, using original image: {e}")
        return img


def _enhance_contrast(img: np.ndarray) -> np.ndarray:
    """Enhance contrast using CLAHE on LAB color space."""
    try:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)

        enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])
        enhanced_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        return enhanced_img
    except Exception as e:
        logger.warning(f"Contrast enhancement failed: {e}")
        return img
