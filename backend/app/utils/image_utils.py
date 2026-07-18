import base64
import io

import numpy as np
from PIL import Image


def image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string for API consumption."""
    return base64.b64encode(image_bytes).decode("utf-8")


def bytes_to_numpy(image_bytes: bytes) -> np.ndarray | None:
    """Convert raw image bytes to a numpy array (BGR for OpenCV)."""
    import cv2
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def numpy_to_jpeg(img: np.ndarray, quality: int = 90) -> bytes:
    """Convert numpy array to JPEG bytes at the specified quality."""
    import cv2
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode(".jpg", img, encode_params)
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


def split_image_vertically(image_bytes: bytes) -> tuple[bytes, bytes]:
    """Split a single NID image vertically into top (front) and bottom (back) halves."""
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    midpoint = height // 2

    front_img = img.crop((0, 0, width, midpoint))
    back_img = img.crop((0, midpoint, width, height))

    img_format = img.format or "JPEG"

    front_io = io.BytesIO()
    front_img.save(front_io, format=img_format)

    back_io = io.BytesIO()
    back_img.save(back_io, format=img_format)

    return front_io.getvalue(), back_io.getvalue()
