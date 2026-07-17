import base64
import io
from pathlib import Path

import numpy as np
from PIL import Image


def image_to_base64(image_bytes: bytes, format: str = "PNG") -> str:
    """Encode image bytes to base64 string for API consumption."""
    return base64.b64encode(image_bytes).decode("utf-8")


def bytes_to_numpy(image_bytes: bytes) -> np.ndarray:
    """Convert raw image bytes to a numpy array (BGR for OpenCV)."""
    import cv2
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def numpy_to_bytes(img: np.ndarray, format: str = ".png") -> bytes:
    """Convert numpy array back to image bytes."""
    import cv2
    _, buffer = cv2.imencode(format, img)
    return buffer.tobytes()


def get_image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Get (width, height) from image bytes using Pillow."""
    img = Image.open(io.BytesIO(image_bytes))
    return img.size


def read_exif_rotation(image_bytes: bytes) -> int:
    """Read EXIF orientation tag. Returns degrees to rotate clockwise."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif()
        orientation = exif.get(274)  # 274 = Orientation tag

        rotation_map = {3: 180, 6: 270, 8: 90}
        return rotation_map.get(orientation, 0)
    except Exception:
        return 0
