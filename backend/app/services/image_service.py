import io

import cv2
import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.core.logging import logger
from app.utils.file_utils import get_file_extension
from app.utils.image_utils import bytes_to_numpy, numpy_to_jpeg, read_exif_rotation


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


def preprocess_image(file_bytes: bytes) -> bytes:
    """Preprocess image for Vision AI extraction.

    Preserves the raw photographic quality of the camera snapshot:
      1. EXIF auto-rotation (keeps card right-side up)
      2. Intelligent downscaling (keeps image within API limits)
      3. Re-encoding as high-quality JPEG (quality=95)
    """
    rotation = read_exif_rotation(file_bytes)
    img = bytes_to_numpy(file_bytes)

    if img is None:
        raise ImageValidationError(
            code="INVALID_IMAGE_FORMAT",
            message="Failed to decode image data.",
        )

    # Step 1: EXIF rotation correction
    if rotation != 0:
        rotation_flags = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
        if rotation in rotation_flags:
            img = cv2.rotate(img, rotation_flags[rotation])
            logger.info(f"Auto-rotated image by {rotation} degrees")

    # Step 2: Downscale if too large (preserve aspect ratio)
    settings = get_settings()
    h, w = img.shape[:2]
    max_dim = settings.backend.max_image_dimension

    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.info(f"Resized image from {w}x{h} to {new_w}x{new_h}")

    # Re-encode as JPEG at quality=95 for high visual fidelity
    return numpy_to_jpeg(img, quality=95)


# ---------------------------------------------------------------------------
# Private preprocessing helpers
# ---------------------------------------------------------------------------

def _deskew(img: np.ndarray) -> np.ndarray:
    """Attempt to deskew image using Hough line detection."""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

        if lines is None or len(lines) < 5:
            return img

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) < 15:  # Consider only near-horizontal lines
                angles.append(angle)

        if not angles:
            return img

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5:
            return img

        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
        logger.info(f"Deskewed image by {median_angle:.2f} degrees")
        return rotated

    except Exception as e:
        logger.warning(f"Deskew failed, using original: {e}")
        return img


def _white_balance(img: np.ndarray) -> np.ndarray:
    """Apply gray-world white balance to reduce colour casts from indoor lighting."""
    try:
        img_float = img.astype(np.float32)
        b_mean, g_mean, r_mean = (img_float[:, :, i].mean() for i in range(3))
        gray_mean = (b_mean + g_mean + r_mean) / 3.0
        if gray_mean == 0:
            return img
        scale = np.array([gray_mean / b_mean, gray_mean / g_mean, gray_mean / r_mean], dtype=np.float32)
        balanced = np.clip(img_float * scale, 0, 255).astype(np.uint8)
        return balanced
    except Exception as e:
        logger.warning(f"White balance failed, using original: {e}")
        return img


def _normalize_brightness(img: np.ndarray) -> np.ndarray:
    """Normalise image brightness using gamma correction based on mean luminance."""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_lum = float(gray.mean())

        # Target luminance ~130 out of 255; skip if already close
        target = 130.0
        if abs(mean_lum - target) < 15:
            return img

        gamma = np.log(target / 255.0) / np.log(mean_lum / 255.0 + 1e-6)
        gamma = float(np.clip(gamma, 0.5, 2.5))

        lut = np.array([min(255, int((i / 255.0) ** gamma * 255)) for i in range(256)], dtype=np.uint8)
        corrected = cv2.LUT(img, lut)
        logger.debug(f"Gamma correction applied: gamma={gamma:.2f} (mean_lum={mean_lum:.1f})")
        return corrected
    except Exception as e:
        logger.warning(f"Brightness normalisation failed, using original: {e}")
        return img


def _enhance_contrast(img: np.ndarray) -> np.ndarray:
    """Enhance contrast using CLAHE on the L channel of LAB colour space."""
    try:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)
        enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    except Exception as e:
        logger.warning(f"Contrast enhancement failed, using original: {e}")
        return img


def _sharpen(img: np.ndarray) -> np.ndarray:
    """Apply unsharp-mask sharpening to improve text edge clarity."""
    try:
        blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=2.0)
        sharpened = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)
        return sharpened
    except Exception as e:
        logger.warning(f"Sharpening failed, using original: {e}")
        return img
